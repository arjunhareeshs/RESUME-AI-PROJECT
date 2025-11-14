from typing import List, Dict, Tuple, Optional, Set

# PaddleOCR (primary OCR engine) - defer import to runtime to avoid startup crashes
PaddleOCR = None  # type: ignore

# Tesseract (fallback / supplementary OCR)
try:
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover - handled gracefully
    pytesseract = None  # type: ignore
    Image = None  # type: ignore

# Lazy-loaded singleton to avoid re-initialising the heavy Paddle model
_paddle_ocr_instance: Optional[PaddleOCR] = None  # type: ignore

def _get_paddle_ocr() -> PaddleOCR:
    """
    Initialise (if needed) and return the shared PaddleOCR instance.
    Raises informative error if PaddleOCR or PaddlePaddle is not installed.
    """
    global _paddle_ocr_instance

    # Import here to catch any binary/runtime issues without breaking app import
    try:
        from paddleocr import PaddleOCR as _PaddleOCR  # type: ignore
    except Exception as e:
        raise ImportError(
            "PaddleOCR (and its dependencies) are unavailable.\n"
            "To enable image OCR, install compatible packages, e.g.:\n"
            "  pip install --upgrade pip setuptools wheel\n"
            "  pip install paddlepaddle paddleocr\n"
            "On Windows/Conda, prefer conda-forge builds for numpy/scikit-image to avoid ABI issues.\n"
            f"Original import error: {e}"
        )

    if _paddle_ocr_instance is None:
        _paddle_ocr_instance = _PaddleOCR(use_angle_cls=True, lang="en")

    return _paddle_ocr_instance


def _paddle_blocks(file_path: str) -> List[Dict]:
    """
    Run PaddleOCR on the image and convert results into our uniform block schema.
    """
    ocr = _get_paddle_ocr()
    result = ocr.ocr(file_path, cls=True)

    blocks: List[Dict] = []
    for page in result:
        for line in page:
            bbox, (text, confidence) = line
            # bbox is a list of 4 points [ [x, y], ... ]
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            blocks.append({
                "text": text.strip(),
                "x0": float(min(xs)),
                "y0": float(min(ys)),
                "x1": float(max(xs)),
                "y1": float(max(ys)),
                "confidence": float(confidence),
                "engine": "paddleocr",
            })
    return blocks


def _tesseract_blocks(file_path: str) -> List[Dict]:
    """
    Optional supplementary OCR using Tesseract (if installed and configured).
    """
    if pytesseract is None or Image is None:
        return []

    image = Image.open(file_path)
    data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT  # type: ignore[attr-defined]
    )

    blocks: List[Dict] = []
    n_boxes = len(data["text"])
    for i in range(n_boxes):
        text = data["text"][i].strip()
        if not text:
            continue
        x, y, w, h = (
            data["left"][i],
            data["top"][i],
            data["width"][i],
            data["height"][i],
        )
        conf = data.get("conf", ["0"] * n_boxes)[i]
        try:
            confidence = float(conf)
        except (TypeError, ValueError):
            confidence = -1.0

        blocks.append({
            "text": text,
            "x0": float(x),
            "y0": float(y),
            "x1": float(x + w),
            "y1": float(y + h),
            "confidence": confidence,
            "engine": "tesseract",
        })
    return blocks


def _deduplicate_blocks(blocks: List[Dict]) -> List[Dict]:
    """
    Deduplicate overlapping results coming from multiple OCR engines by (text, bbox).
    """
    seen: Set[Tuple[str, float, float, float, float]] = set()
    unique_blocks: List[Dict] = []
    for block in blocks:
        key = (
            block["text"],
            round(block["x0"], 2),
            round(block["y0"], 2),
            round(block["x1"], 2),
            round(block["y1"], 2),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_blocks.append(block)
    return unique_blocks


async def extract(file_path: str, use_tesseract: bool = True) -> List[Dict]:
    """
    Extract text blocks from an image using PaddleOCR, optionally supplemented by Tesseract.

    Args:
        file_path: Path to the image file (JPEG/PNG).
        use_tesseract: Whether to run Tesseract in addition to PaddleOCR.

    Returns:
        List of block dictionaries with text, coordinates, confidence, and engine.
    """
    paddle_results = _paddle_blocks(file_path)
    tesseract_results: List[Dict] = []

    if use_tesseract:
        tesseract_results = _tesseract_blocks(file_path)

    combined = paddle_results + tesseract_results
    return _deduplicate_blocks(combined)