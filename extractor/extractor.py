# extractor/extractor.py (K-Means + Vertical Zoning + Text Only + Link Extraction)
import json
import logging
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Optional, Dict, Any
import sys
import glob

import pdfplumber
import fitz # <-- 1. IMPORT PyMuPDF
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# OCR tools
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    
import pytesseract
from PIL import Image

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

# --- Other File Types ---
import docx

# --- Preprocessing ---
try:
    from .preprocess import preprocess_image_for_ocr
except ImportError:
    logging.warning("Could not import preprocess_image_for_ocr. OCR accuracy may be reduced.")
    def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
        return img.convert("L")

# --- Import the Style Processor ---
try:
    from .style_processor import StyleProcessor
except ImportError:
    logger = logging.getLogger("resume_extractor_import")
    logger.critical("FATAL: Failed to import 'StyleProcessor' from .style_processor.py.")
    raise

# ---------------- Logger ----------------
logger = logging.getLogger("resume_extractor_kmeans")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
logger.addHandler(handler)

# ---------------- Helper Classes ----------------
class ExtractionResult:
    """Data container for structured JSONL output."""
    def __init__(self, source: str, pages: int, metadata: dict, 
                 column_texts: List[str],
                 links: List[Dict] = None): # <-- 2. ADD links parameter
                 
        self.source = str(source)
        self.pages = pages
        self.metadata = metadata
        self.column_texts = [t.strip() for t in column_texts]
        self.links = links if links is not None else [] # <-- 2. ADD links field
        
        self.text = "\n\n--- Column Break ---\n\n".join(self.column_texts)

    def to_jsonl(self) -> str:
        data = {
            "source": self.source,
            "pages": self.pages,
            "metadata": self.metadata,
            "column_texts": self.column_texts,
            "links": self.links, # <-- 3. ADD links to JSON
            "combined_text": self.text,
        }
        return json.dumps(data, ensure_ascii=False, default=float)


