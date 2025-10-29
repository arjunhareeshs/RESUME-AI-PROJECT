# extractor/extractor.py (Enhanced with OCR for scanned PDFs, DOCX, and Images - Refined)

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

# OCR and Image Processing
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    
import pytesseract
from pdf2image import convert_from_path, exceptions

# Logger setup (must be before any usage)
logger = logging.getLogger("resume_extractor_enhanced")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [Extractor]: %(message)s"))
    logger.addHandler(handler)

# Set Tesseract path explicitly for Windows if not in PATH
# If Tesseract is in your PATH, you can comment this out.
try:
    # Attempt to find Tesseract automatically
    tesseract_path = pytesseract.get_tesseract_version()
    logger.info(f"Tesseract found automatically: {tesseract_path}")
except pytesseract.TesseractNotFoundError:
    logger.warning("Tesseract not found in PATH. Setting explicitly (Windows).")
    # Modify this path if your Tesseract installation is different
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    # Check again after setting
    try:
        tesseract_path = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract found at explicit path: {tesseract_path}")
    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract not found even at explicit path. OCR will likely fail.")


try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

# DOCX support
try:
    import docx
    from docx.shared import Pt
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Internal imports
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

# Logger already configured above


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


class Extractor:
    def __init__(self, output_dir: str = "data/downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style_processor = StyleProcessor()
        
        # Initialize PaddleOCR if available
        if PADDLE_AVAILABLE:
            try:
                # use_gpu=False can be added if you don't have GPU setup
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=False) 
                logger.info("PaddleOCR initialized successfully (CPU)")
            except Exception as e:
                logger.warning(f"PaddleOCR initialization failed: {e}. Falling back to Tesseract.")
                self.paddle_ocr = None
        else:
            self.paddle_ocr = None
            logger.info("PaddleOCR library not found. Tesseract will be used for OCR.")

    # ============ LINK EXTRACTION ============
    def _find_links_pymupdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract hyperlinks from PDF using PyMuPDF"""
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
            # Don't log errors for file types Fitz cannot open (like images)
            if not isinstance(e, (fitz.fitz.FileNotFoundError, fitz.fitz.FileDataError, RuntimeError)): 
                 logger.error(f"Error extracting links with PyMuPDF for {file_path.name}: {e}")
        
        # Remove duplicates
        unique_links = []
        seen_urls = set()
        for link in links_found:
            # Ignore empty or placeholder URLs
            if link['url'] and link['url'] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link['url'])
        return unique_links

    # ============ COLUMN DETECTION ============
    def _find_optimal_k(self, X: np.ndarray, max_k: int = 5) -> int:
        """Find optimal number of columns using silhouette score"""
        if len(X) < 2:
            return 1
        silhouette_scores = {}
        k_values = range(1, min(max_k + 1, len(X)))
        if 1 in k_values:
            silhouette_scores[1] = -1 # Assign a low score for k=1
        for k in k_values:
            if k > 1:
                try:
                    # n_init helps stability
                    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X) 
                    score = silhouette_score(X, kmeans.labels_)
                    silhouette_scores[k] = score
                except ValueError: # Can happen if a cluster is empty
                    pass
        if not silhouette_scores or max(silhouette_scores.values()) < 0: # Check if any valid score exists
             return 1
        best_k = max(silhouette_scores, key=silhouette_scores.get)
        # Use a threshold to prefer 1 column unless 2 columns are clearly distinct
        if best_k >= 2 and silhouette_scores.get(best_k, 0) > 0.5: 
            return min(best_k, 2) # Assume max 2 columns for resumes
        return 1

    def _cluster_words_into_columns(self, words: List[Dict], page_width: float) -> Tuple[List[str], int]:
        """
        Split words into columns using a robust midpoint split, after checking k-means suggestion.
        (Refined docstring)
        """
        if not words: # Handle empty word list
             return [""], 1 
             
        # Use x0 for clustering column detection
        x_coords = np.array([w['x0'] for w in words]).reshape(-1, 1) 
        num_columns = self._find_optimal_k(x_coords, max_k=3)
        
        if num_columns == 1:
            # Sort all words top-to-bottom, left-to-right before formatting
            words.sort(key=lambda w: (w['top'], w['x0'])) 
            text = self.style_processor.format_words_to_text(words)
            return [text], 1
        
        # If k=2 suggested, use midpoint split
        midpoint = page_width / 2
        left_col_words = []
        right_col_words = []
        
        for w in words:
            # Use word center for assignment
            word_center = (w['x0'] + w['x1']) / 2 
            if word_center < midpoint:
                left_col_words.append(w)
            else:
                right_col_words.append(w)
        
        # Sort within columns
        left_col_words.sort(key=lambda w: (w['top'], w['x0']))
        right_col_words.sort(key=lambda w: (w['top'], w['x0']))
        
        left_text = self.style_processor.format_words_to_text(left_col_words)
        right_text = self.style_processor.format_words_to_text(right_col_words)
        
        return [left_text, right_text], 2

    # ============ PDF SCANNED CHECK ============
    def _is_pdf_scanned(self, file_path: Path) -> bool:
        """Check if PDF is scanned (image-based) by checking text content"""
        try:
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) == 0:
                    logger.info(f"{file_path.name}: PDF has no pages, assuming scanned.")
                    return True
                
                page = pdf.pages[0]
                text = page.extract_text(x_tolerance=2, y_tolerance=2) # Use tolerances
                
                # Check character count instead of arbitrary length
                char_count = len(re.findall(r'\S', text or "")) # Count non-whitespace chars
                if char_count < 100: # If very few characters extracted
                    logger.info(f"{file_path.name}: Few characters ({char_count}), likely scanned.")
                    return True
                
                # Double-check with words (less reliable than text length)
                words = page.extract_words(x_tolerance=2, y_tolerance=2)
                if not words or len(words) < 20:
                     logger.info(f"{file_path.name}: Few words ({len(words or [])}), likely scanned.")
                     return True
                        
                return False # Looks like a text PDF
        except Exception as e:
            logger.warning(f"Error checking if PDF is scanned ({file_path.name}): {e}. Assuming scanned.")
            return True

    # extractor.py (Relevant section modified)

# ... (other imports and code) ...

    # ============ OCR TEXT EXTRACTION ============
    def _extract_text_from_image_ocr(self, img: Image.Image) -> str:
        """Extract text from image using OCR (PaddleOCR or Tesseract)"""
        try:
            # Ensure image is RGB before preprocessing (needed for numpy array)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            processed_img = preprocess_image_for_ocr(img) # Grayscale/Thresholding happens here
            
            ocr_text = ""
            ocr_engine_used = "None"

            # Try PaddleOCR first
            if self.paddle_ocr:
                try:
                    # Pass the numpy array of the processed image
                    result = self.paddle_ocr.ocr(np.array(processed_img), cls=True) 
                    if result and result[0]:
                        text_lines = [line[1][0] for line in result[0] if line and line[1][0]]
                        ocr_text = "\n".join(text_lines)
                        ocr_engine_used = "PaddleOCR"
                        # logger.debug(f"PaddleOCR extracted text: {ocr_text[:100]}...") # Optional debug
                except Exception as e:
                    logger.warning(f"PaddleOCR failed: {e}. Falling back to Tesseract.")
            
            # Fallback to Tesseract if Paddle failed or wasn't available
            if not ocr_text: 
                try:
                    # --- MODIFIED: Changed --psm 6 to --psm 3 ---
                    ocr_text = pytesseract.image_to_string(
                        processed_img, 
                        lang='eng', 
                        config='--psm 3' # Use automatic page segmentation
                    ) 
                    # --- END OF MODIFICATION ---
                    ocr_engine_used = "Tesseract"
                    # logger.debug(f"Tesseract extracted text: {ocr_text[:100]}...") # Optional debug
                except pytesseract.TesseractNotFoundError:
                     logger.error("Tesseract executable not found. Cannot perform OCR fallback.")
                     return "" # Cannot do OCR at all
                except Exception as e:
                     logger.error(f"Tesseract OCR failed: {e}")
                     return "" # Tesseract also failed

            logger.info(f"OCR completed using {ocr_engine_used}.")
            return ocr_text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

# ... (rest of the extractor.py file remains the same) ...
    def _create_mock_words_from_ocr_text(self, text: str, page_width: float = 612) -> List[Dict]:
        """
        Create mock word objects from OCR text to simulate pdfplumber format.
        """
        words = []
        lines = text.split('\n')
        y_position = 50.0 # Use float
        line_height = 15.0 # Estimated line height
        char_width_est = 6.0 # Estimated avg char width
        word_spacing = 7.0 # Estimated spacing

        for line in lines:
            line = line.strip() # Remove leading/trailing whitespace from line
            if not line:
                y_position += line_height
                continue
                
            line_words = line.split() # Split line into words
            x_position = 50.0 # Start from left margin
            
            for word_text in line_words:
                word_width = len(word_text) * char_width_est
                word_dict = {
                    'text': word_text,
                    'x0': x_position,
                    'x1': x_position + word_width, 
                    'top': y_position,
                    'bottom': y_position + line_height * 0.8, # Approx based on line height
                    'fontname': 'OCR-Default', 
                    'size': 11.0 
                }
                words.append(word_dict)
                x_position += word_width + word_spacing # Move right for next word
            
            y_position += line_height # Move down for next line
        
        return words

    # ============ SCANNED PDF EXTRACTION ============
    def _extract_scanned_pdf(self, file_path: Path) -> ExtractionResult:
        """Extract text from scanned PDF using OCR"""
        logger.info(f"Processing scanned PDF: {file_path.name}")
        
        if not PDF2IMAGE_AVAILABLE:
            logger.error("pdf2image not available. Cannot process scanned PDF.")
            return self._create_empty_result(file_path, "pdf2image_not_available")
        
        # --- ADD YOUR POPPLER BIN PATH HERE ---
        # Example: r"C:\path\to\poppler-23.11.0\Library\bin" 
        # Use None if you want to rely *only* on PATH (less reliable)
        poppler_bin_path = r"C:\path\to\your\poppler\bin" # <--- *** REPLACE THIS ***
        # --- END OF PATH ---
        
        ocr_text = ""
        img_width = 612 # Default width
        num_pages = 1 # Default pages
        ocr_engine_used = "None"
        images = [] # Store images to prevent repeated conversion

        try:
            # Get page count first safely
            try:
                doc = fitz.open(file_path)
                num_pages = len(doc)
                doc.close()
            except Exception as page_count_e:
                 logger.warning(f"Could not get page count via fitz for {file_path.name}: {page_count_e}. Defaulting to 1.")

            # --- MODIFIED: Added poppler_path argument ---
            logger.debug(f"Attempting PDF to image conversion using Poppler path: {poppler_bin_path}")
            try:
                images = convert_from_path(
                    file_path,
                    dpi=300,
                    first_page=1,
                    last_page=1,
                    poppler_path=poppler_bin_path # Explicitly tell pdf2image where Poppler is
                )
            except exceptions.PDFInfoNotInstalledError:
                 logger.error("Poppler's pdfinfo command not found. Check Poppler installation and path.")
                 return self._create_empty_result(file_path, "ocr_error_pdfinfo_missing", pages=num_pages)
            except exceptions.PDFPageCountError:
                 logger.error("Poppler failed to get page count. Check Poppler installation and path.")
                 return self._create_empty_result(file_path, "ocr_error_page_count_failed", pages=num_pages)
            except exceptions.PopplerNotInstalledError:
                 logger.error("Poppler executables (like pdftoppm) not found. Check Poppler installation and path.")
                 return self._create_empty_result(file_path, "ocr_error_poppler_missing", pages=num_pages)
            except Exception as conversion_e: # Catch other conversion errors
                 logger.error(f"pdf2image conversion failed: {conversion_e}")
                 return self._create_empty_result(file_path, f"ocr_error_conversion: {str(conversion_e)}", pages=num_pages)
            # --- END OF MODIFICATION ---
            
            if not images:
                # This case might be hit if the PDF exists but poppler fails silently
                logger.warning(f"convert_from_path returned no images for {file_path.name}.")
                return self._create_empty_result(file_path, "no_images_extracted", pages=num_pages)
            
            img = images[0]
            img_width = img.width 
            
            ocr_text = self._extract_text_from_image_ocr(img)
            # Find which engine was used (for metadata)
            ocr_engine_used = "Tesseract" # Default if Paddle fails/unavailable
            if self.paddle_ocr and ocr_text: # Check if Paddle was tried and succeeded
                 # A bit indirect: assume Paddle was used if available and text was found
                 ocr_engine_used = "PaddleOCR"
            
            if not ocr_text:
                return self._create_empty_result(file_path, "ocr_no_text", pages=num_pages)
            
            mock_words = self._create_mock_words_from_ocr_text(ocr_text, img_width)
            
            column_texts, num_columns = self._cluster_words_into_columns(mock_words, img_width)
            
            _, style_data = self.style_processor.process_word_list(mock_words)
            style_data['ocr_note'] = 'Font information is approximate for OCR-extracted text'
            
            links = self._find_links_pymupdf(file_path) 
            
            metadata = {
                "method": "ocr_scanned_pdf",
                "detected_columns": num_columns,
                "ocr_engine": ocr_engine_used, 
                "column_split_rationale": "Document processed via OCR. Column detection applied to extracted text positions.",
                "extraction_method_analysis": {
                    "pdf2image": "Converted PDF page 1 to image",
                    "ocr": f"{ocr_engine_used} used for text extraction",
                    "kmeans": "K-Means used for column detection hint",
                    "column_split": "Midpoint split applied" if num_columns > 1 else "Single column"
                }
            }
            
            return ExtractionResult(
                source=str(file_path),
                pages=num_pages,
                metadata=metadata,
                column_texts=column_texts,
                style_analysis=style_data,
                links=links
            )
            
        except Exception as e:
            # Catch unexpected errors during the whole process
            logger.error(f"Unhandled error processing scanned PDF {file_path.name}: {e}", exc_info=True) # Log traceback
            return self._create_empty_result(file_path, f"ocr_error_unhandled: {str(e)}", pages=num_pages)
        finally:
             # Clean up image objects if created
             for img in images:
                 try:
                     img.close()
                 except: pass


    # ============ REGULAR PDF EXTRACTION ============
    def _extract_pdfplumber(self, file_path: Path) -> ExtractionResult:
        """Extract text from regular PDF with text layer"""
        links = self._find_links_pymupdf(file_path)
        num_pages = 1 # Default
        
        try:
            with pdfplumber.open(file_path) as pdf:
                num_pages = len(pdf.pages)
                if num_pages == 0:
                     return self._create_empty_result(file_path, "pdf_no_pages", links=links)
                
                # Process only the first page
                page = pdf.pages[0] 
                
                raw_words = page.extract_words(
                    x_tolerance=2,
                    y_tolerance=2,
                    # Crucial for style analysis
                    extra_attrs=["fontname", "size"] 
                )
                
                # Check if pdfplumber found text. If not, maybe it's scanned.
                if not raw_words or len(raw_words) < 20: 
                    # Use the refined scanned check
                    if self._is_pdf_scanned(file_path): 
                        logger.warning(f"PDF {file_path.name} had few/no words via pdfplumber, switching to OCR.")
                        # Rerun as scanned PDF
                        return self._extract_scanned_pdf(file_path) 
                    else:
                         # It's not scanned, but pdfplumber couldn't get words. Return empty.
                         logger.warning(f"PDF {file_path.name} had few/no words, but doesn't seem scanned. Returning empty.")
                         return self._create_empty_result(file_path, "pdfplumber_no_meaningful_words", links=links, pages=num_pages)
                
                # If we got words, proceed with column detection and style
                column_texts, num_columns = self._cluster_words_into_columns(raw_words, page.width)
                _, style_data = self.style_processor.process_word_list(raw_words)
                
                metadata = {
                    "method": "pdfplumber_midpoint_split" if num_columns == 2 else "pdfplumber_single_column",
                    "detected_columns": num_columns,
                    "column_split_rationale": "Detected column layout using K-Means hint and applied midpoint split." if num_columns == 2 else "Single column detected.",
                    "extraction_method_analysis": {
                        "pdfplumber": "Base library used for low-level PDF text and layout extraction.",
                        "kmeans": "K-Means used to detect column layout hint.",
                        "column_split": "Midpoint split applied." if num_columns == 2 else "Single column."
                    }
                }
                
                return ExtractionResult(
                    source=str(file_path),
                    pages=num_pages,
                    metadata=metadata,
                    column_texts=column_texts,
                    style_analysis=style_data,
                    links=links
                )
        except Exception as e:
            logger.error(f"Error processing text PDF {file_path.name}: {e}")
            # If pdfplumber fails catastrophically, try OCR as a last resort
            logger.warning(f"Attempting OCR fallback for {file_path.name} due to pdfplumber error.")
            try:
                return self._extract_scanned_pdf(file_path)
            except Exception as ocr_fallback_e:
                 logger.error(f"OCR fallback also failed for {file_path.name}: {ocr_fallback_e}")
                 return self._create_empty_result(file_path, f"pdfplumber_error: {str(e)}", links=links, pages=num_pages)


    # ============ DOCX EXTRACTION ============
    def _extract_docx(self, file_path: Path) -> ExtractionResult:
        """Extract text and style from DOCX files"""
        logger.info(f"Processing DOCX file: {file_path.name}")
        
        if not DOCX_AVAILABLE:
            logger.error("python-docx not available. Cannot process DOCX.")
            return self._create_empty_result(file_path, "docx_not_available")
        
        words = [] # Store mock word dicts
        links = [] # Store links
        
        try:
            doc = docx.Document(file_path)
            
            y_position = 50.0
            line_height = 15.0
            char_width_est = 6.0
            word_spacing = 7.0

            # Extract text run by run to get basic style info
            for para in doc.paragraphs:
                if not para.text.strip():
                    y_position += line_height # Add space for empty paragraphs
                    continue
                
                x_position = 50.0 # Reset X for new paragraph
                
                for run in para.runs:
                    run_text = run.text.strip()
                    if not run_text:
                        continue
                    
                    # Approximate font info
                    font_name = run.font.name or 'Calibri' # Default if None
                    font_size = 11.0 # Default
                    if run.font.size and hasattr(run.font.size, 'pt'):
                         try:
                              font_size = float(run.font.size.pt)
                         except: pass # Keep default if conversion fails

                    # Create mock words for this run
                    run_words_text = run_text.split()
                    for word_text in run_words_text:
                        word_width = len(word_text) * char_width_est
                        word_dict = {
                            'text': word_text,
                            'x0': x_position,
                            'x1': x_position + word_width,
                            'top': y_position,
                            'bottom': y_position + line_height * 0.8,
                            'fontname': font_name,
                            'size': font_size
                        }
                        words.append(word_dict)
                        x_position += word_width + word_spacing
                
                y_position += line_height # Move down after processing paragraph runs
            
            if not words:
                return self._create_empty_result(file_path, "docx_empty")
            
            # --- Link Extraction for DOCX using rels (more reliable) ---
            try:
                # Access relationships from the main document part
                for rel_id, rel in doc.part.rels.items():
                    if "hyperlink" in rel.reltype:
                        # Find the run(s) associated with this relationship ID 
                        # This part is complex and often unreliable with python-docx alone.
                        # We'll just extract the URL target from rels.
                        link_url = rel.target_ref
                        if link_url and not link_url.startswith('mailto:'): # Ignore mailto links for now
                            links.append({
                                'url': link_url,
                                'page': 1, # DOCX doesn't have clear pages like PDF
                                'rect': [] # No reliable coordinates
                            })
            except Exception as rel_e:
                logger.warning(f"Could not extract hyperlinks using rels for {file_path.name}: {rel_e}")
             # De-duplicate links from rels
            unique_links = []
            seen_urls = set()
            for link in links:
                if link['url'] not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(link['url'])
            links = unique_links
            # --- End Link Extraction ---


            # Assume standard page width for column detection
            page_width_approx = 612.0 
            column_texts, num_columns = self._cluster_words_into_columns(words, page_width_approx)
            
            # Use style processor with the created mock words
            _, style_data = self.style_processor.process_word_list(words)
            style_data['docx_note'] = 'Font/size info extracted directly from DOCX runs.'
            
            metadata = {
                "method": "docx_extraction",
                "detected_columns": num_columns,
                "extraction_method_analysis": {
                    "python_docx": "Used for DOCX text and basic style parsing",
                    "kmeans": "K-Means used for column detection hint on mock word positions",
                    "column_split": "Midpoint split applied" if num_columns > 1 else "Single column"
                }
            }
            
            # Approximate page count (often just 1 for simple reads)
            num_pages = 1 
            try:
                # This is a rough estimate based on sections, not accurate pages
                num_pages = len(doc.sections) if doc.sections else 1
            except: pass

            return ExtractionResult(
                source=str(file_path),
                pages=num_pages, 
                metadata=metadata,
                column_texts=column_texts,
                style_analysis=style_data,
                links=links
            )
            
        except Exception as e:
            logger.error(f"Error processing DOCX {file_path.name}: {e}")
            return self._create_empty_result(file_path, f"docx_error: {str(e)}")

    # ============ IMAGE EXTRACTION ============
    def _extract_image(self, file_path: Path) -> ExtractionResult:
        """Extract text from image files using OCR"""
        logger.info(f"Processing image file: {file_path.name}")
        
        try:
            img = Image.open(file_path)
            img_width = img.width # Get width for column calc
            
            # Ensure RGB for OCR processing consistency
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            ocr_text = self._extract_text_from_image_ocr(img)
            ocr_engine_used = "PaddleOCR" if self.paddle_ocr else "Tesseract"
            if not ocr_text and self.paddle_ocr: # If Paddle failed, Tesseract ran
                 ocr_engine_used = "Tesseract"

            if not ocr_text:
                return self._create_empty_result(file_path, "image_ocr_no_text")
            
            mock_words = self._create_mock_words_from_ocr_text(ocr_text, img_width)
            
            column_texts, num_columns = self._cluster_words_into_columns(mock_words, img_width)
            
            _, style_data = self.style_processor.process_word_list(mock_words)
            style_data['ocr_note'] = 'Font information is approximate for OCR-extracted text'
            
            metadata = {
                "method": "image_ocr",
                "detected_columns": num_columns,
                "ocr_engine": ocr_engine_used,
                "image_size": f"{img.width}x{img.height}",
                "extraction_method_analysis": {
                    "PIL": "Image loaded with PIL",
                    "ocr": f"{ocr_engine_used} used for text extraction",
                    "kmeans": "K-Means used for column detection hint",
                    "column_split": "Midpoint split applied" if num_columns > 1 else "Single column"
                }
            }
            
            return ExtractionResult(
                source=str(file_path),
                pages=1, # Images are single page
                metadata=metadata,
                column_texts=column_texts,
                style_analysis=style_data,
                links=[]  # Images don't have embedded hyperlinks
            )
            
        except Exception as e:
            logger.error(f"Error processing image {file_path.name}: {e}")
            return self._create_empty_result(file_path, f"image_error: {str(e)}")
        finally:
            try: # Ensure image file handle is closed
                 if 'img' in locals() and img: img.close()
            except: pass

    # ============ HELPER FUNCTIONS ============
    def _create_empty_result(self, file_path: Path, error_msg: str, links: List = None, pages: int = 0) -> ExtractionResult:
        """Create an empty result for failed extractions"""
        empty_style = {
            "bullet_points_used": "no",
            "unwanted_icon_used": "false",
            "font_types_used": [],
            "font_sizes_used": []
        }
        # Ensure pages isn't negative if passed incorrectly
        pages = max(0, pages) 
        return ExtractionResult(
            source=str(file_path),
            pages=pages, # Use provided page count or default 0
            metadata={"method": "error", "error": error_msg},
            column_texts=[""], # Ensure column_texts is always a list with at least one string
            style_analysis=empty_style,
            links=links if links is not None else [] # Use provided links or default empty list
        )

    # ============ MAIN EXTRACT METHOD ============
    def extract(self, file_path: Path) -> ExtractionResult:
        """Main extraction dispatcher based on file type"""
        ext = file_path.suffix.lower()
        logger.info(f"Dispatching extraction for: {file_path.name} (type: {ext})")
        
        # PDF files
        if ext == '.pdf':
            # Use the refined check which also logs its reasoning
            if self._is_pdf_scanned(file_path): 
                return self._extract_scanned_pdf(file_path)
            else:
                return self._extract_pdfplumber(file_path)
        
        # DOCX files
        elif ext == '.docx':
             # Ensure library is available before attempting
            if DOCX_AVAILABLE:
                return self._extract_docx(file_path)
            else:
                 logger.error(f"Skipping {file_path.name}: python-docx library not installed.")
                 return self._create_empty_result(file_path, "docx_library_missing")

        # Handle .doc by logging a warning
        elif ext == '.doc':
             logger.warning(f".doc file detected ({file_path.name}). Skipping. Please convert to .docx or .pdf.")
             return self._create_empty_result(file_path, "Unsupported .doc file. Please convert to .docx.")

        # Image files
        elif ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']: # Added GIF
            return self._extract_image(file_path)
        
        # Catchall for unsupported types
        else:
            logger.warning(f"Unsupported file type: {ext} for file {file_path.name}")
            return self._create_empty_result(
                file_path, 
                f"File type {ext} not supported. Supported: .pdf, .docx, .jpg, .jpeg, .png, .tiff, .bmp, .gif"
            )

    def process_and_save(self, file_path: str) -> str:
        """Process file and save result to JSONL"""
        file_path_obj = Path(file_path) # Work with Path object
        result = self.extract(file_path_obj)
        # Ensure output directory exists right before writing
        self.output_dir.mkdir(parents=True, exist_ok=True) 
        output_file = self.output_dir / (file_path_obj.stem + ".jsonl")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.to_jsonl())
            logger.info(f"✅ Saved: {output_file}")
            return str(output_file)
        except Exception as e:
             logger.error(f"Failed to save JSONL for {file_path_obj.name}: {e}")
             return "" # Return empty string on save failure


# ============ CLI ============
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m extractor.extractor <input_pattern_or_directory>")
        print("Supported formats: PDF (text/scanned), DOCX, JPG, JPEG, PNG, TIFF, BMP, GIF")
        sys.exit(1)
    
    input_patterns = sys.argv[1:]
    files_to_process = []
    
    for pattern in input_patterns:
         path = Path(pattern)
         if path.is_dir():
              logger.info(f"Searching directory: {path}")
              # Add files directly from directory, checking extensions
              supported_exts = ['.pdf', '.docx', '.doc', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']
              for item in path.iterdir():
                   if item.is_file() and item.suffix.lower() in supported_exts:
                        files_to_process.append(str(item))
         elif path.is_file():
              logger.info(f"Processing single file: {path}")
              files_to_process.append(str(path))
         else: # Assume it's a glob pattern
              logger.info(f"Searching pattern: {pattern}")
              found_files = glob.glob(pattern)
              if found_files:
                  files_to_process.extend(found_files)
              else:
                   logger.warning(f"No files matched pattern: {pattern}")

    if not files_to_process:
        print("No files found to process.")
        sys.exit(1)
    
    print(f"Found {len(files_to_process)} files to process.")
    extractor = Extractor() # Uses default output dir "data/downloads"
    
    processed_count = 0
    for file_path_str in files_to_process:
        try:
            # Add a check for file existence before processing
            if not Path(file_path_str).exists():
                 logger.warning(f"File not found, skipping: {file_path_str}")
                 continue
            extractor.process_and_save(file_path_str)
            processed_count += 1
        except Exception as e:
             logger.error(f"Unhandled exception during processing of {file_path_str}: {e}")

    print(f"Processed {processed_count} files.")