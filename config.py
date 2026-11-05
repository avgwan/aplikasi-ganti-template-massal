import sys
from pathlib import Path
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

BASE_IMAGE_DIR = BASE_DIR / 'hasil-gambar'
TEMPLATE_DIR = BASE_DIR / 'template'
OUTPUT_DIR = BASE_DIR / 'hasil-gambar'
SIZE_STANDARD = (1080, 1080)  

MAX_WORKERS_REMBG   = max(2, (os.cpu_count() or 4))
MAX_WORKERS_COMPOSE = max(2, (os.cpu_count() or 4) // 2)
