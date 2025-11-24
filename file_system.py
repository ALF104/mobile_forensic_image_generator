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
        
        # Base Data Partition Root
        data_root = p / "data"
        
        paths = {
            "root": p,
            # Core Android Partitions (from screenshots)
            "adb": data_root / "adb",
            "anr": data_root / "anr", # App Not Responding logs
            "app": data_root / "app", # APKs
            "app_asec": data_root / "app-asec",
            "app_ephemeral": data_root / "app-ephemeral",
            "app_lib": data_root / "app-lib",
            "app_private": data_root / "app-private",
            "backup": data_root / "backup",
            "bootchart": data_root / "bootchart",
            "cache_root": data_root / "cache",
            "dalvik_cache": data_root / "dalvik-cache",
            "data": data_root / "data", # /data/data (App Data)
            "drm": data_root / "drm",
            "local": data_root / "local",
            "lost_found": data_root / "lost+found",
            "media_root": data_root / "media", # /data/media (Internal Storage)
            "mediadrm": data_root / "mediadrm",
            "misc": data_root / "misc",
            "misc_ce": data_root / "misc_ce",
            "misc_de": data_root / "misc_de",
            "nativetest": data_root / "nativetest",
            "nfc": data_root / "nfc",
            "ota": data_root / "ota",
            "ota_package": data_root / "ota_package",
            "property": data_root / "property",
            "resource_cache": data_root / "resource-cache",
            "ss": data_root / "ss",
            "system": data_root / "system",
            "system_ce": data_root / "system_ce",
            "system_de": data_root / "system_de",
            "tombstones": data_root / "tombstones", # Crash dumps
            "user": data_root / "user",
            "user_de": data_root / "user_de",
            "vendor": data_root / "vendor",
            "vendor_ce": data_root / "vendor_ce",
            "vendor_de": data_root / "vendor_de",
            
            # Sub-paths (System & Users)
            "system_users_base": data_root / "system" / "users",
            "system_users": data_root / "system" / "users" / "0",
            "dropbox": data_root / "system" / "dropbox",
            "user_10": data_root / "user" / "10", # Work Profile
            "user_11": data_root / "user" / "11", # Pixel Private Space
            "secure_folder": data_root / "user" / "150", # Samsung Secure Folder
            "clipboard": data_root / "clipboard",
            "wifi": data_root / "misc" / "wifi",
            
            # Sub-paths (Providers)
            "media_db": data_root / "data" / "com.android.providers.media" / "databases",
            "sms": data_root / "data" / "com.android.providers.telephony" / "databases",
            "calls": data_root / "data" / "com.android.providers.contacts" / "databases",
            
            # Sub-paths (Emulated SDCard / User Content)
            "sdcard": p / "sdcard",
            "dcim": p / "sdcard" / "DCIM" / "Camera",
            "thumbnails": p / "sdcard" / "DCIM" / ".thumbnails",
            "downloads": p / "sdcard" / "Download",
            "reports": p / "_Forensic_Reports"
        }
        return paths

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
        """Creates a .tar archive (Standard for physical extractions)."""
        with tarfile.open(self.base_path / f"{tar_name}.tar", "w") as tar:
            tar.add(self.root, arcname=self.root.name)