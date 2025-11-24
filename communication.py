import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from faker import Faker

from core.file_system import AndroidFileSystem
from core.db_manager import SQLiteDB

class TextHumanizer:
    def __init__(self):
        self.slang_map = {"you": "u", "are": "r", "thanks": "thx", "please": "pls", "because": "cuz", "perfect": "perf", "okay": "k"}
        self.typo_map = {
            'a': 's', 's': 'a', 'e': 'r', 'i': 'o', 'o': 'i', 'm': 'n', 'n': 'm'
        }
        self.emoji_map = {
            "happy": ["😊", "😄"], "sad": ["😢", "☹️"], "angry": ["😡", "😤"],
            "love": ["❤️", "😍"], "food": ["🍔", "🍕"], "beer": ["🍺", "🍻"],
            "money": ["💸", "💰"], "late": ["🕒", "🏃"], "ok": ["👍", "👌"]
        }

    def inject_typos(self, text: str, probability: float = 0.05) -> str:
        """Injects random adjacent-key typos."""
        chars = list(text)
        for i, char in enumerate(chars):
            if char.lower() in self.typo_map and random.random() < probability:
                chars[i] = self.typo_map[char.lower()]
        return "".join(chars)

    def inject_emojis(self, text: str, intensity: int) -> str:
        """Appends emojis based on keywords."""
        if intensity == 0: return text
        lower_text = text.lower()
        emojis_to_add = []
        for key, icons in self.emoji_map.items():
            if key in lower_text:
                emojis_to_add.append(random.choice(icons))
        
        if emojis_to_add:
            return text + " " + "".join(random.sample(emojis_to_add, min(len(emojis_to_add), intensity)))
        return text

    def humanize(self, text: str, intensity: int) -> str:
        if intensity == 0: return text
        
        # 1. Slang Injection
        words = text.split(" ")
        new_words = []
        for w in words:
            clean_w = w.strip(".,?!")
            if intensity >= 2 and clean_w.lower() in self.slang_map and random.random() < 0.6:
                new_words.append(self.slang_map[clean_w.lower()])
            else:
                new_words.append(w)
        result = " ".join(new_words)
        
        # 2. Lowercase conversion (laziness)
        if intensity >= 2 and random.random() < 0.7:
            result = result.lower()
        
        # 3. Punctuation removal
        if intensity > 0 and random.random() < 0.5:
            result = result.replace(".", "").replace(",", "")
            
        # 4. Typo Injection (New)
        if intensity >= 2:
            result = self.inject_typos(result)
            
        # 5. Emoji Injection (New)
        result = self.inject_emojis(result, intensity)
            
        return result

