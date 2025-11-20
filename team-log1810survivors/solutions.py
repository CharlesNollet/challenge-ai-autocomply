import fitz
import requests
import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

# Configuration
API_URL = "https://ai-models.autocomply.ca"
API_KEY = "sk-ac-7f8e9d2c4b1a6e5f3d8c7b9a2e4f6d1c"

MODEL = "gpt-4o"

MAX_CONCURRENCY = 4
REQUEST_TIMEOUT = 30 #secondes 
RETRY_MAX = 3

EXPECTED_SECTIONS = [
    "Articles & Amendments",
    "By Laws",
    "Unanimous Shareholder Agreement",
    "Minutes & Resolutions",
    "Directors Register",
    "Officers Register",
    "Shareholder Register",
    "Securities Register",
    "Share Certificates",
    "Ultimate Beneficial Owner Register"
]

PAGE_PROMPT_TEMPLATE = """Analyze this page from a corporate Minute Book. 

Your task: 
1. Identify if this page is the START of a new section (has a section title/header)
2. Identify the section name if present (must match exactly one of these) : 
    - Articles & Amendments
    - By Laws
    - Unanimous Shareholder Agreement
    - Minutes & Resolutions
    - Directors Register
    - Officers Register
    - Shareholder Register
    - Securities Register
    - Share Certificates
    - Ultimate Beneficial Owner Register

3. Rate your confidence level (HIGH/MEDIUM/LOW)

Respond in this EXACT JSON format: 
{
    "is_section_start": true/false, 
    "section_name": "exact section name" or null, 
    "confidence": "HIGH/MEDIUM/LOW",
    "reasoning": "brief explanation"
}"""

BOUNDARY_VERIFICATION_PROMPT = """You are analyzing a page from a corporate Minute Book to verify section boudnaries.

Given context : 
- Previous page was a part of section: {prev_section}
- Current page number: {page_num}

Determine: 
1. Is this page still part of "{prev_section}" section?
2. Or is it the start of a NEW section?
3. If new section, what is its exact name?

Respond in EXACT JSON format: 
{
    "continues_previous": true/false, 
    "new_section_name": "exact name" or null, 
    "confidence": "HIGH/MEDIUM/LOW"
} """