# ---------------- Main Extractor ----------------
class ResumeExtractor:
    def __init__(self, output_dir: str = "./extracted_resumes", ocr_lang: str = "eng"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_lang = ocr_lang
        self.paddle = None
        
        self.style_processor = StyleProcessor()
        
        if PADDLE_AVAILABLE:
            try:
                self.paddle = PaddleOCR(lang='en', use_textline_orientation=True)
                logger.info("✅ PaddleOCR initialized.")
            except Exception as e:
                logger.warning(f"⚠️ PaddleOCR init failed: {e}")
        
        if not PDF2IMAGE_AVAILABLE:
            logger.error("pdf2image not found. PDF OCR fallback will fail.")

    # -------------- Column Detection (Unchanged) --------------
    def detect_column_labels_kmeans(self, words: List[Dict], page_bbox: tuple, max_cols: int = 3) -> (int, List[int]):
        page_x0, _, page_x1, _ = page_bbox

        if not words or len(words) < 10:
            return 1, [0] * len(words)

        x_positions = np.array([[(w["x0"] + w["x1"]) / 2] for w in words])

        best_k, best_score, best_labels = 1, -1, None
        
        for k in range(1, min(max_cols, len(x_positions) // 2) + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
            labels = kmeans.fit_predict(x_positions)

            if k == 1:
                best_k, best_labels = 1, labels
                continue
            
            try:
                score = silhouette_score(x_positions, labels)
                if k == 2:
                    score *= 1.1 
                
                if score > best_score:
                    best_k, best_score, best_labels = k, score, labels
            except ValueError:
                continue
        
        return best_k, best_labels

    # -------------- PDF Extraction (Modified) --------------
    
    def extract_pdf(self, file_path: Path) -> ExtractionResult:
        final_column_texts = []
        links_data = []
        pdf_pages_count = 0
        metadata = {"method": "failure"} # Default metadata

        try:
            # --- Step 1: Extract Text using pdfplumber ---
            with pdfplumber.open(file_path) as pdf:
                pdf_pages_count = len(pdf.pages)
                max_cols_detected = 1
                
                # First pass for column detection
                for page in pdf.pages:
                    header_height = page.height * 0.18 
                    body_top = page.bbox[1] + header_height
                    body_crop = page.crop((page.bbox[0], body_top, page.bbox[2], page.bbox[3]))
                    words = body_crop.extract_words()
                    k, _ = self.detect_column_labels_kmeans(words, body_crop.bbox)
                    max_cols_detected = max(max_cols_detected, k)
                
                logger.info(f"📄 Document has a maximum of {max_cols_detected} column(s).")
                
                final_column_word_buckets = [[] for _ in range(max_cols_detected)]

                # Second pass for text extraction
                for page_num, page in enumerate(pdf.pages, start=1):
                    header_height = page.height * 0.18
                    body_top = page.bbox[1] + header_height
                    header_crop = page.crop((page.bbox[0], page.bbox[1], page.bbox[2], body_top))
                    body_crop = page.crop((page.bbox[0], body_top, page.bbox[2], page.bbox[3]))
                    
                    header_words = header_crop.extract_words()
                    final_column_word_buckets[0].extend(header_words)
                    
                    body_words = body_crop.extract_words()
                    k, labels = self.detect_column_labels_kmeans(body_words, body_crop.bbox)

                    column_word_buckets = defaultdict(list)
                    for word, label in zip(body_words, labels):
                        column_word_buckets[label].append(word)
                    
                    sorted_buckets = sorted(column_word_buckets.items(), key=lambda item: item[1][0]['x0'] if item[1] else 0)
                    is_full_width_body = (k < max_cols_detected)

                    for i, (label, col_words) in enumerate(sorted_buckets):
                        if is_full_width_body:
                            final_column_word_buckets[0].extend(col_words)
                        else:
                            if i < len(final_column_word_buckets): 
                                final_column_word_buckets[i].extend(col_words)

                # Process buckets into text
                for word_bucket in final_column_word_buckets:
                    plain_text = self.style_processor.process_word_list(word_bucket)
                    final_column_texts.append(plain_text)
                
                metadata = {"method": "pdfplumber_kmeans_zoned", "detected_columns": max_cols_detected}

                # --- Step 2: Extract Links using fitz ---
                try:
                    doc = fitz.open(file_path)
                    for page_num, page in enumerate(doc):
                        page_links = page.get_links() # Get list of link dictionaries
                        for link in page_links:
                            # 'uri' is the URL, 'from' is the Rect where the link is
                            if link.get('kind') == fitz.LINK_URI and link.get('uri'):
                                links_data.append({
                                    "url": link['uri'],
                                    "page": page_num + 1,
                                    "rect": list(link['from']) # Convert Rect to list for JSON
                                })
                    doc.close()
                    logger.info(f"🔗 Extracted {len(links_data)} links using fitz.")
                except Exception as link_e:
                    logger.warning(f"⚠️ Could not extract links using fitz: {link_e}")
                    # Continue without links if this part fails
            
            # --- Step 3: OCR Fallback Check ---
            if not any(t.strip() for t in final_column_texts):
                logger.warning("⚠️ No text detected via pdfplumber. Using OCR fallback...")
                # Note: OCR fallback doesn't extract links
                return self.extract_pdf_ocr(file_path)

            # --- Step 4: Return combined result ---
            return ExtractionResult(
                source=file_path,
                pages=pdf_pages_count,
                metadata=metadata,
                column_texts=final_column_texts,
                links=links_data # Pass the extracted links
            )

        except Exception as e:
            logger.exception(f"❌ PDF Extraction failed: {e}") 
            # Return error result, ensuring links field exists
            return ExtractionResult(
                source=file_path, pages=0,
                metadata={"method": "failure", "error": str(e)},
                column_texts=[""],
                links=[] 
            )

    # -------------- OCR Fallback (Modified to return links field) --------------
    def extract_pdf_ocr(self, file_path: Path) -> ExtractionResult:
        if not PDF2IMAGE_AVAILABLE:
            return ExtractionResult(
                source=file_path, pages=0,
                metadata={"method": "ocr_fallback_error", "error": "pdf2image not found"},
                column_texts=[""], links=[]
            )
            
        try:
            images = convert_from_path(file_path, dpi=300)
            texts = []
            # ... (rest of OCR logic is unchanged) ...
            if self.paddle:
                for i, img in enumerate(images):
                    logger.info(f"Running PaddleOCR on page {i+1}...")
                    np_img = np.array(img)
                    result = self.paddle.ocr(np_img)
                    lines = [line[1][0] for line in result[0]] if result else []
                    texts.append(f"--- Page {i+1} ---\n" + "\n".join(lines))
            else:
                logger.info("PaddleOCR not found, using Tesseract.")
                for i, img in enumerate(images):
                    logger.info(f"Running Tesseract OCR on page {i+1}...")
                    img = preprocess_image_for_ocr(img)
                    text = pytesseract.image_to_string(img, lang=self.ocr_lang)
                    texts.append(f"--- Page {i+1} ---\n{text}")


            # Return OCR result, indicating no links extracted
            return ExtractionResult(
                source=file_path, pages=len(images),
                metadata={"method": "ocr_fallback", "engine": "paddle" if self.paddle else "tesseract"},
                column_texts=texts,
                links=[] # OCR doesn't provide links
            )
        except Exception as e:
            logger.error(f"OCR fallback failed: {e}")
            return ExtractionResult(
                source=file_path, pages=0,
                metadata={"method": "ocr_fallback_error", "error": str(e)},
                column_texts=[""], links=[]
            )

    # -------------- Other File Handlers (Modified to return links field) --------------
    
    def extract_docx(self, file_path: Path) -> ExtractionResult:
        # DOCX doesn't have the same link structure as PDF
        try:
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs if p.text])
            return ExtractionResult(
                source=file_path, pages=0,
                metadata={"method": "docx"},
                column_texts=[text],
                links=[] # No links extracted from DOCX
            )
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return ExtractionResult(
                source=file_path, pages=0,
                metadata={"method": "docx_error", "error": str(e)},
                column_texts=[""], links=[]
            )

    def extract_image(self, file_path: Path) -> ExtractionResult:
        # Images don't have embedded links
        try:
            img = Image.open(file_path)
            text = ""
            # ... (rest of image OCR logic is unchanged) ...
            if self.paddle:
                logger.info("Running PaddleOCR on image...")
                np_img = np.array(img)
                result = self.paddle.ocr(np_img)
                lines = [line[1][0] for line in result[0]] if result else []
                text = "\n".join(lines)
            else:
                logger.info("PaddleOCR not found, using Tesseract on image...")
                img = preprocess_image_for_ocr(img)
                text = pytesseract.image_to_string(img, lang=self.ocr_lang)


            return ExtractionResult(
                source=file_path, pages=1,
                metadata={"method": "image_ocr", "engine": "paddle" if self.paddle else "tesseract"},
                column_texts=[text],
                links=[] # No links extracted from images
            )
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
            return ExtractionResult(
                source=file_path, pages=1,
                metadata={"method": "image_error", "error": str(e)},
                column_texts=[""], links=[]
            )

    # -------------- Main Entry Point (Unchanged) --------------
    
    def extract(self, file_path: Path) -> ExtractionResult:
        """Main routing function to select the correct extractor."""
        ext = file_path.suffix.lower()
        
        if ext == ".pdf":
            return self.extract_pdf(file_path)
        elif ext == ".docx":
            return self.extract_docx(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
            return self.extract_image(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            # Return with empty links
            return ExtractionResult(
                source=file_path, pages=0,
                metadata={"method": "unsupported_type", "error": f"File type {ext} not supported."},
                column_texts=[""], links=[]
            )

    def process_and_save(self, file_path: str) -> str:
        file_path = Path(file_path)
        result = self.extract(file_path) # This result object now includes links
        
        output_file = self.output_dir / f"{file_path.stem}.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result.to_jsonl()) # .to_jsonl() now includes links
            
        logger.info(f"✅ Saved: {output_file}")
        return str(output_file)

# -------------- CLI Usage (Unchanged) --------------
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

    extractor = ResumeExtractor(output_dir="data/downloads")
    for file in files:
        print(f"Processing: {file}")
        try:
            extractor.process_and_save(file)
        except Exception as e:
            print(f"   -> FAILED: {e}")