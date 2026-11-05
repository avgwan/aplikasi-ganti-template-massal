from typing import List 
from pathlib import Path

def ask_int(prompt: str, lo: int, hi: int) -> int:
    while True:
        try:
            v = int(input(prompt))
            if lo <= v <= hi:  # Cek apakah angka masuk dalam rentang lo sampai hi
                return v
        except Exception:
            pass
        print(f"Masukkan angka {lo}-{hi}.")

def parse_multi_selection(text: str, hi: int) -> List[int]:
    out = set()
    for tok in text.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            n = int(tok)
            if 1 <= n <= hi:
                out.add(n-1)
        except Exception:
            pass
    return sorted(out)

def select_directories_cli(dirs: List[Path]) -> List[Path]:
    print("\nPilih sumber folder:\n  1. Satu\n  2. Semua\n  3. Custom")
    choice = ask_int("Pilihan: ", 1, 3)
    if choice == 1:
        for i, d in enumerate(dirs, 1): print(f"  {i}. {d.name}")
        return [dirs[ask_int("Nomor: ", 1, len(dirs))-1]]
    if choice == 2:
        return dirs
   
    return [dirs[i] for i in parse_multi_selection(input("Nomor (koma): "), len(dirs))]

