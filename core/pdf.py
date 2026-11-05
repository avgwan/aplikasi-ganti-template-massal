from pathlib import Path
from utils.helpers import numerical_sort_key
from core.cancel import check_cancel

def create_pdf_from_folder(image_folder: Path, output_filepath: Path, max_images_per_pdf: int=500, callback=None, cancel_event=None) -> None:
    images = sorted([p for p in image_folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")], key=numerical_sort_key)
    if not images: return
    total = len(images)

    for part, start in enumerate(range(0, total, max_images_per_pdf), 1):
        check_cancel(cancel_event)
        batch = images[start:start+max_images_per_pdf]
        p_suffix = f"_part{part}" if total > max_images_per_pdf else ""
        final_out = output_filepath.with_name(f"{output_filepath.stem}{p_suffix}.pdf")
        _save_pdf_batch(batch, final_out, callback=callback)

def _save_pdf_batch(image_paths, out_path, callback=None):
    if not image_paths: return False
    try:
        import img2pdf
        if callback: callback(f"Mengonversi {len(image_paths)} gambar ke PDF...")
        with open(out_path, "wb") as file:
            file.write(img2pdf.convert([str(p) for p in image_paths]))
        return True
    except (ImportError, ModuleNotFoundError):
        if callback: callback("img2pdf tidak ditemukan, menggunakan Pillow (lebih lambat)...")


        from PIL import Image

        pil_images = []
        for p in image_paths:
            try:
                pil_images.append(Image.open(p).convert("RGB"))
            except:
                pass
        if pil_images:
            pil_images[0].save(out_path, "PDF", save_all=True, append_images=pil_images[1:])
            for im in pil_images: im.close()
            return True
    except Exception as e:
        if callback: callback(f"Gagal membuat PDF: {e}")
    return False