class PDFSplitter: 
    def __init__(self, pdfPath: str):
        self.pdfPath = pdfPath
        self.doc = fitz.open(pdfPath)
        self.totalPages = len(self.doc)
        self.apiCalls = 0
        self.cache = {}
    
    def PdfPageToBase64(self, pageNumber: int):
        page = self.doc.load_page(pageNumber)
        pix = page.get_pixmap(matrix= fitz.Matrix(1.5, 1.5))
        imgBytes = pix.tobytes("png")
        return base64.b64encode(imgBytes).decode('utf-8')
    
    def CallApi(self, pageB64, prompt, retries = 0): 
        headers={
            "Authorization" : f"Bearer {API_KEY}", 
            "Content-Type": "application/json"
        }

        payload = {
            "pdfPage" : pageB64, 
            "prompt" : prompt, 
            "model" : MODEL
        }

        try: 
            reponse = requests.post(
                f"{API_URL}/process-pdf", 
                json=payload, 
                headers=headers, 
                timeout=REQUEST_TIMEOUT
            )

            self.apiCalls += 1

            if reponse.status_code == 200:
                return reponse.json()["result"]
            elif reponse.status_code == 429 and retries < RETRY_MAX: 
                time.sleep(2**retries)
                return self.CallApi(pageB64, prompt, retries+1)
            else: 
                print(f"API Error: {reponse.status_code} - {reponse.text}")
                return None
        
        except Exception as e:
            print(f"Request failed: {e}")
            if retries < RETRY_MAX: 
                time.sleep(2**retries)
                return self.CallApi(pageB64, prompt, retries + 1)
            return None
    
    def ParseJSONReponse(self, reponse): 
        if not reponse: 
            return None
        
        try: 
            cleaned = reponse.strip()
            if cleaned.startswith("```json"): 
                cleaned = cleaned[7:]
            if cleaned.startswith("```"): 
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}\nResponse: {reponse}")
            return None
        
    def SamplePages(self): 
        samples = set()

        samples.update(range(min(5, self.totalPages)))

        step = 10
        for i in range(0, self.totalPages, step): 
            samples.add(i)

        if self.totalPages > 10:
            samples.update(range(max(0, self.totalPages - 5), self.totalPages))

        return sorted(list(samples))
    
    def DetectSectionStarts(self, samplePages): 
        sectionStarts = {}

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
            futureToPage = {}

            for pageNum in samplePages:
                pageB64 = self.PdfPageToBase64(pageNum)
                future = executor.submit(self.CallApi, pageB64, PAGE_PROMPT_TEMPLATE)
                futureToPage[future] = pageNum
            
            for future in as_completed(futureToPage):
                pageNum = futureToPage[future]
                reponse = future.result()

                if reponse: 
                    data = self.ParseJSONReponse(reponse)
                    if data and data.get("is_section_start"): 
                        sectionStarts[pageNum] = data
                        print(f"Page {pageNum} : Detected section '{data.get('section_name')}' (confidence: {data.get('confidence')})")

        return sectionStarts
    
    def binarySearchBoundary(self, sectionName, startPage, endPage, searchForEnd = False): 
        if startPage >= endPage - 1: 
            return startPage if not searchForEnd else endPage
        
        mid = (startPage + endPage) // 2
        pageB64 = self.PdfPageToBase64(mid)

        prompt = BOUNDARY_VERIFICATION_PROMPT.format(prev_section=sectionName, page_num=mid)

        reponse = self.CallApi(pageB64, prompt)

        if not reponse: 
            return mid
        
        data = self.ParseJSONReponse(reponse)
        if not data:
            return mid
        
        if searchForEnd:
            if data.get("continues_previous"): 
                return self.binarySearchBoundary(sectionName, mid, endPage, False)
            else: 
                return self.binarySearchBoundary(sectionName, startPage, mid, False)

            
    def RefineBoundaries(self, sectionStarts):
        sections = []
        sortedStarts = sorted(sectionStarts.items())

        for i, (pageNum, data) in enumerate(sortedStarts):
            sectionName = data.get("section_name")
            if not sectionName: 
                continue

            startPage = pageNum

            if i < len(sortedStarts) - 1:
                nextStart = sortedStarts[i+1][0]
                endPage = nextStart - 1
            else: 
                endPage = self.totalPages -1 

            if data.get("confidence") != "HIGH" or ((endPage - startPage) > 15) :
                refinedEnd = self.verifyEndPage(sectionName, startPage, endPage)
                if refinedEnd: 
                    endPage = refinedEnd

            sections.append({
                "name": sectionName, 
                'startPage': startPage + 1, 
                "endPage": endPage + 1
            })
        
        return sections
    
    def verifyEndPage(self, sectionName, start, end): 
        if end - start <= 5 :
            return end
        
        pagesToCheck = [end, end -1, end - 2]

        for page in pagesToCheck:
            if page <= start:
                continue

            pageB64 = self.PdfPageToBase64(page)
            prompt= BOUNDARY_VERIFICATION_PROMPT.format(
                prev_section = sectionName, 
                page_num = page
            )

            reponse = self.CallApi(pageB64, prompt)
            
            if reponse:
                data = self.ParseJSONReponse(reponse)
                if data: 
                    if not data.get("continues_previous") and data.get("confidence") == "HIGH":
                        return page - 1
            
        return end
    
    def split(self): 
        startTime = time.time()

        print(f"Processing PDF: {self.pdfPath}")
        print(f"Total pages: {self.totalPages}")

        samplePages = self.SamplePages()
        print(f"Samplinf {len(samplePages)} pages...")

        sectionStarts = self.DetectSectionStarts(samplePages)
        print(f"Found {len(sectionStarts)} potentiel section starts")

        sections = self.RefineBoundaries(sectionStarts)
        sections.sort(key=lambda x: x["startPage"])
        elapsedTime = time.time() - startTime
        print(f"\n--- Results ---")
        print(f"Execution time: {elapsedTime:.2f}s")
        print(f"API calls: {self.apiCalls}")
        print(f"Sections found: {len(sections)}")
        
        for section in sections:
            print(f"  {section['name']}: pages {section['startPage']}-{section['endPage']}")
        
        return {
            "sections": sections,
            "metadata": {
                "execution_time": elapsedTime,
                "api_calls": self.apiCalls,
                "total_pages": self.totalPages
            }
        }
    
def main():
    if len(sys.argv) < 2:
        print("Usage: python solution.py <pdf_path>")
        sys.exit(1)
        
    pdfPath = sys.argv[1]

    splitter = PDFSplitter(pdfPath)
    result = splitter.split()

    output = {"sections" : result["sections"]}

    with open("result.json", "w") as f: 
        json.dump(output, f, indent=2)

    print(f"\nResults saved to result.json")
    print(f"Estimated score: {result['metadata']['execution_time']:.2f} + {result['metadata']['api_calls']} + errors^2")


if __name__ == "__main__":
    main()