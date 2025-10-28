# extractor/style_processor.py (Simplified - Text Only)

import logging
from collections import defaultdict
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("style_processor")

class StyleProcessor:
    """
    Handles the conversion of raw word lists from pdfplumber
    into plain text.
    """
    def __init__(self):
        logger.info("Style Processor (Text-Only) initialized.")

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

    def process_word_list(self, words: List[Dict]) -> str:
        """
        Processes a single list of words into plain text.
        
        Returns:
            plain_text
        """
        # Sort words top-to-bottom, then left-to-right
        words.sort(key=lambda w: (w['top'], w['x0']))
        
        plain_text = self.format_words_to_text(words)
        
        return plain_text