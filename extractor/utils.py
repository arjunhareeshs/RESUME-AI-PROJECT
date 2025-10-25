# extractor/utils.py
from pathlib import Path
from typing import Iterator
import os

def iter_files(directory: str, extensions=None):
    extensions = extensions or [".pdf", ".docx", ".jpg", ".jpeg", ".png", ".tiff", ".bmp"]
    p = Path(directory)
    for f in p.rglob("*"):
        if f.is_file() and f.suffix.lower() in extensions:
            yield str(f)
