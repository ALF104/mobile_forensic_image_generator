import shutil
import json
import tarfile
from pathlib import Path
from typing import List, Dict

class AndroidFileSystem:
    def __init__(self, base_path: Path, root_dir_name: str = "Android_Extraction"):
        self.base_path = base_path
        self.root = self.base_path / root_dir_name
        self.paths = self._define_paths()

    def _define_paths(self) -> Dict[str, Path]:
        """Defines the internal Android folder structure."""
        p = self.root
        return {
            "root": p,
            "data": p / "data" / "data",
            "system": p / "data" / "system",
            "misc": p / "data" / "misc",
            "sdcard": p / "sdcard",
            # Sub-paths (System)
            "system_users_base": p / "data" / "system" / "users",
            "system_users": p / "data" / "system" / "users" / "0",
            "dropbox": p / "data" / "system" / "dropbox",
            "user_10": p / "data" / "user" / "10", # Work Profile
            "user_11": p / "data" / "user" / "11", # NEW: Pixel Private Space
            "secure_folder": p / "data" / "user" / "150", # Samsung Secure Folder
            "clipboard": p / "data" / "clipboard",
            "wifi": p / "data" / "misc" / "wifi",
            "media_db": p / "data" / "com.android.providers.media" / "databases",
            # Sub-paths (Providers)
            "sms": p / "data" / "data" / "com.android.providers.telephony" / "databases",
            "calls": p / "data" / "data" / "com.android.providers.contacts" / "databases",
            # Sub-paths (User Content)
            "dcim": p / "sdcard" / "DCIM" / "Camera",
            "thumbnails": p / "sdcard" / "DCIM" / ".thumbnails",
            "downloads": p / "sdcard" / "Download",
            "reports": p / "_Forensic_Reports"
        }

    def create_structure(self):
        """Creates the physical directories."""
        for key, path in self.paths.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                print(f"Error creating directory {path}: {e}")

    def get_path(self, key: str) -> Path:
        return self.paths.get(key, self.root)

    def write_json(self, path: Path, data: dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def zip_extraction(self, zip_name: str):
        """Creates a standard ZIP archive."""
        shutil.make_archive(str(self.base_path / zip_name), 'zip', self.root)

    def tar_extraction(self, tar_name: str):
        """Feature #10: Creates a .tar archive (Standard for physical extractions)."""
        with tarfile.open(self.base_path / f"{tar_name}.tar", "w") as tar:
            tar.add(self.root, arcname=self.root.name)