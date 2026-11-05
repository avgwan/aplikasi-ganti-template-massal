import sys
from pathlib import Path
from PIL import Image
from config import TEMPLATE_DIR, OUTPUT_DIR

def log_msg(msg: str) -> None:
    print(msg, flush=True)

def ensure_directories() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

def numerical_sort_key(path: Path):
    stem = path.stem
    if stem.isdigit():
        return (0, int(stem))
    return (1, stem.lower())

def get_resample_method():
    return getattr(Image, 'Resampling', Image).LANCZOS