# extractor/extractor.py (Updated with a debug line)

import json
import logging
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Optional, Dict, Any, Tuple
import sys
import glob
import math
import os

import pdfplumber
import fitz
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from PIL import Image

# (Imports are all correct)
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
import pytesseract
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
try:
    import docx
except ImportError:
    pass
try:
    from .preprocess import preprocess_image_for_ocr
except ImportError:
    logging.warning("Could not import preprocess_image_for_ocr. Using default.")
    def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
        return img.convert("L")
try:
    from .style_processor import StyleProcessor
except ImportError:
    logger = logging.getLogger("resume_extractor_import")
    logger.critical("FATAL: Failed to import 'StyleProcessor'.")
    raise

# (Logger is correct)
logger = logging.getLogger("resume_extractor_kmeans")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [Extractor]: %(message)s"))
    logger.addHandler(handler)

# (ExtractionResult class is correct)
class ExtractionResult:
    def __init__(
        self,
        source: str,
        pages: int,
        metadata: Dict[str, Any],
        column_texts: List[str],
        style_analysis: Dict[str, Any],
        links: List[Dict[str, Any]] 
    ):
        self.source = str(source).replace(os.path.sep, '\\\\') 
        self.pages = pages
        self.metadata = metadata
        self.column_texts = column_texts
        self.style_analysis = style_analysis
        self.links = links  

    def to_jsonl(self) -> str:
        data = {
            "source": self.source,
            "pages": self.pages,
            "metadata": self.metadata,
            "column_texts": self.column_texts,
            "style_analysis": self.style_analysis,
            "links": self.links 
        }
        return json.dumps(data, ensure_ascii=False)


# ---------------- Extractor Logic ----------------

