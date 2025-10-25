# extractor/extractor.py (REVISED)
import io
import logging
from pathlib import Path
from typing import Optional, List

# --- New Imports for pdfminer.six ---
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
# ------------------------------------

import fitz  # PyMuPDF (Still needed for the OCR fallback)
from PIL import Image
import pytesseract
import docx
from .preprocess import preprocess_image_for_ocr

logger = logging.getLogger("resume_extractor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)


class ExtractionResult:
    def __init__(self, text: str, source: str, pages: int = 0, metadata: Optional[dict] = None):
        self.text = text
        self.source = source
        self.pages = pages
        self.metadata = metadata or {}


class ResumeExtractor:
    """
    Unified extractor for PDFs (using pdfminer.six), DOCX and images.
    """
    def __init__(self, ocr_lang: str = "eng", ocr_config: str = "--psm 3"):
        self.ocr_lang = ocr_lang
        self.ocr_config = ocr_config

    def extract(self, file_path: str) -> ExtractionResult:
        p = Path(file_path)
        ext = p.suffix.lower()
        if ext == ".pdf":
            return self._extract_pdf(p)
        elif ext in [".docx"]:
            return self._extract_docx(p)
        elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
            return self._extract_image(p)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf(self, path: Path) -> ExtractionResult:
        """
        Extracts text from PDF using pdfminer.six for layout preservation.
        Falls back to PyMuPDF/OCR for image-only pages.
        """
        text_chunks: List[str] = []
        pages_count = 0
        is_searchable = False

        try:
            # --- Primary Extraction: pdfminer.six for Layout ---
            output_string = io.StringIO()
            
            # Key step: Using LAParams for layout analysis
            laparams = LAParams(
                line_overlap=0.5,
                char_margin=2.0,
                word_margin=0.1,
                line_margin=0.5,
                boxes_flow=0.5, # Try 0.5 for left-to-right, top-to-bottom flow
                detect_vertical=False,
                all_texts=False
            )

            with open(path, 'rb') as fp:
                extract_text_to_fp(fp, output_string, laparams=laparams)
            
            pdfminer_text = output_string.getvalue()

            if pdfminer_text and not pdfminer_text.isspace():
                is_searchable = True
                text_chunks.append(pdfminer_text)
                with fitz.open(path) as doc: # Use fitz just to get page count
                    pages_count = doc.page_count
                
            else:
                # --- Fallback: If pdfminer.six finds no text, the PDF is likely a scan ---
                logger.warning(f"No text layer found in {path.name}. Falling back to OCR.")
                
                with fitz.open(path) as doc:
                    pages_count = doc.page_count
                    for page_no in range(pages_count):
                        page = doc.load_page(page_no)
                        
                        # Check if page itself has any text first
                        if page.get_text("text"):
                            is_searchable = True # At least one page has text
                        
                        # Rasterize page and run OCR
                        pix = page.get_pixmap(dpi=300) # Higher DPI for better OCR
                        img = Image.open(io.BytesIO(pix.tobytes()))
                        img = preprocess_image_for_ocr(img)
                        ocr_text = pytesseract.image_to_string(img, lang=self.ocr_lang, config=self.ocr_config)
                        text_chunks.append(ocr_text)

        except Exception as e:
            logger.error(f"Critical PDF extraction failure for {path.name}: {e}")
            return ExtractionResult(text="", source=str(path), pages=0, metadata={"method": "failure"})

        full_text = "\n\n".join(chunk for chunk in text_chunks if chunk and chunk.strip())
        method = "pdfminer_six" if is_searchable else "ocr_fallback"
        
        return ExtractionResult(text=full_text, source=str(path), pages=pages_count,
                                 metadata={"method": method})

    def _extract_docx(self, path: Path) -> ExtractionResult:
        doc = docx.Document(path)
        paras = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        text = "\n".join(paras)
        return ExtractionResult(text=text, source=str(path), pages=0, metadata={"method": "docx"})

    def _extract_image(self, path: Path) -> ExtractionResult:
        img = Image.open(path)
        img = preprocess_image_for_ocr(img)
        text = pytesseract.image_to_string(img, lang=self.ocr_lang, config=self.ocr_config)
        return ExtractionResult(text=text, source=str(path), pages=1, metadata={"method": "image_ocr"})