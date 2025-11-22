import sys
import os
import random
import hashlib
import json
import math
import sqlite3
import struct
import time
import shutil
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta

# --- PySide6 Imports ---
try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                   QHBoxLayout, QLabel, QSpinBox, QComboBox, 
                                   QPushButton, QTextEdit, QProgressBar, QMessageBox, QGroupBox, 
                                   QLineEdit, QCheckBox, QTabWidget, QDialog, QDateTimeEdit, 
                                   QFormLayout, QListWidget, QListWidgetItem, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView)
    from PySide6.QtCore import Qt, QThread, Signal, QObject, QDate, QTime
    from PySide6.QtGui import QFont, QAction
except ImportError:
    print("Error: PySide6 is missing. Please run: pip install PySide6")
    sys.exit(1)

# --- Data Processing Imports ---
try: import pandas as pd
except ImportError: pass
try: from PIL import Image, ImageDraw, ImageFont
except ImportError: pass
try: from reportlab.pdfgen import canvas
except ImportError: pass
try: from docx import Document
except ImportError: pass
try: from pptx import Presentation
except ImportError: pass
try: import openpyxl
except ImportError: pass

# --- Configuration Defaults ---
DEFAULT_FIRST_NAME = "Aiden"
DEFAULT_SURNAME = "Smith"

NATIVE_APPS = ["Phone", "Messages (SMS)", "Chrome", "Contacts", "Camera", "Gallery", "Calendar", "Calculator", "Settings", "Pixel Launcher", "Google", "Maps", "Digital Wellbeing"]
OPTIONAL_APPS = [
    "WhatsApp", "Telegram", "Signal", "Instagram", "Facebook Messenger", 
    "Snapchat", "Discord", "Slack", "Microsoft Teams", "Zoom", 
    "Google Meet", "Firefox", "Spotify", "Netflix", "Uber", "Twitter", "TikTok"
]

# --- ANDROID FILE SYSTEM PATHS ---
ROOT_DIR = "Android_Extraction"
PATH_DATA = os.path.join(ROOT_DIR, "data", "data")
PATH_SYSTEM = os.path.join(ROOT_DIR, "data", "system")
PATH_SYSTEM_USERS = os.path.join(PATH_SYSTEM, "users", "0") 
PATH_ACCOUNTS = PATH_SYSTEM_USERS 
PATH_MISC = os.path.join(ROOT_DIR, "data", "misc")
PATH_MISC_WIFI = os.path.join(PATH_MISC, "wifi")
PATH_MISC_BT = os.path.join(PATH_MISC, "bluedroid")
PATH_RADIO = os.path.join(PATH_MISC, "radio") 
PATH_CLIPBOARD = os.path.join(ROOT_DIR, "data", "clipboard")

# DB Paths (Providers)
PATH_SMS = os.path.join(PATH_DATA, "com.android.providers.telephony", "databases")
PATH_CALLS = os.path.join(PATH_DATA, "com.android.providers.contacts", "databases")
PATH_CONTACTS = os.path.join(PATH_DATA, "com.android.providers.contacts", "databases")
PATH_CALENDAR = os.path.join(PATH_DATA, "com.android.providers.calendar", "databases")
PATH_DOWNLOADS_DB = os.path.join(PATH_DATA, "com.android.providers.downloads", "databases")
PATH_MEDIA_DB = os.path.join(PATH_DATA, "com.android.providers.media", "databases")

# DB Paths (Google/System)
PATH_CHROME_DB = os.path.join(PATH_DATA, "com.android.chrome", "app_chrome", "Default")
PATH_USER_DICT = os.path.join(PATH_DATA, "com.android.inputmethod.latin", "databases")
PATH_WELLBEING = os.path.join(PATH_DATA, "com.google.android.apps.wellbeing", "databases")
PATH_GSEARCH = os.path.join(PATH_DATA, "com.google.android.googlequicksearchbox", "databases")
PATH_MAPS_CACHE = os.path.join(PATH_DATA, "com.google.android.apps.maps", "cache")

# System Paths
PATH_USAGE = os.path.join(PATH_SYSTEM, "usagestats")
PATH_BATTERY = os.path.join(PATH_SYSTEM, "batterystats")
PATH_RECENT = os.path.join(PATH_SYSTEM, "recent_images")
PATH_NOTIF = os.path.join(PATH_SYSTEM, "notification_log.db")

# App Specific Paths (DBs & Prefs)
PATH_WHATSAPP = os.path.join(PATH_DATA, "com.whatsapp")
PATH_WHATSAPP_DB = os.path.join(PATH_WHATSAPP, "databases")
PATH_WHATSAPP_PREF = os.path.join(PATH_WHATSAPP, "shared_prefs")
PATH_CHROME_PREF = os.path.join(PATH_DATA, "com.android.chrome", "shared_prefs")
PATH_SIGNAL = os.path.join(PATH_DATA, "org.thoughtcrime.securesms", "databases")
PATH_TELEGRAM = os.path.join(PATH_DATA, "org.telegram.messenger", "files")
PATH_INSTAGRAM = os.path.join(PATH_DATA, "com.instagram.android", "databases")

# SD Card Paths
PATH_DCIM = os.path.join(ROOT_DIR, "sdcard", "DCIM", "Camera")
PATH_TRASH = os.path.join(ROOT_DIR, "sdcard", "DCIM", ".trash")
PATH_THUMBNAILS = os.path.join(ROOT_DIR, "sdcard", "DCIM", ".thumbnails")
PATH_DOWNLOAD = os.path.join(ROOT_DIR, "sdcard", "Download")
PATH_MUSIC = os.path.join(ROOT_DIR, "sdcard", "Music", "Recordings")
PATH_DOCS = os.path.join(ROOT_DIR, "sdcard", "Documents")
LOCATION_FOLDER = os.path.join(ROOT_DIR, "sdcard", "Location")
PATH_REPORTS = os.path.join(ROOT_DIR, "_Forensic_Reports")
PATH_CARVED = os.path.join(ROOT_DIR, "_Carved_Deleted_Data")

