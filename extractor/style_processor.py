# extractor/style_processor.py (Corrected - Removed PaddleOCR import)

import logging
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Set
# from paddleocr import PaddleOCR  <-- REMOVED THIS UNNECESSARY LINE

logger = logging.getLogger("style_processor")

class StyleProcessor:
    """
    Handles the conversion of raw word lists from pdfplumber
    into plain text and extracts REAL style metadata.
    """
    def __init__(self):
        logger.info("Style Processor (Full Style Extraction) initialized.")

    def format_words_to_text(self, words: List[Dict]) -> str:
        """Converts a list of pdfplumber word dicts into a plain string."""
        if not words:
            return ""
        
        lines = defaultdict(list)
        # Group words by their 'top' (y-coordinate)
        for w in words:
            lines[round(w['top'])].append(w)
        
        sorted_lines = sorted(lines.items(), key=lambda item: item[0])
        
        text_lines = []
        for top, line_words in sorted_lines:
            line_words.sort(key=lambda w: w['x0']) # Sort words left-to-right
            text_lines.append(" ".join(w['text'] for w in line_words))
            
        return "\n".join(text_lines)

    def extract_style_data(self, words: List[Dict]) -> Dict[str, Any]:
        """
        Extracts real font types, sizes, and infers style elements.
        """
        if not words:
            return {
                "bullet_points_used": "no",
                "unwanted_icon_used": "false",
                "font_types_used": [],
                "font_sizes_used": []
            }

        # Use Sets for unique collection
        font_types: Set[str] = set()
        font_sizes: Set[float] = set()
        
        potential_bullets_count = 0
        isolated_m_found = False
        isolated_9_found = False
        
        for w in words:
            # 1. Collect Font Information
            # 'fontname' and 'size' are standard keys in pdfplumber word dictionaries
            if 'fontname' in w and w['fontname']:
                # Clean up font name (e.g., F1+Arial-Bold -> Arial-Bold)
                clean_font = w['fontname'].split('+')[-1]
                font_types.add(clean_font)

                # Check for common bullet-point fonts
                font_lower = clean_font.lower()
                if 'symbol' in font_lower or 'wingdings' in font_lower:
                    potential_bullets_count += 1

            if 'size' in w and w['size']:
                # Round size to two decimal places for grouping
                font_sizes.add(round(w['size'], 2)) 

            # 2. Infer Bullet Points (Text-based heuristic)
            # Check for common bullet characters
            if len(w['text']) <= 2 and w['text'] in ['•', '·', '-', '–', '*', '➢']:
                potential_bullets_count += 1

            # 3. Check for isolated icons (Your specific logic)
            # This looks for 'M' and '9' as *isolated* words (from resume2.pdf)
            if w['text'] == 'M':
                isolated_m_found = True
            if w['text'] == '9':
                isolated_9_found = True

        # 4. Final Style Dictionary
        style_data = {
            # Set to 'yes' if we find 3 or more bullet-like indicators
            "bullet_points_used": "yes" if potential_bullets_count >= 3 else "no",
            "unwanted_icon_used": "true" if (isolated_m_found and isolated_9_found) else "false",
            "font_types_used": sorted(list(font_types)),
            "font_sizes_used": sorted(list(font_sizes)),
        }
        
        return style_data

    def process_word_list(self, words: List[Dict]) -> Tuple[str, Dict[str, Any]]:
        """
        Processes a single list of words into plain text and returns style data.
        
        Returns:
            (plain_text, style_data_dict)
        """
        plain_text = self.format_words_to_text(words)
        style_data = self.extract_style_data(words)
        return plain_text, style_data