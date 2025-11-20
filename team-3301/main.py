"""Main entry point for PDF section classification"""
import json
import time
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import API_URL, API_KEY, MODEL, MINUTEBOOK_PDF_PATH
from api_client import APIClient
from classifier import TextBasedClassifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')


def main():
    """Main execution function."""
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), MINUTEBOOK_PDF_PATH)
    
    start = time.time()
    
    api_client = APIClient(API_URL, API_KEY)
    classifier = TextBasedClassifier(api_client, batch_size=6)
    
    sections = classifier.find_all_sections(pdf_path, MODEL)
    
    end = time.time()
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result.json")
    output = {"sections": sections}
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Classification terminée!")
    print(f"{'='*80}")
    print(f"Temps: {end-start:.2f}s")
    print(f"Requêtes API: {api_client.request_count}")
    print(f"Sections trouvées: {len(sections)}")
    print(f"\nSections:")
    for section in sections:
        page_count = section['endPage'] - section['startPage'] + 1
        print(f"  {section['name']}: pages {section['startPage']}-{section['endPage']} ({page_count} pages)")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
