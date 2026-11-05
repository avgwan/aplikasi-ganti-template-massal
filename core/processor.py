import io
import concurrent.futures
from pathlib import Path
from typing import List, Tuple, Callable, Optional, Union, Any
from PIL import Image, ImageOps
from rembg import remove


from config import SIZE_STANDARD, MAX_WORKERS_REMBG, MAX_WORKERS_COMPOSE
from utils.helpers import get_resample_method, numerical_sort_key
from core.pdf import create_pdf_from_folder
from core.cancel import ProcessCancelled, check_cancel

def _log(callback: Optional[Callable], message: str, progress: Optional[float] = None):
    if callback:
        callback(message, progress)

def _process_single_rembg(src_path: Path, dst_path: Path, cancel_event=None) -> Tuple[Path, bool, str]:
    if cancel_event is not None and cancel_event.is_set():
        return (dst_path, False, "dibatalkan")
    try:
        with open(src_path, "rb") as file:
            data = file.read()

        output_data = remove(data)

        with Image.open(io.BytesIO(output_data)) as img:
            img = img.convert("RGBA")
            img = ImageOps.contain(img, SIZE_STANDARD, method=get_resample_method())
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(dst_path, "PNG")
            
        return (dst_path, True, "OK")
    except Exception as e:
        return (dst_path, False, str(e))
    