class Extractor:
    def __init__(self, output_dir: str = "data/downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style_processor = StyleProcessor() 

    # (_find_links_pymupdf is correct)
    def _find_links_pymupdf(self, file_path: Path) -> List[Dict[str, Any]]:
        links_found = []
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                links = page.get_links()
                for link in links:
                    if link.get('kind') == fitz.LINK_URI:
                        rect_coords = []
                        if 'rect' in link and link['rect']:
                            rect_coords = [link['rect'].x0, link['rect'].y0, link['rect'].x1, link['rect'].y1]
                        links_found.append({
                            'url': link.get('uri', ''),
                            'page': page_num + 1,
                            'rect': rect_coords
                        })
            doc.close()
        except Exception as e:
            logger.error(f"Error extracting links with PyMuPDF: {e}")
        unique_links = []
        seen_urls = set()
        for link in links_found:
            if link['url'] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link['url'])
        return unique_links

    # (_find_optimal_k is correct)
    def _find_optimal_k(self, X: np.ndarray, max_k: int = 5) -> int:
        if len(X) < 2:
            return 1
        silhouette_scores = {}
        k_values = range(1, min(max_k + 1, len(X)))
        if 1 in k_values:
            silhouette_scores[1] = -1 
        for k in k_values:
            if k > 1:
                try:
                    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
                    score = silhouette_score(X, kmeans.labels_)
                    silhouette_scores[k] = score
                except ValueError:
                    pass
        if not silhouette_scores: return 1
        best_k = max(silhouette_scores, key=silhouette_scores.get)
        if best_k >= 2 and silhouette_scores.get(best_k, 0) > 0.5:
            return min(best_k, 2)
        return 1

    # (_cluster_words_into_columns is correct)
    def _cluster_words_into_columns(self, words: List[Dict], page_width: float) -> Tuple[List[str], int]:
        x_coords = np.array([w['x0'] for w in words]).reshape(-1, 1)
        num_columns = self._find_optimal_k(x_coords, max_k=3)
        if num_columns == 1:
            text = self.style_processor.format_words_to_text(words)
            return [text], 1
        midpoint = page_width / 2
        left_col_words = []
        right_col_words = []
        for w in words:
            word_center = (w['x0'] + w['x1']) / 2
            if word_center < midpoint:
                left_col_words.append(w)
            else:
                right_col_words.append(w)
        left_col_words.sort(key=lambda w: (w['top'], w['x0']))
        right_col_words.sort(key=lambda w: (w['top'], w['x0']))
        left_text = self.style_processor.format_words_to_text(left_col_words)
        right_text = self.style_processor.format_words_to_text(right_col_words)
        return [left_text, right_text], 2

    # --- THIS FUNCTION IS NOW FIXED ---
    def _extract_pdfplumber(self, file_path: Path) -> ExtractionResult:
        """Extracts text, columns, style, and links from a PDF."""
        
        empty_style = {
            "bullet_points_used": "no",
            "unwanted_icon_used": "false",
            "font_types_used": [],
            "font_sizes_used": []
        }
        
        links = self._find_links_pymupdf(file_path)
            
        try:
            with pdfplumber.open(file_path) as pdf:
                num_pages = len(pdf.pages)
                page = pdf.pages[0] 
                
                raw_words = page.extract_words(
                    x_tolerance=2, 
                    y_tolerance=2, 
                    extra_attrs=["fontname", "size"]
                )
                
                if not raw_words:
                    return ExtractionResult(
                        source=str(file_path), pages=num_pages, 
                        metadata={"method": "pdfplumber_empty"}, 
                        column_texts=[""], 
                        style_analysis=empty_style,
                        links=links
                    )
                
                # --- ADDED THIS DEBUG LINE ---
                # This will print the first word's data to the console
                print(f"DEBUG DATA FOR {file_path.name}:", raw_words[0])
                # --- END OF DEBUG LINE ---

                column_texts, num_columns = self._cluster_words_into_columns(raw_words, page.width)
                
                _, style_data = self.style_processor.process_word_list(raw_words)

                metadata = {
                    "method": "pdfplumber_midpoint_split",
                    "detected_columns": num_columns,
                    "column_split_rationale": "The document was detected as having a two-column layout. The K-means clustering algorithm was used on the horizontal coordinates (x-coordinates) of text elements to group them into two distinct vertical zones (columns) for accurate separation and sequential reading of logical content.",
                    "extraction_method_analysis": {
                        "pdfplumber": "Base library used for low-level PDF text and layout extraction.",
                        "kmeans": "K-Means used to detect 2-column layout.",
                        "zoned": "Page split at vertical midpoint."
                    }
                }
                if num_columns == 1:
                     metadata["method"] = "pdfplumber_single_column"


                return ExtractionResult(
                    source=str(file_path),
                    pages=num_pages,
                    metadata=metadata,
                    column_texts=column_texts,
                    style_analysis=style_data,
                    links=links
                )
        except Exception as e:
            logger.error(f"Error processing PDF with pdfplumber: {e}")
            return ExtractionResult(
                source=str(file_path), pages=0, 
                metadata={"method": "pdfplumber_error", "error": str(e)}, 
                column_texts=[""], 
                style_analysis=empty_style,
                links=links
            )

    # (extract method is correct)
    def extract(self, file_path: Path) -> ExtractionResult:
        ext = file_path.suffix.lower()
        if ext == '.pdf':
            return self._extract_pdfplumber(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            empty_style = {
                "bullet_points_used": "no",
                "unwanted_icon_used": "false",
                "font_types_used": [],
                "font_sizes_used": []
            }
            return ExtractionResult(
                source=str(file_path), pages=0,
                metadata={"method": "unsupported_type", "error": f"File type {ext} not supported."},
                column_texts=[""],
                style_analysis=empty_style,
                links=[] 
            )

    # (process_and_save method is correct)
    def process_and_save(self, file_path: str) -> str:
        file_path = Path(file_path)
        result = self.extract(file_path)
        output_file = self.output_dir / (file_path.stem + ".jsonl")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result.to_jsonl())
        logger.info(f"✅ Saved: {output_file}")
        return str(output_file)

# (CLI is correct)
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m extractor.extractor <input_pattern>")
        sys.exit(1)
    input_patterns = sys.argv[1:]
    files = []
    for pattern in input_patterns:
        files.extend(glob.glob(pattern))
    if not files:
        print("No files found.")
        sys.exit(1)
    extractor = Extractor()
    for file in files:
        extractor.process_and_save(file)