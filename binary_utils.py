from pathlib import Path
import os
import time
import random

def write_random_binary_file(path: Path, size_bytes: int):
    """Writes random bytes to a file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(os.urandom(size_bytes))
    except OSError:
        pass

def set_file_timestamp(path: Path, timestamp_obj):
    """Modifies the file's access and modified times."""
    try:
        mod_time = time.mktime(timestamp_obj.timetuple())
        os.utime(path, (mod_time, mod_time))
    except OSError:
        pass

def create_obfuscated_file(folder: Path, filename: str, signature_type: str):
    """
    Creates a file with the requested filename but writes specific 
    magic bytes (signature) to the header to mislead analysis.
    
    signature_type: 'jpg', 'png', 'zip', 'pdf'
    """
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        
        # Magic Bytes map
        headers = {
            "jpg": b"\xFF\xD8\xFF\xE0",
            "png": b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A",
            "zip": b"\x50\x4B\x03\x04",
            "pdf": b"\x25\x50\x44\x46\x2D"
        }
        
        header = headers.get(signature_type, os.urandom(4))
            
        with open(path, "wb") as f:
            f.write(header)
            # Write random data, but maybe some text strings to confuse grep
            f.write(b"CONFIDENTIAL")
            f.write(os.urandom(1024)) 
            
    except OSError:
        pass

def create_trash_artifact(sdcard_path: Path, filename: str):
    """
    Creates a file in a hidden .trash folder to simulate deletion.
    """
    trash_dir = sdcard_path / ".trash"
    trash_dir.mkdir(parents=True, exist_ok=True)
    
    ts = int(time.time())
    path = trash_dir / f"{ts}_{filename}"
    write_random_binary_file(path, 2048)