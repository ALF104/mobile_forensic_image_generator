import sqlite3
import json
import random
import logging
from datetime import datetime, timedelta
from faker import Faker
from core.file_system import AndroidFileSystem

class PersonalDataEngine:
    def __init__(self, fs: AndroidFileSystem, logger: logging.Logger):
        self.fs = fs
        self.logger = logger
        self.fake = Faker()

    def generate_calendar_db(self):
        """Generates a calendar database with realistic events."""
        path = self.fs.get_path("data") / "com.android.providers.calendar" / "databases"
        path.mkdir(parents=True, exist_ok=True)
        
        try:
            with sqlite3.connect(path / "calendar.db") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS Events (_id INTEGER PRIMARY KEY, title TEXT, dtstart INTEGER, dtend INTEGER, eventLocation TEXT, description TEXT)")
                
                # Generate 20 random events over the last month
                for _ in range(20):
                    start_dt = self.fake.date_time_between(start_date='-30d', end_date='now')
                    end_dt = start_dt + timedelta(hours=1)
                    
                    title = random.choice(["Meeting", "Dentist", "Lunch", "Gym", "Call Mom", "Project Sync"])
                    if random.random() < 0.2: title = "Meetup at drop point" # Scenario noise
                    
                    c.execute("INSERT INTO Events (title, dtstart, dtend, eventLocation, description) VALUES (?, ?, ?, ?, ?)",
                              (title, int(start_dt.timestamp()*1000), int(end_dt.timestamp()*1000), self.fake.address(), self.fake.sentence()))
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Calendar DB Error: {e}")

    def generate_notes_db(self):
        """Generates a Notes database (e.g. Google Keep style)."""
        path = self.fs.get_path("data") / "com.google.android.keep" / "databases"
        path.mkdir(parents=True, exist_ok=True)
        
        try:
            with sqlite3.connect(path / "keep.db") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS list_item (text TEXT, is_checked INTEGER, list_parent_id INTEGER)")
                c.execute("CREATE TABLE IF NOT EXISTS tree_entity (title TEXT, last_modified_time INTEGER)")
                
                notes = [
                    ("Groceries", "Milk, Eggs, Bread"),
                    ("Wifi", "Password123"),
                    ("To Do", "Call bank, Fix car"),
                    ("Codes", "8822, 9911")
                ]
                
                for title, body in notes:
                    ts = int(datetime.now().timestamp()*1000)
                    c.execute("INSERT INTO tree_entity (title, last_modified_time) VALUES (?, ?)", (title, ts))
                    c.execute("INSERT INTO list_item (text, is_checked, list_parent_id) VALUES (?, ?, ?)", (body, 0, 1))
                conn.commit()
        except sqlite3.Error: pass

    def generate_health_data(self):
        """Generates JSON health data (Steps/Heart Rate)."""
        path = self.fs.get_path("data") / "com.fitbit.FitbitMobile" / "files"
        path.mkdir(parents=True, exist_ok=True)
        
        data = {"activities": []}
        for i in range(7):
            day_stats = {
                "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "steps": random.randint(2000, 12000),
                "distance": random.uniform(1.5, 8.0),
                "calories": random.randint(1800, 2800)
            }
            data["activities"].append(day_stats)
            
        try:
            with open(path / "exercise_log.json", "w") as f:
                json.dump(data, f, indent=2)
        except OSError: pass

    def generate_keyboard_cache(self):
        """Generates User Dictionary (Predictive text learned words)."""
        path = self.fs.get_path("data") / "com.android.providers.userdictionary" / "databases"
        path.mkdir(parents=True, exist_ok=True)
        
        words = ["crypto", "btc", "meetup", "package", "drop", "signal", "proton"]
        
        try:
            with sqlite3.connect(path / "user_dict.db") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS words (_id INTEGER PRIMARY KEY, word TEXT, frequency INTEGER, locale TEXT)")
                for w in words:
                    c.execute("INSERT INTO words (word, frequency, locale) VALUES (?, ?, ?)", (w, 250, "en_US"))
                conn.commit()
        except sqlite3.Error: pass

    def generate_voice_memos(self):
        """Generates dummy audio files."""
        path = self.fs.get_path("sdcard") / "Recordings"
        path.mkdir(parents=True, exist_ok=True)
        
        # Fake M4A header
        header = b"\x00\x00\x00\x20\x66\x74\x79\x70\x4D\x34\x41\x20\x00\x00\x00\x00"
        
        for i in range(3):
            ts = datetime.now() - timedelta(days=random.randint(0, 10))
            fname = f"Recording_{ts.strftime('%Y%m%d_%H%M%S')}.m4a"
            try:
                with open(path / fname, "wb") as f:
                    f.write(header)
                    f.write(self.fake.binary(length=1024*50)) # 50KB of noise
            except OSError: pass