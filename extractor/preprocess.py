# extractor/preprocess.py

import numpy as np
from PIL import Image, ImageFilter, ImageOps

def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """
    Cleans and optimizes a PIL Image object for better OCR accuracy.
    """
  
    # 1. Convert to grayscale ('L' mode)
    # OCR works best on black-and-white images.
    img = img.convert("L")

    # 2. Resize if the image is very small
    # OCR models are often trained on images of a certain size.
    # Upscaling a small image can improve recognition.
    max_dim = max(img.size)
    if max_dim < 1000:
        scale = 1000 / max_dim
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.LANCZOS) # Use high-quality resampling

    # 3. Apply an optional sharpening filter
    # This can help make blurry text more distinct.
    img = img.filter(ImageFilter.SHARPEN)

    # 4. Apply a simple threshold
    # This converts the grayscale image to pure black-and-white,
    # removing shadows and noise.
    arr = np.array(img)
    
    # This logic thresholds the image based on its median brightness,
    # which is a good way to handle varying brightness levels.
    med = np.median(arr)
    thresh = med * 0.9  # A tunable threshold
    bin_arr = (arr > thresh) * 255
    
    # 5. Convert back to a PIL Image
    out = Image.fromarray(bin_arr.astype('uint8'))
    return out