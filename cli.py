import sys  
from pathlib import Path 

from config import BASE_IMAGE_DIR, TEMPLATE_DIR, OUTPUT_DIR 
from utils.helpers import ensure_directories 
from utils.ui import ask_int, select_directories_cli  
from core.processor import process_mode_logo, remove_backgrounds, apply_templates
from core.pdf import create_pdf_from_folder

def main():
    ensure_directories()
    
    
    sources = [d for d in BASE_IMAGE_DIR.iterdir() if d.is_dir()]
    if not sources:
        print("Folder kosong. Harap isi folder 'hasil-gambar' dengan subfolder berisi gambar.")
        return

    print("\nMode:\n  1. Olah Template/Logo\n  2. Langsung PDF")
    mode = ask_int("Pilihan: ", 1, 2)

    if mode == 1: 
        chosen_dirs = select_directories_cli(sources)
        
        templates = [t for t in TEMPLATE_DIR.glob("*") if t.suffix.lower() in (".png", ".jpg", ".jpeg")]
        
        if not templates:
            print("Template kosong. Harap isi folder 'template'.")
            return

        print("\nPilih template:")
        for i, t in enumerate(templates, 1): 
            print(f"  {i}. {t.name}")
        tm_idx = ask_int("Pilih nomor template (atau 0 untuk semua): ", 0, len(templates))
        
        selected_templates = templates if tm_idx == 0 else [templates[tm_idx-1]]

        for src in chosen_dirs:
            print(f"\n>>> Memproses Folder: {src.name}")
            output_name = f"olahan_{src.name}"
            target_dir = OUTPUT_DIR / output_name
            target_dir.mkdir(parents=True, exist_ok=True)

            for tmpl in selected_templates:
                
                if tmpl.name.upper().startswith("LOGO"):
                    process_mode_logo(src, target_dir, tmpl, output_name)
                else:
                    
                    rembg_dir = target_dir / "01_rembg" 
                    remove_backgrounds(src, rembg_dir)
                    apply_templates(rembg_dir, target_dir, [tmpl], output_name)


        print("\nSelesai.")
    else:
        
        for i, d in enumerate(sources, 1): 
            print(f"  {i}. {d.name}")
        src = sources[ask_int("Pilih folder untuk dijadikan PDF: ", 1, len(sources))-1]
        create_pdf_from_folder(src, OUTPUT_DIR / f"PDF_{src.name}.pdf") 

if __name__ == "__main__": 
    try: 
        main() 
    except KeyboardInterrupt:
        print("\nProses dihentikan oleh pengguna.")