# --- Names & Logic ---
FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Donald", "Mark", "Paul", "Steven", "Andrew", "Kenneth", "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Margaret", "Betty", "Sandra", "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol", "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Laura", "Sharon", "Cynthia"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts"]

RELATIONSHIP_PREFS = {
    "Colleague": ["Microsoft Teams", "Slack", "Zoom", "Google Meet", "Email", "Phone", "Messages (SMS)"],
    "Family": ["WhatsApp", "Signal", "Phone", "Messages (SMS)", "Google Meet"],
    "Friend": ["Instagram", "Snapchat", "WhatsApp", "Signal", "Discord", "Facebook Messenger", "Phone", "Messages (SMS)"],
    "Service": ["Messages (SMS)", "Email"]
}

TOPIC_CONTENT = {
    "project_kickoff": [("Owner", "Here is the initial scope."), ("Owner", "project_scope_v1.docx"), ("Partner", "Thanks, reviewing tonight."), ("Partner", "kickoff_slides.pptx"), ("Owner", "Perfect.")],
    "budget_review": [("Partner", "Did you see the budget variances?"), ("Partner", "Q3_budget_analysis.xlsx"), ("Owner", "Travel expenses are high."), ("Partner", "Vegas conference cost a lot.")],
    "lunch_sushi": [("Owner", "Sushi?"), ("Partner", "Always."), ("Owner", "Lobby 12:30."), ("Partner", "K.")],
    "weekend_plans": [("Partner", "Weekend plans?"), ("Owner", "Movies."), ("Partner", "Nice.")],
}
if "project_kickoff" not in TOPIC_CONTENT: TOPIC_CONTENT = {"default": [("Owner", "Hello"), ("Partner", "Hi")]}

BROWSER_TOPIC_MAP = {"hiking": [("AllTrails", "https://alltrails.com")], "news": [("CNN", "https://cnn.com")]}
COMMON_URLS = [("Google", "https://google.com"), ("Gmail", "https://mail.google.com")]

# --- Helper Functions ---
def create_android_structure():
    paths = [PATH_SMS, PATH_CALLS, PATH_CONTACTS, PATH_CHROME_DB, PATH_CALENDAR, PATH_USAGE, PATH_SYSTEM, PATH_BATTERY, 
             PATH_MISC, PATH_ACCOUNTS, PATH_WHATSAPP_DB, PATH_WHATSAPP_PREF, PATH_CHROME_PREF, PATH_SIGNAL, PATH_TELEGRAM, PATH_INSTAGRAM,
             PATH_DCIM, PATH_THUMBNAILS, PATH_DOWNLOAD, PATH_MUSIC, PATH_DOCS, LOCATION_FOLDER, PATH_REPORTS, PATH_CARVED,
             PATH_MISC_WIFI, PATH_MISC_BT, PATH_DOWNLOADS_DB, PATH_USER_DICT, PATH_RECENT, PATH_CLIPBOARD]
    for p in paths:
        if not os.path.exists(p):
            try: os.makedirs(p)
            except OSError: pass

def set_file_time(filepath, dt_object):
    try:
        mod_time = time.mktime(dt_object.timetuple())
        os.utime(filepath, (mod_time, mod_time))
    except: pass

def prettify_xml(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

# --- Text Humanizer ---
class TextHumanizer:
    def __init__(self):
        self.slang_map = { "you": "u", "are": "r", "thanks": "thx", "please": "pls", "because": "cuz", "perfect": "perf", "okay": "k" }
    def humanize(self, text, intensity):
        if intensity == 0: return text
        words = text.split(" "); new_words = []
        for w in words:
            clean_w = w.strip(".,?!")
            if intensity == 2 and clean_w.lower() in self.slang_map and random.random() < 0.6: new_words.append(self.slang_map[clean_w.lower()])
            else: new_words.append(w)
        result = " ".join(new_words)
        if intensity == 2: result = result.lower()
        if intensity > 0 and random.random() < 0.5: result = result.replace(".", "").replace(",", "")
        return result

# --- File Gen Helpers ---
def generate_jpg(filename, timestamp, is_deleted=False):
    main_path = os.path.join(PATH_DCIM, filename)
    thumb_path = os.path.join(PATH_THUMBNAILS, filename)
    if os.path.exists(main_path) or os.path.exists(thumb_path): return 
    try:
        h = hashlib.md5(filename.encode()).hexdigest(); color = (int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)); img = Image.new('RGB', (400, 300), color=color); draw = ImageDraw.Draw(img); draw.rectangle([(20, 20), (380, 280)], fill=(255, 255, 255))
        font = ImageFont.load_default(); draw.text((200, 150), f"IMG: {filename}", fill=color, anchor="mm", font=font)
        exif = img.getexif(); exif[271] = "Google"; exif[272] = "Pixel 8"; exif[306] = timestamp.strftime("%Y:%m:%d %H:%M:%S")
        if not is_deleted: img.save(main_path, "JPEG", exif=exif); set_file_time(main_path, timestamp)
        thumb = img.resize((320, 240)); thumb.save(thumb_path, "JPEG"); set_file_time(thumb_path, timestamp)
    except: pass

def generate_doc(filename, timestamp):
    full_path = os.path.join(PATH_DOWNLOAD, filename)
    if os.path.exists(full_path): return
    try:
        if filename.endswith(".pdf"): c = canvas.Canvas(full_path); c.drawString(100, 750, f"Dummy PDF: {filename}"); c.save()
        elif filename.endswith(".docx"): doc = Document(); doc.add_heading(f'File: {filename}', 0); doc.save(full_path)
        elif filename.endswith(".xlsx"): wb = openpyxl.Workbook(); ws = wb.active; ws['A1'] = "Data"; wb.save(full_path)
        set_file_time(full_path, timestamp)
    except: pass

# --- ENGINES ---
class DeviceInfoEngine:
    def generate_device_info(self, owner_name):
        info = { "Device Owner": owner_name, "Manufacturer": "Google", "Model": "Pixel 8", "Extraction Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S") }
        try:
            with open(os.path.join(ROOT_DIR, "device_info.json"), 'w') as f: json.dump(info, f, indent=4)
            with open(os.path.join(PATH_SYSTEM, "build.prop"), 'w') as f: f.write(f"ro.product.owner={owner_name}\n")
        except Exception: pass
        return info

