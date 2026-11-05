import re
from pathlib import Path
from typing import List

from config import OUTPUT_DIR

# Folder hasil dibuat UploadPage dengan format: olahan_<nama folder>_<YYYYMMDD_HHMMSS>
_TIMESTAMP = r"\d{8}_\d{6}"
INCOMPLETE_MARKER = ".dibatalkan"


def find_previous_runs(folder_name: str, output_dir: Path = None) -> List[Path]:
    """Cari hasil proses sebelumnya untuk folder dengan nama yang sama.

    Yang dihitung 'sudah pernah diproses' adalah folder hasil `olahan_<nama>_<timestamp>`
    di folder output yang tidak ditandai batal/gagal. Jadi kalau hasilnya dihapus
    pengguna, folder itu boleh diproses lagi.
    """
    output_dir = Path(output_dir or OUTPUT_DIR)
    if not output_dir.exists():
        return []

    pattern = re.compile(rf"^olahan_{re.escape(folder_name)}_{_TIMESTAMP}$", re.IGNORECASE)
    return sorted(
        p for p in output_dir.iterdir()
        if p.is_dir() and pattern.match(p.name) and not (p / INCOMPLETE_MARKER).exists()
    )


def mark_incomplete(result_dir: Path) -> None:
    """Tandai hasil proses yang batal/gagal supaya tidak dianggap 'sudah pernah diproses'."""
    try:
        (Path(result_dir) / INCOMPLETE_MARKER).write_text("proses tidak selesai", encoding="utf-8")
    except OSError:
        pass
