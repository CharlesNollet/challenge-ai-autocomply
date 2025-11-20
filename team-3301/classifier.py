"""Main text-based section classifier"""
import json
import logging
import concurrent.futures
import fitz
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_utils import create_page_grid_b64
from config import SECTION_NAMES
from api_client import APIClient
from section_processor import SectionProcessor
from prompts import TEXT_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class TextBasedClassifier:
    """Text-based section classifier using batch processing."""
    
    def __init__(self, api_client: APIClient, batch_size: int = 6):
        """Initialize classifier.
        
        Args:
            api_client: API client instance
            batch_size: Number of pages per batch
        """
        self.api_client = api_client
        self.batch_size = batch_size
    
    def find_all_sections(self, pdf_path: str, model: str) -> List[dict]:
        """Find all sections in PDF.
        
        Args:
            pdf_path: Path to PDF file
            model: AI model to use
        
        Returns:
            List of section dicts
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        logger.info(f"Traitement de {total_pages} pages...")
        logger.info(f"Création de lots de {self.batch_size} pages...")
        
        batches = self._create_batches(doc, total_pages)
        doc.close()
        
        logger.info(f"{len(batches)} lots créés")
        
        logger.info("Extraction du texte et analyse")
        sections = self._process_batches(batches, total_pages, model)
        
        return sections
    
    def _create_batches(self, doc: fitz.Document, total_pages: int) -> List[dict]:
        """Create batches of pages for processing."""
        batches = []
        for i in range(0, total_pages, self.batch_size):
            batch_indices = list(range(i, min(i + self.batch_size, total_pages)))
            grid_b64 = create_page_grid_b64(doc, batch_indices)
            if grid_b64:
                batches.append({
                    'batch_num': len(batches) + 1,
                    'start_page': batch_indices[0] + 1,
                    'end_page': batch_indices[-1] + 1,
                    'page_nums': [p + 1 for p in batch_indices],
                    'grid_image_b64': grid_b64,
                    'text_result': None
                })
        return batches
    
    def _process_batches(self, batches: List[dict], total_pages: int, model: str) -> List[dict]:
        """Process batches to extract text and identify structure."""
        def process_batch(batch: dict) -> dict:
            prompt = TEXT_EXTRACTION_PROMPT.format(
                num_pages=len(batch['page_nums']),
                start_page=batch['start_page'],
                end_page=batch['end_page']
            )
            
            response = self.api_client.call_vision_api(batch['grid_image_b64'], prompt, model)
            batch['text_result'] = response
            return batch
        
        total_batches = len(batches)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
            
            for future in concurrent.futures.as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    result_batch = future.result()
                    logger.info(f"  Lot {result_batch['batch_num']}/{total_batches} terminé")
                except Exception as exc:
                    logger.error(f"  Lot {batch['batch_num']}/{total_batches} échoué: {exc}")
                    batch['text_result'] = f"ERREUR: {exc}"
        
        return self._identify_structure(batches, total_pages, model)
    
    def _identify_structure(self, batches: List[dict], total_pages: int, model: str) -> List[dict]:
        """Identify section structure from extracted text."""
        aggregated_text = self._aggregate_batch_results(batches)
        
        chunk_strategies = [1, 3, 5]
        
        for chunk_count in chunk_strategies:
            logger.info(f"  Analyse de structure avec {chunk_count} segment")
            identified_sections = self._extract_with_chunks(
                aggregated_text, 
                chunk_count, 
                model, 
                total_pages
            )
            
            if identified_sections:
                logger.info(f"  Structure identifiée avec {chunk_count} segment")
                return identified_sections
            
            logger.info(f"  Approche à {chunk_count} segment infructueuse, essai suivant...")
        
        logger.warning("  Toutes les stratégies de segmentation épuisées, aucune section identifiée, sad :(")
        return []
    
    def _aggregate_batch_results(self, batches: List[dict]) -> str:
        """Aggregate text results from all batches.
        
        Args:
            batches: List of batch dictionaries
        
        Returns:
            Combined text string
        """
        text_parts = []
        separator = "=" * 50
        
        for batch in batches:
            header = f"\n[Batch {batch['batch_num']}: Pages {batch['start_page']}-{batch['end_page']}]"
            text_parts.append(header)
            text_parts.append(batch['text_result'])
            text_parts.append(separator)
        
        return "\n".join(text_parts)
    
    def _extract_with_chunks(self, text: str, num_chunks: int, model: str, total_pages: int) -> Optional[List[dict]]:
        """Extract structure using chunked text."""
        lines = text.splitlines(keepends=True)
        total_lines = len(lines)
        chunk_size = (total_lines + num_chunks - 1) // num_chunks
        
        current_sections = []
        
        for i in range(num_chunks):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, total_lines)
            chunk_text = "".join(lines[start:end])
            
            if not chunk_text.strip():
                continue
            
            prompt = self._build_structure_prompt(chunk_text, current_sections, i + 1, num_chunks, total_pages)
            
            response = self.api_client.call_text_api(prompt, model)
            parsed = self.api_client.parse_json_response(response)
            
            if parsed and "sections" in parsed:
                current_sections = parsed["sections"]
            else:
                return None
        
        sections = SectionProcessor.fix_section_boundaries(current_sections)
        return sections if sections else None
    
    def _build_structure_prompt(self, text: str, current_sections: List[dict], part_idx: int, total_parts: int, total_pages: int) -> str:
        """Build prompt for structure extraction."""
        section_list = "\n".join(f"- {name}" for name in SECTION_NAMES)
        
        if total_parts == 1:
            from prompts import STRUCTURE_PROMPT_SINGLE
            return STRUCTURE_PROMPT_SINGLE.format(
                total_pages=total_pages,
                section_list=section_list,
                text=text
            )
        else:
            from prompts import STRUCTURE_PROMPT_MULTI
            
            if current_sections:
                context_section = f"""PREVIOUS ANALYSIS CONTEXT:
Sections identified so far:
{json.dumps(current_sections, indent=2)}"""
                context_instruction = "Continue building the section list. Update endPage values for continuing sections, and add new sections as they appear. Return the COMPLETE updated list."
            else:
                context_section = "This is the first part of the analysis."
                context_instruction = "Begin identifying sections from the extracted text below."
            
            return STRUCTURE_PROMPT_MULTI.format(
                total_pages=total_pages,
                part_idx=part_idx,
                total_parts=total_parts,
                section_list=section_list,
                context_section=context_section,
                context_instruction=context_instruction,
                text=text
            )
