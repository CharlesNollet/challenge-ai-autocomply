"""Prompt templates for text extraction and structure identification"""

TEXT_EXTRACTION_PROMPT = """You're examining a grid layout of document page previews from a legal minute book. The grid shows {num_pages} pages spanning from page {start_page} through page {end_page}.

VISUAL LAYOUT:
The image is organized as a 2-column grid. Each cell contains a page preview with a red numeric label positioned at the bottom-right corner indicating its page number.

YOUR TASK:
For every single page in this range, identify and extract the most prominent textual elements that reveal what type of content appears on that page. Focus on:
- Document headers and titles that appear at the top
- Section names or category labels
- Legal document identifiers (like "BY-LAW", "ARTICLES", "RESOLUTION", "REGISTER")
- Any text that helps classify what kind of document section this is

OUTPUT INSTRUCTIONS:
Return your findings as a simple numbered list. For each page number, write what you see:

Page [number]: [brief description of main content/heading]

CRITICAL RULES:
1. You must provide an entry for every page from {start_page} to {end_page} - no skipping
2. Use the red numbers in the bottom-right to identify which page is which
3. Keep descriptions concise (1-2 lines maximum per page)
4. Focus on headers/titles rather than paragraph text
5. Maintain the correct page sequence

Example of expected output:
Page 1: Articles of Incorporation - Company registration document
Page 2: Share capital structure and registered office information
Page 3: BY-LAW NUMBER 1 - General corporate governance rules
Page 4: Directors' powers and responsibilities section
Page 5: Unanimous Shareholder Agreement - voting provisions

"""

STRUCTURE_PROMPT_SINGLE = """You are analyzing a corporate minute book that contains {total_pages} pages total. Based on the extracted text content provided below, your job is to figure out where each major section begins and ends.

The minute book is organized into these section categories (in typical order):
{section_list}

Here's the extracted text from the document with page references:
{text}

WHAT YOU NEED TO DO:
Map out the page ranges for each section type. Some sections might be very long (50+ pages), while others like registers might only be 1-2 pages. Pay close attention to short sections so you don't miss them.

IMPORTANT CONSTRAINTS:
- The document runs continuously from page 1 to page {total_pages}
- Every single page must belong to exactly one section
- Sections cannot overlap (if section A ends on page 50, section B must start on page 51)
- There should be no gaps between sections
- Each section type appears only once in the document

RESPONSE FORMAT:
Return a JSON object with this exact structure:

{{
  "sections": [
    {{"name": "Articles & Amendments", "startPage": 1, "endPage": 20}},
    {{"name": "By Laws", "startPage": 21, "endPage": 45}}
  ]
}}

Use the exact section names from the list above. Only include sections you can actually identify in the text.

QUALITY CHECK:
Before responding, verify that:
- Your first section starts at page 1
- Your last section ends at page {total_pages}
- There are no gaps or overlaps between consecutive sections
- You haven't missed any short sections (especially registers which are often brief)"""

STRUCTURE_PROMPT_MULTI = """You're working on part {part_idx} of {total_parts} of a minute book analysis. The complete document has {total_pages} pages.

SECTION TYPES TO IDENTIFY:
{section_list}

{context_section}

TEXT CONTENT FOR THIS SEGMENT (Part {part_idx}/{total_parts}):
{text}

YOUR TASK:
{context_instruction}

ANALYSIS TIPS:
- Some sections like registers are very short (1-3 pages) - don't overlook them
- Look for clear indicators like "REGISTER OF", "BY-LAW", "ARTICLES", "RESOLUTION"
- Each section type only appears once in the entire document
- Be especially careful not to merge different section types together

STRUCTURAL REQUIREMENTS:
The final result must have these properties:
- Starts at page 1, ends at page {total_pages}
- No page appears in multiple sections
- No pages are left unassigned
- Sections are in sequential order with no gaps (if section A ends at page X, section B starts at page X+1)

OUTPUT FORMAT:
Return the COMPLETE list of all sections identified so far as JSON:

{{
  "sections": [
    {{"name": "Section Name", "startPage": X, "endPage": Y}}
  ]
}}

Use exact section names from the list provided above.

FINAL CHECK:
Make sure your section list covers all pages from 1 to {total_pages} with no gaps or overlaps."""
