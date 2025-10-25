# extractor/extractor.py
import io
import logging
from pathlib import Path
from typing import Tuple, Optional

import fitz  # PyMuPDF
import pdfplumber
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
    Unified extractor for PDFs, DOCX and images.
    Strategy:
      - For PDF: Try text layer via PyMuPDF; if empty page -> OCR that page
      - For DOCX: python-docx
      - For images: run preprocessing -> pytesseract
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
        text_chunks = []
        pages_count = 0
        try:
            with fitz.open(path) as doc:
                pages_count = doc.page_count
                for page_no in range(doc.page_count):
                    page = doc.load_page(page_no)
                    page_text = page.get_text("text").strip()
                    if page_text:
                        text_chunks.append(page_text)
                    else:
                        # fallback to raster + OCR
                        pix = page.get_pixmap(dpi=200)
                        img = Image.open(io.BytesIO(pix.tobytes()))
                        img = preprocess_image_for_ocr(img)
                        ocr_text = pytesseract.image_to_string(img, lang=self.ocr_lang, config=self.ocr_config)
                        text_chunks.append(ocr_text)
        except Exception as e:
            logger.warning("PyMuPDF extraction failed, trying pdfplumber fallback: %s", e)
            # fallback: pdfplumber (useful for some edge cases)
            with pdfplumber.open(path) as pdf:
                pages_count = len(pdf.pages)
                for pg in pdf.pages:
                    t = pg.extract_text()
                    if t:
                        text_chunks.append(t)
                    else:
                        pil = pg.to_image(resolution=200).original
                        pil = preprocess_image_for_ocr(pil)
                        text_chunks.append(pytesseract.image_to_string(pil, lang=self.ocr_lang, config=self.ocr_config))

        full_text = "\n\n".join(chunk for chunk in text_chunks if chunk and chunk.strip())
        return ExtractionResult(text=full_text, source=str(path), pages=pages_count,
                                metadata={"method": "pymupdf+ocr_fallback"})

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
