import os
import sqlite3
import hashlib
import logging
import random
from datetime import datetime
from typing import List, Tuple, Dict

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from core.file_system import AndroidFileSystem
from utils.binary_utils import set_file_timestamp

class MediaEngine:
    def __init__(self, fs: AndroidFileSystem, logger: logging.Logger):
        self.fs = fs
        self.logger = logger
        if not PIL_AVAILABLE:
            self.logger.warning("Pillow (PIL) not found. Image generation will be skipped.")

    def _to_deg(self, value, loc):
        """Helper to convert decimal coordinates to EXIF rational format."""
        if value < 0: loc_value = loc[1]
        else: loc_value = loc[0]
        abs_value = abs(value)
        deg = int(abs_value)
        t1 = (abs_value - deg) * 60
        min = int(t1)
        sec = round((t1 - min) * 60 * 10000)
        return (deg, 1), (min, 1), (sec, 10000), loc_value

    def generate_image_file(self, filename: str, timestamp: datetime, location: Tuple[float, float] = None):
        if not PIL_AVAILABLE: return
        main_path = self.fs.get_path("dcim") / filename
        thumb_path = self.fs.get_path("thumbnails") / filename
        try:
            h = hashlib.md5(filename.encode()).hexdigest()
            color = (int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            img = Image.new('RGB', (400, 300), color=color)
            draw = ImageDraw.Draw(img)
            draw.rectangle([(20, 20), (380, 280)], fill=(255, 255, 255))
            
            # Visual Text
            text = f"IMG: {filename}"
            if location: text += f"\nLat: {location[0]:.4f}\nLon: {location[1]:.4f}"
            try:
                font = ImageFont.load_default()
                draw.text((200, 150), text, fill=color, anchor="mm", font=font)
            except Exception: pass
            
            # Save initial image
            img.save(main_path, "JPEG")
            
            # Feature #1: Real EXIF Injection
            if PIEXIF_AVAILABLE and location:
                exif_dict = {"GPS": {}}
                lat_deg = self._to_deg(location[0], ["N", "S"])
                lon_deg = self._to_deg(location[1], ["E", "W"])
                
                exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = [lat_deg[0], lat_deg[1], lat_deg[2]]
                exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_deg[3]
                exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = [lon_deg[0], lon_deg[1], lon_deg[2]]
                exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_deg[3]
                
                exif_bytes = piexif.dump(exif_dict)
                img.save(main_path, "JPEG", exif=exif_bytes)

            set_file_timestamp(main_path, timestamp)
            img.resize((320, 240)).save(thumb_path, "JPEG")
            set_file_timestamp(thumb_path, timestamp)
        except Exception as e: self.logger.error(f"Error generating image {filename}: {e}")

    def build_media_store_db(self):
        dcim = self.fs.get_path("dcim")
        db_path = self.fs.get_path("media_db")
        db_path.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(db_path / "external.db") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS files (_id INTEGER PRIMARY KEY, _data TEXT, date_added INTEGER, media_type INTEGER, mime_type TEXT)")
                if dcim.exists():
                    for f in dcim.iterdir():
                        if f.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                            ts = int(f.stat().st_mtime)
                            c.execute("INSERT INTO files (_data, date_added, media_type, mime_type) VALUES (?, ?, ?, ?)", (str(f), ts, 1, "image/jpeg"))
                conn.commit()
        except sqlite3.Error: pass

    def generate_financial_receipts(self, installed_apps: Dict[str, str]):
        path = self.fs.get_path("downloads")
        path.mkdir(parents=True, exist_ok=True)
        finance_apps = ["PayPal", "Cash App", "Venmo", "Coinbase", "Amazon"]
        for app_name in installed_apps.keys():
            for fin in finance_apps:
                if fin.lower() in app_name.lower():
                    filename = f"{fin}_Receipt_{random.randint(10000,99999)}.pdf"
                    try:
                        with open(path / filename, "wb") as f:
                            f.write(b"%PDF-1.5\n")
                            f.write(f"Transaction confirmed for {fin}\nAmount: ${random.uniform(50, 500):.2f}".encode())
                            f.write(b"\n%%EOF")
                    except OSError: pass

    def generate_download_manager_db(self):
        dl_path = self.fs.get_path("downloads")
        db_path = self.fs.get_path("data") / "com.android.providers.downloads" / "databases"
        db_path.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(db_path / "downloads.db") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS downloads (_id INTEGER PRIMARY KEY, uri TEXT, _data TEXT, mimetype TEXT, title TEXT, description TEXT)")
                if dl_path.exists():
                    for f in dl_path.iterdir():
                        if f.is_file():
                            uri = f"https://mail.google.com/mail/u/0?ui=2&ik=c12345&view=att&th=123&attid=0.1&disp=safe&zw&name={f.name}"
                            c.execute("INSERT INTO downloads (uri, _data, title, mimetype) VALUES (?, ?, ?, ?)",
                                      (uri, str(f), f.name, "application/octet-stream"))
                conn.commit()
        except sqlite3.Error: pass

    def generate_thumbnail_cache(self):
        path = self.fs.get_path("thumbnails")
        path.mkdir(parents=True, exist_ok=True)
        for i in [3, 4]:
            filename = f".thumbdata3--{random.randint(1000000000, 9999999999)}"
            try:
                with open(path / filename, "wb") as f:
                    f.write(b"\x01\x00\x00\x00")
                    f.write(os.urandom(1024 * 1024))
            except OSError: pass

    def generate_office_docs(self):
        doc_path = self.fs.get_path("sdcard") / "Documents"
        doc_path.mkdir(parents=True, exist_ok=True)
        if OPENPYXL_AVAILABLE:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Financials"
            ws['A1'] = "Account"; ws['B1'] = "Balance"
            ws['A2'] = "Offshore"; ws['B2'] = 50000
            try: wb.save(doc_path / "Q3_Financials.xlsx")
            except: pass
        try:
            with open(doc_path / "Meeting_Notes.docx", "wb") as f:
                f.write(b"PK\x03\x04") 
                f.write(b"fake_word_content_xml_structure_here")
        except OSError: pass