class HashEngine:
    def generate_manifest(self):
        manifest = []
        for root, dirs, files in os.walk(ROOT_DIR):
            for file in files:
                if file == "hash_manifest.csv": continue
                path = os.path.join(root, file)
                try:
                    with open(path, 'rb') as f: d = f.read(); manifest.append({"File": os.path.relpath(path, ROOT_DIR), "MD5": hashlib.md5(d).hexdigest()})
                except: pass
        try: pd.DataFrame(manifest).to_csv(os.path.join(ROOT_DIR, "hash_manifest.csv"), index=False)
        except: pass

class SystemArtifactsEngine:
    def generate_wifi_config(self):
        try:
            with open(os.path.join(PATH_MISC_WIFI, "WifiConfigStore.xml"), 'w') as f: f.write("<WifiConfigStoreData><NetworkList><Network><SSID>Home_Network</SSID></Network></NetworkList></WifiConfigStoreData>")
        except: pass
    def generate_accounts_db(self, owner):
        try:
            conn = sqlite3.connect(os.path.join(PATH_ACCOUNTS, "accounts.db")); c = conn.cursor()
            c.execute("CREATE TABLE accounts (_id INTEGER PRIMARY KEY, name TEXT, type TEXT)")
            c.execute("INSERT INTO accounts (name, type) VALUES (?, ?)", (f"{owner}@gmail.com", "com.google"))
            conn.commit(); conn.close()
        except: pass

class PersonaEngine:
    def generate_social_graph(self, owner_name, network_size, installed_apps):
        graph = {}; available = [f"{fn} {ln}" for fn in FIRST_NAMES for ln in LAST_NAMES if f"{fn} {ln}" != owner_name]
        selected = random.sample(available, min(len(available), network_size))
        for name in selected:
            role = random.choice(["Colleague", "Friend", "Family"])
            valid_plats = [p for p in RELATIONSHIP_PREFS[role] if p in installed_apps] or ["Messages (SMS)"]
            topics = ["project_kickoff"] if role == "Colleague" else ["lunch_sushi"]
            graph[name] = { "Role": role, "Platforms": valid_plats, "Topics": topics, "Schedule": "work_hours" if role == "Colleague" else "anytime" }
        return graph

class AppListEngine:
    def generate_app_list(self, installed_apps):
        return [{"App": app, "Type": "System" if app in NATIVE_APPS else "User"} for app in installed_apps]

class SharedPrefsEngine:
    def generate_prefs(self, owner, installed_apps):
        if "WhatsApp" in installed_apps:
            root = ET.Element("map")
            ET.SubElement(root, "string", name="push_name").text = owner
            try:
                with open(os.path.join(PATH_WHATSAPP_PREF, "com.whatsapp_preferences.xml"), "w") as f: f.write(prettify_xml(root))
            except: pass
        if "Chrome" in installed_apps:
            root = ET.Element("map")
            ET.SubElement(root, "string", name="last_url").text = "https://google.com"
            try:
                with open(os.path.join(PATH_CHROME_PREF, "com.android.chrome_preferences.xml"), "w") as f: f.write(prettify_xml(root))
            except: pass

class PackageManagerEngine:
    def generate_packages_xml(self, installed_apps, start_date):
        root = ET.Element("packages")
        for app in installed_apps:
            ET.SubElement(root, "package", name=app, it=str(int(start_date.timestamp()*1000)))
        try:
            with open(os.path.join(PATH_SYSTEM, "packages.xml"), "w") as f: f.write(prettify_xml(root))
        except: pass

class ClipboardEngine:
    def generate_clipboard(self, all_chats):
        clips = []
        for chat in all_chats:
            msg = chat['Body']
            if len(msg) > 5 and random.random() < 0.05: clips.append({"text": msg, "ts": chat['Timestamp']})
        for i, clip in enumerate(clips):
            fname = f"clip_{i+1}.txt"
            try:
                with open(os.path.join(PATH_CLIPBOARD, fname), "w") as f: f.write(clip['text'])
                dt = datetime.strptime(clip['ts'], "%Y-%m-%d %H:%M:%S")
                set_file_time(os.path.join(PATH_CLIPBOARD, fname), dt)
            except: pass

class TelephonyEngine:
    def generate_telephony_db(self, location_track):
        try:
            db_path = os.path.join(PATH_SMS, "telephony.db")
            conn = sqlite3.connect(db_path); c = conn.cursor()
            c.execute("CREATE TABLE carriers (_id INTEGER PRIMARY KEY, name TEXT)")
            c.execute("INSERT INTO carriers (name) VALUES ('Verizon')")
            c.execute("CREATE TABLE cell_towers (_id INTEGER PRIMARY KEY, date INTEGER, lat REAL, long REAL)")
            for point in location_track:
                ts = int(datetime.strptime(point['timestamp'], "%Y-%m-%dT%H:%M:%SZ").timestamp() * 1000)
                c.execute("INSERT INTO cell_towers (date, lat, long) VALUES (?, ?, ?)", (ts, point['latitude'], point['longitude']))
            conn.commit(); conn.close()
        except: pass

class RecentTasksEngine:
    def generate_snapshots(self, installed_apps):
        for app in random.sample(installed_apps, min(5, len(installed_apps))):
            filename = f"task_{random.randint(1000,9999)}.jpg"
            path = os.path.join(PATH_RECENT, filename)
            try:
                img = Image.new('RGB', (1080, 1920), color=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))
                img.save(path, "JPEG")
            except: pass

class UserDictionaryEngine:
    def generate_dictionary(self, participants, humanizer):
        try:
            db_path = os.path.join(PATH_USER_DICT, "user_dict.db")
            conn = sqlite3.connect(db_path); c = conn.cursor()
            c.execute("CREATE TABLE words (_id INTEGER PRIMARY KEY, word TEXT, frequency INTEGER, locale TEXT)")
            for p in participants:
                for part in p.split(" "): c.execute("INSERT INTO words (word, frequency, locale) VALUES (?, ?, ?)", (part, 200, "en_US"))
            conn.commit(); conn.close()
        except: pass