def remove_backgrounds(src_dir: Path, out_dir: Path, callback: Optional[Callable] = None, cancel_event=None) -> int:
    images = sorted([p for p in src_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")], key=numerical_sort_key)
    if not images: return 0
    check_cancel(cancel_event)

    total = len(images)
    _log(callback, f"Menghapus background dari {total} gambar...", 0.0)
    ok_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_REMBG) as executor:
        futures = {
            executor.submit(_process_single_rembg, p, out_dir / f"{p.stem}_rembg.png", cancel_event): p for p in images
        }
        try:
            for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
                check_cancel(cancel_event)
                src_image = futures[fut]
                _, ok, error_msg = fut.result()
                if ok: ok_count += 1
                else: _log(callback, f"Gagal hapus bg {src_image.name}: {error_msg}")

                if i % 5 == 0 or i == total:
                    _log(callback, f"Progres Rembg: {i}/{total}", i / total)
        except ProcessCancelled:
            # buang antrian yang belum jalan; `with` akan menunggu yang sedang jalan
            executor.shutdown(wait=False, cancel_futures=True)
            raise
    return ok_count

def _overlay_logo_one(prod_path: Path, logo_img: Image.Image, out_path: Path, logo_scale: float = 1.0, cancel_event=None) -> None:
    check_cancel(cancel_event)
    resample = get_resample_method()
    
    # 1. Foto produk sebagai background
    with Image.open(prod_path).convert("RGB") as bg:
        if bg.size != SIZE_STANDARD:
            bg = bg.resize(SIZE_STANDARD, resample=resample)

        # 2. Resize Logo
        target_w = int(SIZE_STANDARD[0] * logo_scale)
        target_h = int(SIZE_STANDARD[1] * logo_scale)
        
        with logo_img.copy() as logo_copy:
            logo_copy.thumbnail((target_w, target_h), resample=resample)

            # 3. Tempel logo di tengah
            x = (SIZE_STANDARD[0] - logo_copy.width) // 2
            y = (SIZE_STANDARD[1] - logo_copy.height) // 2
            
            bg.paste(logo_copy, (x, y), mask=logo_copy if logo_copy.mode == 'RGBA' else None)

            out_path.parent.mkdir(parents=True, exist_ok=True)
            bg.save(out_path, "JPEG", quality=95)

def process_mode_logo(src_dir: Path, out_parent: Path, logo_path: Path, base_name: str, callback: Optional[Callable] = None, cancel_event=None):
    check_cancel(cancel_event)
    _log(callback, f"Mode Logo: Menggunakan {logo_path.name} sebagai overlay...")
    
    # 1. Buka dan bersihkan logo
    with Image.open(logo_path) as logo_img:
        if logo_img.mode != 'RGBA':
            _log(callback, f"Cleaning logo background...")
            with open(logo_path, "rb") as f:
                logo_data = f.read()
            logo_cleaned = remove(logo_data)
            logo_final = Image.open(io.BytesIO(logo_cleaned)).convert("RGBA")
        else:
            logo_final = logo_img.convert("RGBA").copy()

    try:
        check_cancel(cancel_event)

        # 2. Ambil gambar asli
        images = sorted([p for p in src_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")], key=numerical_sort_key)
        out_dir = out_parent / f"02_logo_{logo_path.stem}"
        out_dir.mkdir(parents=True, exist_ok=True)

        total = len(images)
        _log(callback, f"Memproses {total} gambar dengan logo...")

        # 3. Proses paralel
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_COMPOSE) as executor:
            # Gunakan logo_scale=1.0 sesuai olah_gambar(1).py
            futures = [executor.submit(_overlay_logo_one, img, logo_final, out_dir / f"{img.stem}.jpg", 1.0, cancel_event) for img in images]
            try:
                for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
                    check_cancel(cancel_event)
                    try:
                        fut.result()
                        if i % 10 == 0 or i == total:
                            _log(callback, f"Progres Logo: {i}/{total}", i / total)
                    except ProcessCancelled:
                        raise
                    except Exception as e:
                        _log(callback, f"Gagal proses logo: {e}")
            except ProcessCancelled:
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        create_pdf_from_folder(out_dir, out_parent / f"{base_name} - {logo_path.stem}.pdf", callback=callback, cancel_event=cancel_event)
    finally:
        logo_final.close()

def _combine_background_one(fg_path: Path, template_path: Path, out_path: Path, fg_scale: float = 0.8, cancel_event=None) -> None:
    check_cancel(cancel_event)
    resample = get_resample_method()
    with Image.open(template_path).convert("RGB") as base:
        if base.size != SIZE_STANDARD:
            base = base.resize(SIZE_STANDARD, resample=resample)
            
        with Image.open(fg_path).convert("RGBA") as fg:
            target = (int(SIZE_STANDARD[0] * fg_scale), int(SIZE_STANDARD[1] * fg_scale))
            fg = ImageOps.contain(fg, target, method=resample)
            
            x = (SIZE_STANDARD[0] - fg.width) // 2
            y = (SIZE_STANDARD[1] - fg.height) // 2
            
            base.paste(fg, (x, y), mask=fg)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            base.save(out_path, "JPEG", quality=95)

def apply_templates(rembg_dir: Path, out_parent: Path, templates: List[Path], base_name: str, callback: Optional[Callable] = None, cancel_event=None):
    rembg_files = sorted(rembg_dir.glob('*_rembg.png'), key=numerical_sort_key)
    if not rembg_files: return

    for tmpl in templates:
        check_cancel(cancel_event)
        out_dir = out_parent / f"02_template_{tmpl.stem}"
        out_dir.mkdir(parents=True, exist_ok=True)
        _log(callback, f"Menerapkan template: {tmpl.name}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_COMPOSE) as executor:
            futures = [
                executor.submit(_combine_background_one, fg, tmpl, out_dir / f"{fg.stem.replace('_rembg', '')}.jpg", 0.8, cancel_event)
                for fg in rembg_files
            ]
            try:
                for fut in concurrent.futures.as_completed(futures):
                    check_cancel(cancel_event)
                    if fut.exception() is not None:
                        _log(callback, f"Gagal menerapkan template: {fut.exception()}")
            except ProcessCancelled:
                executor.shutdown(wait=False, cancel_futures=True)
                raise

        pdf_path = out_parent / f"{base_name} - {tmpl.stem}.pdf"
        create_pdf_from_folder(out_dir, pdf_path, callback=callback, cancel_event=cancel_event)
