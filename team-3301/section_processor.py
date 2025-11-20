"""Section boundary processing and fixing logic"""
import logging
from typing import List

logger = logging.getLogger(__name__)


class SectionProcessor:
    """Handles section boundary fixing and validation."""
    
    @staticmethod
    def fix_section_boundaries(sections: List[dict]) -> List[dict]:
        """Fix overlapping sections and small gaps.
        
        Args:
            sections: List of section dicts
        
        Returns:
            Fixed list of section dicts
        """
        if not sections:
            return sections
        
        sorted_sections = sorted(sections, key=lambda s: s['startPage'])
        fixed_sections = []
        i = 0
        
        while i < len(sorted_sections):
            current = sorted_sections[i]
            
            if i < len(sorted_sections) - 1:
                next_section = sorted_sections[i + 1]
                
                if current['endPage'] >= next_section['startPage']:
                    if current['startPage'] == next_section['startPage'] and current['endPage'] == next_section['endPage']:
                        logger.info(f"  Suppression de la section dupliquée: {next_section['name']} (identique à {current['name']})")
                        i += 1
                        continue
                    
                    midpoint = (current['endPage'] + next_section['startPage']) // 2
                    current = {
                        'name': current['name'],
                        'startPage': current['startPage'],
                        'endPage': midpoint
                    }
                    sorted_sections[i + 1] = {
                        'name': next_section['name'],
                        'startPage': midpoint + 1,
                        'endPage': next_section['endPage']
                    }
                    logger.info(f"  Chevauchement corrigé entre {current['name']} et {next_section['name']} à la page {midpoint}")
            
            fixed_sections.append(current)
            i += 1
        
        final_sections = []
        for i, section in enumerate(fixed_sections):
            if i < len(fixed_sections) - 1:
                next_section = fixed_sections[i + 1]
                gap = next_section['startPage'] - section['endPage'] - 1
                if 0 < gap <= 5:
                    section = {
                        'name': section['name'],
                        'startPage': section['startPage'],
                        'endPage': next_section['startPage'] - 1
                    }
                    logger.info(f"  Écart de {gap} page(s) comblé après {section['name']}")
            final_sections.append(section)
        
        return final_sections
