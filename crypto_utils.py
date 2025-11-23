import hashlib
from pathlib import Path

def calculate_md5(file_path: Path) -> str:
    """Calculates the MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""

def generate_color_from_string(text: str) -> tuple:
    """Generates a consistent RGB color based on a string hash."""
    h = hashlib.md5(text.encode()).hexdigest()
    return int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)