class CommunicationEngine:
    def __init__(self, fs: AndroidFileSystem, logger: logging.Logger):
        self.fs = fs
        self.logger = logger
        self.humanizer = TextHumanizer()
        self.fake = Faker()

    def generate_social_graph(self, owner_name: str, scenarios: dict, network_size: int, installed_apps: List[str]) -> Dict:
        self.logger.info("Building social graph...")
        graph = {}
        first_names = scenarios.get("first_names", [])
        last_names = scenarios.get("last_names", [])
        available_names = [f"{fn} {ln}" for fn in first_names for ln in last_names if f"{fn} {ln}" != owner_name]
        
        # Fill remainder with faker if needed
        while len(available_names) < network_size:
            available_names.append(self.fake.name())
            
        selected_contacts = random.sample(available_names, min(len(available_names), network_size))
        
        for name in selected_contacts:
            role = random.choice(["Colleague", "Friend", "Family"])
            valid_platforms = ["Messages (SMS)", "Phone"]
            if "WhatsApp" in installed_apps: valid_platforms.append("WhatsApp")
            
            topics = ["project_kickoff"] if role == "Colleague" else ["lunch_sushi", "weekend_plans"]
            
            graph[name] = {
                "Role": role, 
                "Platforms": valid_platforms, 
                "Topics": topics, 
                "PhoneNumber": self.fake.phone_number(), 
                "Email": self.fake.email()
            }
        return graph

    def create_sms_db(self, messages: List[Dict]):
        db_path = self.fs.get_path("sms") / "mmssms.db"
        with SQLiteDB(db_path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS sms (_id INTEGER PRIMARY KEY, address TEXT, date INTEGER, body TEXT, type INTEGER)")
            for msg in messages:
                if "SMS" not in msg['Platform']: continue
                dt = int(datetime.strptime(msg['Timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
                msg_type = 1 if msg['Direction'] == "Incoming" else 2
                addr = msg.get('SenderNum') if msg_type == 1 else msg.get('RecipientNum')
                if not addr: addr = msg['Sender'] if msg_type == 1 else msg['Recipient']
                c.execute("INSERT INTO sms (address, date, body, type) VALUES (?, ?, ?, ?)", (addr, dt, msg['Body'], msg_type))

    def create_whatsapp_db(self, messages: List[Dict]):
        db_path = self.fs.get_path("data") / "com.whatsapp" / "databases" / "msgstore.db"
        with SQLiteDB(db_path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS messages (_id INTEGER PRIMARY KEY, data TEXT, timestamp INTEGER, remote_resource TEXT)")
            for msg in messages:
                if "WhatsApp" not in msg['Platform']: continue
                ts = int(datetime.strptime(msg['Timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
                remote = msg.get('SenderNum') if msg['Direction'] == "Incoming" else msg.get('RecipientNum')
                if not remote: remote = msg['Sender']
                c.execute("INSERT INTO messages (data, timestamp, remote_resource) VALUES (?, ?, ?)", (msg['Body'], ts, remote))

    def generate_call_log(self, calls: List[Dict]):
        db_path = self.fs.get_path("calls") / "calllog.db"
        with SQLiteDB(db_path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS calls (_id INTEGER PRIMARY KEY, number TEXT, date INTEGER, duration INTEGER, type INTEGER)")
            for call in calls:
                ts = int(datetime.strptime(call['Timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
                ctype = 1
                if call['Direction'] == "Outgoing": ctype = 2
                if call['Status'] == "Missed": ctype = 3
                dur = int(call.get('Duration', 0))
                c.execute("INSERT INTO calls (number, date, duration, type) VALUES (?, ?, ?, ?)", (call['CallerNum'], ts, dur, ctype))

    def generate_emails(self, owner_email):
        path = self.fs.get_path("data") / "com.google.android.gm" / "files" / "messages"
        path.mkdir(parents=True, exist_ok=True)
        subjects = [("Welcome to Twitter", "Verify your account."), ("Your Amazon Order", "On the way."), ("Security Alert", "New login."), ("Invoice 2023-001", "Please pay.")]
        for i, (subj, body) in enumerate(subjects):
            content = f"From: service@notification.com\nTo: {owner_email}\nSubject: {subj}\n\n{body}"
            try:
                with open(path / f"msg_{i}.eml", "w") as f: f.write(content)
            except OSError as e:
                self.logger.warning(f"Failed to write email {i}: {e}")

    def generate_sim_info(self):
        db_path = self.fs.get_path("sms") / "telephony.db"
        with SQLiteDB(db_path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS siminfo (_id INTEGER PRIMARY KEY, icc_id TEXT, display_name TEXT, carrier_name TEXT, number TEXT)")
            iccid = f"89{self.fake.random_number(digits=18)}"
            phone_num = self.fake.phone_number()
            carrier = random.choice(["Verizon", "T-Mobile", "AT&T", "Vodafone"])
            c.execute("INSERT INTO siminfo (icc_id, display_name, carrier_name, number) VALUES (?, ?, ?, ?)",
                      (iccid, carrier, carrier, phone_num))

    def generate_cell_tower_db(self, geo_points: List[Dict]):
        db_path = self.fs.get_path("sms") / "telephony.db" 
        with SQLiteDB(db_path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS cell_towers (timestamp INTEGER, fake_cid INTEGER, fake_lac INTEGER, lat REAL, long REAL)")
            for pt in geo_points:
                if random.random() < 0.15:
                    ts = int(datetime.strptime(pt['timestamp'], "%Y-%m-%dT%H:%M:%SZ").timestamp() * 1000)
                    cid = random.randint(10000, 60000)
                    lac = random.randint(100, 900)
                    c.execute("INSERT INTO cell_towers VALUES (?, ?, ?, ?, ?)", 
                              (ts, cid, lac, pt['latitude'], pt['longitude']))