class DownloadManagerEngine:
    def generate_download_db(self):
        try:
            db_path = os.path.join(PATH_DOWNLOADS_DB, "downloads.mmssms.db")
            conn = sqlite3.connect(db_path); c = conn.cursor()
            c.execute("CREATE TABLE downloads (_id INTEGER PRIMARY KEY, uri TEXT, _data TEXT)")
            files = os.listdir(PATH_DOWNLOAD)
            for f in files:
                path = os.path.join(PATH_DOWNLOAD, f)
                uri = "https://google.com/download/" + f
                c.execute("INSERT INTO downloads (uri, _data) VALUES (?, ?)", (uri, path))
            conn.commit(); conn.close()
        except: pass

class BluetoothConfigEngine:
    def generate_bt_config(self):
        try:
            with open(os.path.join(PATH_MISC_BT, "bt_config.conf"), 'w') as f: f.write("[Adapter]\nName=Pixel 8\n")
        except: pass

class NotificationHistoryEngine:
    def generate_notification_db(self, all_chats, start_date, end_date):
        try:
            conn = sqlite3.connect(PATH_NOTIF); c = conn.cursor()
            c.execute("CREATE TABLE log (_id INTEGER PRIMARY KEY, pkg TEXT, title TEXT, text TEXT, post_time INTEGER)")
            sample = random.sample(all_chats, min(len(all_chats), 50))
            for chat in sample:
                ts = int(datetime.strptime(chat['Timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
                pkg = "com.whatsapp" if "WhatsApp" in chat['Platform'] else "com.google.android.apps.messaging"
                c.execute("INSERT INTO log (pkg, title, text, post_time) VALUES (?, ?, ?, ?)", (pkg, chat['Sender'], chat['Body'][:50], ts))
            conn.commit(); conn.close()
        except: pass

class CallLogEngine:
    def generate_calls(self, owner, participants, count, start_date, end_date, platforms):
        data = []; current = start_date; avg_gap_sec = (end_date - start_date).total_seconds() / max(count, 1); partners = [p for p in participants if p != owner] or ["Unknown"]; plat_list = [p.strip() for p in platforms.split(',') if p.strip()] or ["Cellular"]
        for _ in range(count):
            partner = random.choice(partners); platform = random.choice(plat_list)
            if random.random() < 0.5: caller = owner; receiver = partner; direction = "Outgoing"
            else: caller = partner; receiver = owner; direction = "Incoming"
            status = random.choice(["Connected", "Missed"]); dur = str(timedelta(seconds=random.randint(10, 600))) if status == "Connected" else "0"
            current += timedelta(seconds=random.randint(int(avg_gap_sec * 0.5), int(avg_gap_sec * 1.5)))
            if current > end_date: break
            data.append({"Platform": platform, "Caller": caller, "Receiver": receiver, "Direction": direction, "Status": status, "Duration": dur, "Timestamp": current.strftime("%Y-%m-%d %H:%M:%S")})
        return data

class LocationEngine:
    def __init__(self): self.base_work = (40.7488, -73.9854); self.base_home = (40.6781, -73.9441); self.base_park = (40.7850, -73.9682)
    def jitter(self, lat, lon, amount=0.0005): return lat + random.uniform(-amount, amount), lon + random.uniform(-amount, amount)
    def get_location_for_time(self, dt):
        hour = dt.hour; is_weekend = dt.weekday() >= 5
        if is_weekend: return self.jitter(self.base_park[0], self.base_park[1], 0.005) if 11 <= hour <= 15 else self.jitter(self.base_home[0], self.base_home[1], 0.002)
        else: return self.jitter(self.base_home[0], self.base_home[1], 0.0002) if 0 <= hour < 8 or hour > 19 else self.jitter(self.base_work[0], self.base_work[1], 0.0005)
    def generate_track(self, start_time, end_time):
        points = []; current = start_time
        while current <= end_time:
            lat, lon = self.get_location_for_time(current)
            points.append({"timestamp": current.strftime("%Y-%m-%dT%H:%M:%SZ"), "latitude": lat, "longitude": lon})
            current += timedelta(minutes=30)
        return points
    def generate_track_by_count(self, start_time, count, end_time_cap=None):
        points = []; current = start_time; interval_mins = 15
        if end_time_cap and count > 0: interval_mins = max(1, (end_time_cap - start_time).total_seconds() / 60 / count)
        for _ in range(count):
            if end_time_cap and current > end_time_cap: break
            lat, lon = self.get_location_for_time(current)
            points.append({"timestamp": current.strftime("%Y-%m-%dT%H:%M:%SZ"), "latitude": lat, "longitude": lon})
            current += timedelta(minutes=interval_mins)
        return points
    def save_kml(self, points, filename):
        with open(os.path.join(LOCATION_FOLDER, filename), 'w') as f: f.write("KML") # Simplified
    def save_json(self, points, filename):
        with open(os.path.join(LOCATION_FOLDER, filename), 'w') as f: json.dump(points, f, indent=2)

class BrowserEngine:
    def generate_history(self, owner, start_date, end_date):
        history = []; current = start_date
        while current < end_date:
            if current.hour == 8:
                for site in COMMON_URLS: history.append({"URL": site[1], "Title": site[0], "Timestamp": current.strftime("%Y-%m-%d %H:%M:%S")})
            current += timedelta(hours=1)
        return history

class ContactsEngine:
    def generate_contacts(self, participants, random_count=20):
        contacts = []
        for p in participants: contacts.append({"Name": p, "Number": "555-0199", "Email": "test@test.com", "Type": "Friend"})
        return contacts

class CalendarEngine:
    def generate_calendar(self, owner, start_date, end_date): return [{"Summary": "Meeting", "Start": start_date, "End": end_date, "Location": "Office"}]
    def save_ics(self, events, filename): pass

class EmailEngine:
    def generate_emails(self, owner, participants, count, start_date, end_date): return [{"From": "test", "Subject": "test", "Date": "now", "Body": "test"}]
    def save_eml(self, email_data, folder): pass

class ConnectivityEngine:
    def generate_wifi(self, start_date, end_date): return [{"SSID": "Home", "Timestamp": "now"}]
    def generate_bluetooth(self, start_date, end_date): return [{"Device": "Car", "Timestamp": "now"}]

class DatabaseEngine:
    def create_sms_db(self, chats):
        db_path = os.path.join(PATH_SMS, "mmssms.db"); conn = sqlite3.connect(db_path); c = conn.cursor()
        c.execute("CREATE TABLE sms (_id INTEGER PRIMARY KEY, address TEXT, date INTEGER, body TEXT, type INTEGER)")
        for ch in chats:
            dt = int(datetime.strptime(ch['Timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
            c.execute("INSERT INTO sms (address, date, body, type) VALUES (?, ?, ?, ?)", (ch['Sender'], dt, ch['Body'], 1))
        conn.commit(); conn.close()
    def create_call_db(self, calls):
        db_path = os.path.join(PATH_CALLS, "calllog.db"); conn = sqlite3.connect(db_path); c = conn.cursor()
        c.execute("CREATE TABLE calls (_id INTEGER PRIMARY KEY, number TEXT, date INTEGER, duration INTEGER, type INTEGER)")
        for ca in calls: c.execute("INSERT INTO calls (number, date, duration, type) VALUES (?, ?, ?, ?)", (ca['Caller'], 12345, 100, 1))
        conn.commit(); conn.close()
    def create_whatsapp_db(self, chats):
        db_path = os.path.join(PATH_WHATSAPP_DB, "msgstore.db"); conn = sqlite3.connect(db_path); c = conn.cursor()
        c.execute("CREATE TABLE messages (_id INTEGER PRIMARY KEY, data TEXT)")
        for ch in chats: c.execute("INSERT INTO messages (data) VALUES (?)", (ch['Body'],))
        conn.commit(); conn.close()
    def create_signal_db(self, chats):
        db_path = os.path.join(PATH_SIGNAL, "signal.db"); conn = sqlite3.connect(db_path); c = conn.cursor()
        c.execute("CREATE TABLE sms (_id INTEGER PRIMARY KEY, body TEXT)")
        for ch in chats: c.execute("INSERT INTO sms (body) VALUES (?)", (ch['Body'],))
        conn.commit(); conn.close()
    def create_browser_db(self, history):
        db_path = os.path.join(PATH_CHROME_DB, "History"); conn = sqlite3.connect(db_path); c = conn.cursor()
        c.execute("CREATE TABLE urls (_id INTEGER PRIMARY KEY, url TEXT)")
        for h in history: c.execute("INSERT INTO urls (url) VALUES (?)", (h['URL'],))
        conn.commit(); conn.close()

class TimelineEngine:
    def create_master_timeline(self, all_data, filename):
        master = []
        for d in all_data.get('chats', []): master.append({"Timestamp": d['Timestamp'], "Type": "Chat", "Detail": d['Body'][:20]})
        pd.DataFrame(master).to_csv(os.path.join(PATH_REPORTS, filename), index=False)

class UsageStatsEngine:
    def generate_usage_stats(self, installed_apps, start, end):
        data = [{"Timestamp": start.strftime("%Y-%m-%d"), "App": "com.android.deskclock"}]
        pd.DataFrame(data).to_csv(os.path.join(PATH_USAGE, "daily_events.csv"), index=False)

class DigitalWellbeingEngine:
    def generate_db(self, start_date, end_date, installed_apps):
        try:
            conn = sqlite3.connect(os.path.join(PATH_WELLBEING, "app_usage.db")); c = conn.cursor()
            c.execute("CREATE TABLE events (_id INTEGER PRIMARY KEY, timestamp INTEGER, package_name TEXT, type INTEGER)")
            current = start_date
            while current < end_date:
                if 8 <= current.hour <= 22 and random.random() < 0.4:
                    pkg = random.choice(installed_apps)
                    ts = int(current.timestamp() * 1000)
                    c.execute("INSERT INTO events (timestamp, package_name, type) VALUES (?, ?, ?)", (ts, pkg, 1))
                    current += timedelta(minutes=random.randint(15, 60))
                else: current += timedelta(hours=1)
            conn.commit(); conn.close()
        except: pass

class MediaStoreEngine:
    def generate_db(self):
        try:
            conn = sqlite3.connect(os.path.join(PATH_MEDIA_DB, "external.db")); c = conn.cursor()
            c.execute("CREATE TABLE files (_id INTEGER PRIMARY KEY, _data TEXT, date_added INTEGER, media_type INTEGER, mime_type TEXT)")
            if os.path.exists(PATH_DCIM):
                for f in os.listdir(PATH_DCIM):
                    path = os.path.join(PATH_DCIM, f)
                    ts = int(os.path.getmtime(path))
                    c.execute("INSERT INTO files (_data, date_added, media_type, mime_type) VALUES (?, ?, ?, ?)", (path, ts, 1, "image/jpeg"))
            conn.commit(); conn.close()
        except: pass

class WifiScanEngine:
    def generate_logs(self, start_date, end_date):
        log_content = ""
        current = start_date
        aps = ["Neighbor_Wifi", "Xfinity_Wifi", "iPhone_Hotspot"]
        while current < end_date:
            if random.random() < 0.2:
                ts = int(current.timestamp() * 1000)
                log_content += f"Timestamp={ts} SSID={random.choice(aps)} RSSI=-50\n"
                current += timedelta(minutes=45)
            else: current += timedelta(hours=1)
        try:
            with open(os.path.join(PATH_MISC_WIFI, "wlan_scan_cache"), "w") as f: f.write(log_content)
        except: pass

class MapsCacheEngine:
    def generate_cache(self):
        try:
            for i in range(10):
                fname = f"tile_{random.randint(100,999)}_{random.randint(100,999)}.png"
                with open(os.path.join(PATH_MAPS_CACHE, fname), "wb") as f: f.write(os.urandom(1024))
        except: pass

class TrashBinEngine:
    def move_to_trash(self):
        if not os.path.exists(PATH_DCIM): return
        files = os.listdir(PATH_DCIM)
        if not files: return
        target_count = max(1, int(len(files) * 0.05))
        to_delete = random.sample(files, target_count)
        for f in to_delete:
            src = os.path.join(PATH_DCIM, f)
            dst = os.path.join(PATH_TRASH, f"{int(time.time())}_{f}")
            try: shutil.move(src, dst)
            except: pass

class GoogleSearchEngine:
    def generate_db(self, owner, start_date, end_date):
        try:
            conn = sqlite3.connect(os.path.join(PATH_GSEARCH, "search_history.db")); c = conn.cursor()
            c.execute("CREATE TABLE suggestions (_id INTEGER PRIMARY KEY, query TEXT, date INTEGER)")
            queries = ["restaurants near me", "weather", "how to hide files"]
            current = start_date
            while current < end_date:
                if random.random() < 0.1:
                    ts = int(current.timestamp() * 1000)
                    c.execute("INSERT INTO suggestions (query, date) VALUES (?, ?)", (random.choice(queries), ts))
                    current += timedelta(days=1)
                else: current += timedelta(hours=6)
            conn.commit(); conn.close()
        except: pass

class PermissionsEngine:
    def generate_xml(self, installed_apps):
        root = ET.Element("runtime-permissions")
        try:
            with open(os.path.join(PATH_SYSTEM_USERS, "runtime-permissions.xml"), "w") as f: f.write(prettify_xml(root))
        except: pass

class SimCardEngine:
    def generate_xml(self):
        root = ET.Element("sim_cards")
        try:
            with open(os.path.join(PATH_RADIO, "sim_cards.xml"), "w") as f: f.write(prettify_xml(root))
        except: pass

# --- Worker ---
class ChatWorker(QObject):
    finished = Signal(); progress = Signal(int); log = Signal(str); error = Signal(str)
    def __init__(self, total_messages, export_format, settings, flags):
        super().__init__(); self.tm = total_messages; self.fmt = export_format; self.sets = settings; self.f = flags; self.running = True
    
    def run(self):
        try:
            create_android_structure()
            owner = f"{self.sets['fname']} {self.sets['sname']}"
            start = self.sets['start']; end = self.sets['end']
            installed = self.sets['installed_apps']
            
            self.log.emit(f"Building System & User Data for: {owner}")
            self.progress.emit(5)
            
            # 1. System Artifacts
            self.log.emit("Generating System Artifacts...")
            if self.f.get('meta', True): DeviceInfoEngine().generate_device_info(owner)
            SystemArtifactsEngine().generate_wifi_config()
            SystemArtifactsEngine().generate_accounts_db(owner)
            
            # NEW: Shared Prefs & Deep System
            if self.f.get('recent', True): 
                self.log.emit("Gen XML Prefs & Deep Artifacts...")
                SharedPrefsEngine().generate_prefs(owner, installed)
                PackageManagerEngine().generate_packages_xml(installed, start)
                
                # New Engines v27
                DigitalWellbeingEngine().generate_db(start, end, installed)
                MediaStoreEngine().generate_db()
                WifiScanEngine().generate_logs(start, end)
                MapsCacheEngine().generate_cache()
                GoogleSearchEngine().generate_db(owner, start, end)
                PermissionsEngine().generate_xml(installed)
                SimCardEngine().generate_xml()
            self.progress.emit(10)

            # 2. Graph & Apps
            self.log.emit("Building Social Graph...")
            pe = PersonaEngine(); graph = pe.generate_social_graph(owner, self.sets['net_size'], installed)
            ae = AppListEngine(); apps_data = ae.generate_app_list(installed)
            try: pd.DataFrame(apps_data).to_excel(os.path.join(PATH_REPORTS, "installed_apps.xlsx"), index=False)
            except: pass
            self.progress.emit(15)

            # 3. Chats Logic
            self.log.emit("Simulating Chats...")
            humanizer = TextHumanizer()
            
            sms_data = []; whatsapp_data = []; signal_data = []; all_data = []; deleted_data = []
            current = start; msg_count = 0; participants = list(graph.keys())
            if not participants: self.log.emit("Error: No participants."); self.finished.emit(); return
            avg_gap = (end - start).total_seconds() / max(self.tm, 1)
            
            track = [] # Keep track for GPS
            
            while msg_count < self.tm and self.running:
                if current > end: break
                p_name = random.choice(participants); p_data = graph[p_name]
                chat_plats = [p for p in p_data["Platforms"] if p not in ["Phone", "Email", "Zoom", "Google Meet"]]
                if not chat_plats: chat_plats = ["Messages (SMS)"]
                plat = random.choice(chat_plats)
                t_key = random.choice(p_data["Topics"]); convo = TOPIC_CONTENT.get(t_key, [])
                current += timedelta(seconds=random.randint(int(avg_gap * 0.2), int(avg_gap * 1.8)))
                
                # Track GPS for Telephony DB
                le = LocationEngine()
                pt = le.get_location_for_time(current)
                track.append({"timestamp": current.strftime("%Y-%m-%dT%H:%M:%SZ"), "latitude": pt[0], "longitude": pt[1]})
                
                for s_role, content in convo:
                    if msg_count >= self.tm: break
                    r_sender = owner if s_role == "Owner" else p_name
                    r_recip = p_name if s_role == "Owner" else owner
                    direc = "Outgoing" if r_sender == owner else "Incoming"
                    hum = humanizer.humanize(content, 2 if p_data["Role"]=="Friend" else 0)
                    att_val = ""
                    if "." in content and len(content) < 30:
                        ext = os.path.splitext(content)[1].lower()
                        if ext in ['.jpg','.png']: generate_jpg(content, current); att_val = f"/sdcard/DCIM/{content}"
                        elif ext in ['.pdf','.docx']: generate_doc(content, current); att_val = f"/sdcard/Download/{content}"

                    entry = {"Platform": plat, "Sender": r_sender, "Recipient": r_recip, "Direction": direc, "Body": hum, "Timestamp": current.strftime("%Y-%m-%d %H:%M:%S"), "Attachment": att_val}
                    
                    if self.f.get('delete', False) and random.random() < 0.05: deleted_data.append(entry)
                    else:
                        all_data.append(entry)
                        if "WhatsApp" in plat: whatsapp_data.append(entry)
                        elif "Signal" in plat: signal_data.append(entry)
                        else: sms_data.append(entry)
                    msg_count += 1; current += timedelta(seconds=random.randint(20, 120))
                prog = 15 + int((msg_count / self.tm) * 65); self.progress.emit(prog)

            # 4. Save DBs & Deep Artifacts
            self.log.emit("Writing App Databases...")
            dbe = DatabaseEngine()
            if sms_data: dbe.create_sms_db(sms_data)
            if whatsapp_data: dbe.create_whatsapp_db(whatsapp_data)
            if signal_data: dbe.create_signal_db(signal_data)
            
            if self.f.get('recent', True): 
                self.log.emit("Gen Deep System...")
                RecentTasksEngine().generate_snapshots(installed)
                UserDictionaryEngine().generate_dictionary(participants, humanizer)
                DownloadManagerEngine().generate_download_db()
                BluetoothConfigEngine().generate_bt_config()
                # FIX: Pass all_data (the chat list), not all_chats
                NotificationHistoryEngine().generate_notification_db(all_data, start, end)
                ClipboardEngine().generate_clipboard(all_data)
                TelephonyEngine().generate_telephony_db(track)
                TrashBinEngine().move_to_trash()

            # 5. Save Reports & Hash
            self.log.emit("Saving Final Reports...")
            try: pd.DataFrame(all_data).to_excel(os.path.join(PATH_REPORTS, "chat_report.xlsx"), index=False)
            except: pass
            
            if self.f.get('hash', True): self.log.emit("Hashing..."); HashEngine().generate_manifest()

            # 6. Zip Output (NEW)
            self.log.emit("Creating Forensic Zip Image...")
            zip_name = f"Forensic_Image_{owner.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            shutil.make_archive(zip_name, 'zip', ROOT_DIR)
            self.log.emit(f"Image Created: {zip_name}.zip")

            self.progress.emit(100); self.log.emit("Done!"); self.finished.emit()
        except Exception as e: self.error.emit(str(e)); self.finished.emit()

# --- Forensic Parser Window (NEW) ---
class ForensicParserWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Forensic Analyzer Lite"); self.resize(800, 600)
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        
        # Tabs
        self.tab_info = QWidget(); self.setup_info_tab(); self.tabs.addTab(self.tab_info, "Device Info")
        self.tab_chats = QWidget(); self.setup_chat_tab(); self.tabs.addTab(self.tab_chats, "Chats (SMS)")
        self.tab_calls = QWidget(); self.setup_call_tab(); self.tabs.addTab(self.tab_calls, "Calls")
        
        # Menu
        self.menu = self.menuBar().addMenu("File")
        self.act_load_folder = QAction("Load Folder", self); self.act_load_folder.triggered.connect(self.load_folder)
        self.menu.addAction(self.act_load_folder)
        
        self.act_load_zip = QAction("Load Zip Archive", self); self.act_load_zip.triggered.connect(self.load_zip)
        self.menu.addAction(self.act_load_zip)
        
        self.extraction_path = ""
        self.temp_dir = None # Keep track to clean up later if needed

    def setup_info_tab(self):
        l = QVBoxLayout(self.tab_info); self.txt_info = QTextEdit(); self.txt_info.setReadOnly(True); l.addWidget(self.txt_info)

    def setup_chat_tab(self):
        l = QVBoxLayout(self.tab_chats); self.tbl_chats = QTableWidget(); l.addWidget(self.tbl_chats)

    def setup_call_tab(self):
        l = QVBoxLayout(self.tab_calls); self.tbl_calls = QTableWidget(); l.addWidget(self.tbl_calls)

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Android_Extraction Folder")
        if folder:
            self.extraction_path = folder
            self.run_parsers()

    def load_zip(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Forensic Image (Zip)", "", "Zip Files (*.zip)")
        if path:
            try:
                self.temp_dir = tempfile.mkdtemp()
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
                
                # Check structure
                if os.path.exists(os.path.join(self.temp_dir, "Android_Extraction")):
                    self.extraction_path = os.path.join(self.temp_dir, "Android_Extraction")
                else:
                    self.extraction_path = self.temp_dir
                
                self.run_parsers()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Invalid Zip: {e}")

    def run_parsers(self):
        self.parse_info()
        self.parse_sms()
        self.parse_calls()

    def parse_info(self):
        try:
            with open(os.path.join(self.extraction_path, "device_info.json"), 'r') as f:
                data = json.load(f)
                self.txt_info.setText(json.dumps(data, indent=4))
        except: self.txt_info.setText("device_info.json not found.")

    def parse_sms(self):
        db_path = os.path.join(self.extraction_path, "data/data/com.android.providers.telephony/databases/mmssms.db")
        if not os.path.exists(db_path): return
        conn = sqlite3.connect(db_path); c = conn.cursor()
        try:
            c.execute("SELECT address, date, body, type FROM sms")
            rows = c.fetchall()
            self.tbl_chats.setRowCount(len(rows)); self.tbl_chats.setColumnCount(4); self.tbl_chats.setHorizontalHeaderLabels(["Address", "Date", "Body", "Type"])
            for i, row in enumerate(rows):
                self.tbl_chats.setItem(i, 0, QTableWidgetItem(str(row[0])))
                self.tbl_chats.setItem(i, 1, QTableWidgetItem(datetime.fromtimestamp(row[1]/1000).strftime('%Y-%m-%d %H:%M:%S')))
                self.tbl_chats.setItem(i, 2, QTableWidgetItem(str(row[2])))
                self.tbl_chats.setItem(i, 3, QTableWidgetItem("Incoming" if row[3]==1 else "Outgoing"))
        except: pass
        conn.close()

    def parse_calls(self):
        db_path = os.path.join(self.extraction_path, "data/data/com.android.providers.contacts/databases/calllog.db")
        if not os.path.exists(db_path): return
        conn = sqlite3.connect(db_path); c = conn.cursor()
        try:
            c.execute("SELECT number, date, duration, type FROM calls")
            rows = c.fetchall()
            self.tbl_calls.setRowCount(len(rows)); self.tbl_calls.setColumnCount(4); self.tbl_calls.setHorizontalHeaderLabels(["Number", "Date", "Duration", "Type"])
            for i, row in enumerate(rows):
                self.tbl_calls.setItem(i, 0, QTableWidgetItem(str(row[0])))
                self.tbl_calls.setItem(i, 1, QTableWidgetItem(datetime.fromtimestamp(row[1]/1000).strftime('%Y-%m-%d %H:%M:%S')))
                self.tbl_calls.setItem(i, 2, QTableWidgetItem(str(row[2])))
                t = "Incoming" if row[3]==1 else ("Outgoing" if row[3]==2 else "Missed")
                self.tbl_calls.setItem(i, 3, QTableWidgetItem(t))
        except: pass
        conn.close()

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("ALF Forensics - Android Generator V30"); self.resize(900, 800)
        central = QWidget(); self.setCentralWidget(central); main_layout = QVBoxLayout(central)
        
        # Header with Parser Button
        header = QHBoxLayout()
        header.addWidget(QLabel("Forensic Generator"))
        self.btn_parser = QPushButton("Launch Analyzer Tool")
        self.btn_parser.clicked.connect(self.open_parser)
        header.addWidget(self.btn_parser)
        main_layout.addLayout(header)

        gb = QGroupBox("1. User Identity"); l = QFormLayout()
        self.fname_inp = QLineEdit(DEFAULT_FIRST_NAME); self.sname_inp = QLineEdit(DEFAULT_SURNAME)
        self.net_size = QSpinBox(); self.net_size.setValue(15)
        l.addRow("First Name:", self.fname_inp); l.addRow("Surname:", self.sname_inp); l.addRow("Social Size:", self.net_size)
        gb.setLayout(l); main_layout.addWidget(gb)
        
        gb_apps = QGroupBox("2. Apps"); la = QVBoxLayout()
        self.app_list = QListWidget()
        for app in OPTIONAL_APPS: 
            it = QListWidgetItem(app); it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Unchecked); self.app_list.addItem(it)
        for i in range(self.app_list.count()):
            if self.app_list.item(i).text() in ["WhatsApp", "Chrome"]: self.app_list.item(i).setCheckState(Qt.Checked)
        la.addWidget(self.app_list); gb_apps.setLayout(la); main_layout.addWidget(gb_apps)
        
        gb_time = QGroupBox("3. Timeframe"); lt = QHBoxLayout()
        self.start = QDateTimeEdit(datetime(2023,1,1,9,0)); self.start.setCalendarPopup(True)
        self.end = QDateTimeEdit(datetime(2023,2,1,18,0)); self.end.setCalendarPopup(True)
        self.act = QComboBox(); self.act.addItems(["Quiet", "Moderate", "Active", "Hyper"]); self.act.setCurrentIndex(1)
        lt.addWidget(self.start); lt.addWidget(self.end); lt.addWidget(self.act); gb_time.setLayout(lt); main_layout.addWidget(gb_time)
        
        gb_for = QGroupBox("4. Forensic Layers"); l_for = QHBoxLayout()
        self.cb_meta = QCheckBox("Meta/Hash"); self.cb_meta.setChecked(True); l_for.addWidget(self.cb_meta)
        self.cb_del = QCheckBox("Deleted Data"); self.cb_del.setChecked(True); l_for.addWidget(self.cb_del)
        self.cb_sys = QCheckBox("Deep System (XML/Registry/Clip/Towers)"); self.cb_sys.setChecked(True); l_for.addWidget(self.cb_sys)
        gb_for.setLayout(l_for); main_layout.addWidget(gb_for)

        self.btn_gen = QPushButton("GENERATE ANDROID EXTRACTION"); self.btn_gen.setMinimumHeight(50); self.btn_gen.clicked.connect(self.start_gen)
        main_layout.addWidget(self.btn_gen); self.pb = QProgressBar(); main_layout.addWidget(self.pb)
        self.log = QTextEdit(); self.log.setReadOnly(True); main_layout.addWidget(self.log)

    def open_parser(self):
        self.parser_window = ForensicParserWindow()
        self.parser_window.show()

    def get_installed_apps(self):
        apps = list(NATIVE_APPS)
        for i in range(self.app_list.count()):
            if self.app_list.item(i).checkState() == Qt.Checked: apps.append(self.app_list.item(i).text())
        return apps

    def start_gen(self):
        self.log.clear(); installed = self.get_installed_apps()
        sets = {"fname": self.fname_inp.text(), "sname": self.sname_inp.text(), "net_size": self.net_size.value(), "start": self.start.dateTime().toPython(), "end": self.end.dateTime().toPython(), "installed_apps": installed}
        rates = [10, 40, 80, 150]; daily = rates[self.act.currentIndex()]; days = (sets["end"] - sets["start"]).days or 1; total = days * daily
        
        sys_flag = self.cb_sys.isChecked()
        flags = {
            'call': True, 'meta': self.cb_meta.isChecked(), 'hash': self.cb_meta.isChecked(), 
            'delete': self.cb_del.isChecked(), 'usage': True, 
            'recent': sys_flag, 'dict': sys_flag, 'dl': sys_flag, 'bt_conf': sys_flag, 'notif': sys_flag
        }
        self.thread = QThread(); self.worker = ChatWorker(total, "xlsx", sets, flags)
        self.worker.moveToThread(self.thread); self.worker.finished.connect(self.thread.quit)
        self.worker.log.connect(self.log.append); self.worker.progress.connect(self.pb.setValue)
        self.thread.started.connect(self.worker.run); self.thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec())