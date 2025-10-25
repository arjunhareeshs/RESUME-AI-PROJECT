# extractor/preprocess.py
from PIL import Image, ImageFilter, ImageOps
import numpy as np

def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """
    Basic preprocessing chain that helps OCR accuracy:
      - convert to grayscale
      - apply adaptive-like thresholding (lightweight)
      - optionally sharpen
      - resize small images
    """
    # convert to grayscale
    img = img.convert("L")

    # Resize if very small (improves recognition)
    max_dim = max(img.size)
    if max_dim < 1000:
        scale = 1000 / max_dim
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size)

    # optional sharpening
    img = img.filter(ImageFilter.SHARPEN)

    # simple thresholding using numpy (works well for many resumes)
    arr = np.array(img)
    # compute median and threshold at median * 0.9 (tunable)
    med = np.median(arr)
    thresh = med * 0.9
    bin_arr = (arr > thresh) * 255
    out = Image.fromarray(bin_arr.astype('uint8'))
    return out
