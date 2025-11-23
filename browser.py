import sqlite3
import random
import logging
from datetime import datetime
from typing import List, Dict
from faker import Faker

from core.file_system import AndroidFileSystem

class BrowserEngine:
    def __init__(self, fs: AndroidFileSystem, logger: logging.Logger):
        self.fs = fs
        self.logger = logger
        self.fake = Faker()

    def generate_chrome_history(self, history_items: List[Dict]):
        path = self.fs.get_path("data") / "com.android.chrome" / "app_chrome" / "Default"
        path.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(path / "History") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT, visit_count INTEGER, last_visit_time INTEGER)")
                c.execute("CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY, url INTEGER, visit_time INTEGER, transition INTEGER)")
                for item in history_items:
                    ts = int(datetime.strptime(item['Timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() * 1000000)
                    c.execute("INSERT INTO urls (url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?)", (item['URL'], item['Title'], 1, ts))
                    url_id = c.lastrowid
                    c.execute("INSERT INTO visits (url, visit_time, transition) VALUES (?, ?, ?)", (url_id, ts, 0)) 
                conn.commit()
        except sqlite3.Error: pass

    def generate_cookies(self, history_items: List[Dict]):
        """Generates the Cookies database."""
        path = self.fs.get_path("data") / "com.android.chrome" / "app_chrome" / "Default"
        path.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(path / "Cookies") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS cookies (creation_utc INTEGER, host_key TEXT, name TEXT, value TEXT, path TEXT, expires_utc INTEGER, is_secure INTEGER, is_httponly INTEGER, last_access_utc INTEGER, has_expires INTEGER, is_persistent INTEGER, priority INTEGER, encrypted_value BLOB, samesite INTEGER, source_scheme INTEGER)")
                
                for item in history_items:
                    # Simple domain extraction
                    host = "." + item['URL'].split("//")[-1].split("/")[0]
                    ts = int(datetime.now().timestamp() * 1000000)
                    c.execute("INSERT INTO cookies (creation_utc, host_key, name, value, path, is_secure) VALUES (?, ?, ?, ?, ?, ?)",
                              (ts, host, "session_id", self.fake.md5(), "/", 1))
                conn.commit()
        except sqlite3.Error: pass

    def generate_web_data(self, owner_name):
        """Generates the Web Data (Autofill) database."""
        path = self.fs.get_path("data") / "com.android.chrome" / "app_chrome" / "Default"
        path.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(path / "Web Data") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS autofill (name TEXT, value TEXT, value_lower TEXT, date_created INTEGER, date_last_used INTEGER, count INTEGER)")
                
                first, last = owner_name.split(" ")
                c.execute("INSERT INTO autofill (name, value, value_lower) VALUES (?, ?, ?)", ("name_first", first, first.lower()))
                c.execute("INSERT INTO autofill (name, value, value_lower) VALUES (?, ?, ?)", ("name_last", last, last.lower()))
                c.execute("INSERT INTO autofill (name, value, value_lower) VALUES (?, ?, ?)", ("email", f"{first}.{last}@gmail.com", f"{first}.{last}@gmail.com".lower()))
                conn.commit()
        except sqlite3.Error: pass