import sqlite3
import json
import random
import shutil
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging
from pathlib import Path
from typing import Dict, List, Union
from faker import Faker
from datetime import datetime, timedelta

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from core.file_system import AndroidFileSystem

class SystemEngine:
    def __init__(self, fs: AndroidFileSystem, logger: logging.Logger):
        self.fs = fs
        self.logger = logger
        self.fake = Faker()

    def _prettify_xml(self, elem) -> str:
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    # --- CORE SYSTEM METHODS ---
    def generate_wifi_config(self, ssids: List[str] = None):
        if ssids is None: ssids = ["Home_Network", "Starbucks_WiFi", "Airport_Free_Wifi"]
        root = ET.Element("WifiConfigStoreData")
        net_list = ET.SubElement(root, "NetworkList")
        for ssid in ssids:
            net = ET.SubElement(net_list, "Network")
            ET.SubElement(net, "SSID").text = f'"{ssid}"'
            ET.SubElement(net, "ConfigKey").text = f'"{ssid}"WPA_PSK'
        path = self.fs.get_path("wifi") / "WifiConfigStore.xml"
        try:
            with open(path, "w") as f: f.write(self._prettify_xml(root))
        except OSError: pass

    def generate_accounts_db(self, owner_email: str, installed_apps: Dict[str, str]):
        path = self.fs.get_path("system_users")
        path.mkdir(parents=True, exist_ok=True)
        db_path = path / "accounts.db"
        username_base = owner_email.split('@')[0]
        try:
            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS accounts (_id INTEGER PRIMARY KEY, name TEXT, type TEXT)")
                c.execute("INSERT INTO accounts (name, type) VALUES (?, ?)", (owner_email, "com.google"))
                for app_name, pkg in installed_apps.items():
                    account_type, account_name = None, None
                    if "whatsapp" in pkg: account_type, account_name = "com.whatsapp", self.fake.phone_number()
                    elif "telegram" in pkg: account_type, account_name = "org.telegram.messenger", self.fake.phone_number()
                    elif "instagram" in pkg: account_type, account_name = "com.instagram", f"{username_base}_{random.randint(10,99)}"
                    elif "facebook" in pkg: account_type, account_name = "com.facebook.auth.login", owner_email
                    elif "twitter" in pkg: account_type, account_name = "com.twitter.android.auth.login", f"@{username_base}"
                    if account_type: c.execute("INSERT INTO accounts (name, type) VALUES (?, ?)", (account_name, account_type))
                conn.commit()
        except sqlite3.Error: pass

    def generate_packages_xml(self, installed_apps: Dict[str, str], install_time_ts: float):
        root = ET.Element("packages")
        sorted_items = sorted(installed_apps.items(), key=lambda x: x[1])
        for i, (name, pkg) in enumerate(sorted_items):
            uid = 10000 + i
            ET.SubElement(root, "package", name=pkg, codePath=f"/data/app/{pkg}-1", userId=str(uid), it=str(int(install_time_ts*1000)))
        path = self.fs.get_path("system") / "packages.xml"
        try:
            with open(path, "w") as f: f.write(self._prettify_xml(root))
        except OSError: pass

    def generate_json_artifacts(self, installed_apps: Dict[str, str]):
        data_root = self.fs.get_path("data")
        for app_name, pkg_name in installed_apps.items():
            if app_name in ["Phone", "Settings", "Calculator"]: continue
            app_dir = data_root / pkg_name
            cache_dir = app_dir / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            session_data = {
                "user_id": self.fake.uuid4(),
                "username": self.fake.user_name(),
                "is_active": True,
                "last_login": str(datetime.now()),
                "preferences": {"theme": "dark", "notifications_enabled": True}
            }
            try:
                with open(cache_dir / "user_session.json", "w") as f:
                    json.dump(session_data, f, indent=2)
            except OSError: pass

    def generate_protobuf_artifacts(self):
        usagestats_path = self.fs.get_path("system") / "usagestats" / "0" / "daily"
        usagestats_path.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            filename = f"{int(datetime.now().timestamp()) - (i*86400)}"
            with open(usagestats_path / filename, "wb") as f:
                f.write(b"\x0A\x45\x08\x01\x12") 
                f.write(self.fake.binary(length=128))

    def generate_cloud_takeout(self, owner_email):
        takeout_path = self.fs.get_path("sdcard") / "Takeout"
        takeout_path.mkdir(parents=True, exist_ok=True)
        activity_html = f"""<html><body><h1>My Activity</h1><p>User: {owner_email}</p><ul><li>Searched for 'How to disappear completely'</li></ul></body></html>"""
        with open(takeout_path / "MyActivity.html", "w") as f: f.write(activity_html)
        loc_json = {"locations": [{"timestampMs": str(int(datetime.now().timestamp()*1000)), "latitudeE7": 407488000, "longitudeE7": -739854000}]}
        with open(takeout_path / "LocationHistory.json", "w") as f: json.dump(loc_json, f)
        shutil.make_archive(str(self.fs.get_path("sdcard") / "google_takeout"), 'zip', takeout_path)
        shutil.rmtree(takeout_path)

    def generate_bluetooth_config(self):
        path = self.fs.get_path("misc") / "bluedroid"
        path.mkdir(parents=True, exist_ok=True)
        config = "[Adapter]\nAddress=11:22:33:44:55:66\nName=Pixel_User\n\n[PairedDevices]\nC4:D0:E3:11:22:33=Toyota Camry\nA0:B1:C2:33:44:55=AirPods Pro\n"
        try:
            with open(path / "bt_config.conf", "w") as f: f.write(config)
        except OSError: pass

    def generate_digital_wellbeing(self, installed_apps: Dict[str, str]):
        path = self.fs.get_path("data") / "com.google.android.apps.wellbeing" / "databases"
        path.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(path / "app_usage.db") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS events (_id INTEGER PRIMARY KEY, timestamp INTEGER, package_name TEXT, type INTEGER)")
                pkgs = list(installed_apps.values())
                if not pkgs: pkgs = ["com.android.chrome"]
                start_ts = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
                for i in range(50):
                    ts = start_ts + (i * 1000 * 60 * random.randint(10, 60))
                    pkg = random.choice(pkgs)
                    c.execute("INSERT INTO events (timestamp, package_name, type) VALUES (?, ?, ?)", (ts, pkg, 1))
                conn.commit()
        except sqlite3.Error: pass

    def generate_runtime_permissions(self, installed_apps: Dict[str, str]):
        path = self.fs.get_path("system_users"); path.mkdir(parents=True, exist_ok=True)
        root = ET.Element("runtime-permissions")
        for pkg in installed_apps.values():
            pkg_elem = ET.SubElement(root, "pkg", name=pkg)
            perms = ["android.permission.INTERNET"]
            if random.random() < 0.5: perms.append("android.permission.ACCESS_FINE_LOCATION")
            for p in perms: ET.SubElement(pkg_elem, "item", name=p, granted="true", flags="0")
        try:
            with open(path / "runtime-permissions.xml", "w") as f: f.write(self._prettify_xml(root))
        except OSError: pass

    def generate_shared_preferences(self, installed_apps: Dict[str, str]):
        data_root = self.fs.get_path("data")
        for pkg in installed_apps.values():
            prefs_dir = data_root / pkg / "shared_prefs"; prefs_dir.mkdir(parents=True, exist_ok=True)
            root = ET.Element("map")
            ET.SubElement(root, "string", name="device_id", value=self.fake.uuid4())
            try:
                with open(prefs_dir / f"{pkg}_preferences.xml", "w") as f: f.write(self._prettify_xml(root))
            except OSError: pass

    def generate_recent_snapshots(self, installed_apps: Dict[str, str]):
        if not PIL_AVAILABLE: return
        path = self.fs.get_path("system") / "recent_images"; path.mkdir(parents=True, exist_ok=True)
        pkgs = list(installed_apps.values())
        for _ in range(5):
            pkg = random.choice(pkgs)
            img = Image.new('RGB', (540, 1200), color=(random.randint(50,200), random.randint(50,200), random.randint(50,200)))
            draw = ImageDraw.Draw(img); draw.text((100, 500), f"Snapshot: {pkg}", fill="white")
            try: img.save(path / f"{random.randint(1000,9000)}_snapshot.jpg", "JPEG", quality=50)
            except OSError: pass

    def generate_notification_history(self, messages: List[Dict]):
        path = self.fs.get_path("system"); path.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(path / "notification_log.db") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS log (_id INTEGER PRIMARY KEY, package_name TEXT, post_time INTEGER, title TEXT, text TEXT)")
                for msg in messages[-20:]:
                    pkg = "com.whatsapp" if "WhatsApp" in msg.get('Platform', '') else "com.google.android.apps.messaging"
                    ts = int(datetime.strptime(msg['Timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
                    c.execute("INSERT INTO log (package_name, post_time, title, text) VALUES (?, ?, ?, ?)", (pkg, ts, msg['Sender'], msg['Body']))
                conn.commit()
        except sqlite3.Error: pass

    def generate_wifi_scan_logs(self, geo_points: List[Dict]):
        path = self.fs.get_path("misc") / "wifi"; path.mkdir(parents=True, exist_ok=True)
        log_content = ""
        common_ssids = ["Xfinity_WiFi", "Linksys", "Netgear"]
        for pt in geo_points:
            if random.random() < 0.1:
                log_content += f"{pt['timestamp']} SCAN_RESULT: SSID={random.choice(common_ssids)} RSSI={random.randint(-90, -40)}\n"
        try:
            with open(path / "wlan_logs.txt", "w") as f: f.write(log_content)
        except OSError: pass

    def generate_clipboard_history(self):
        path = self.fs.get_path("clipboard"); path.mkdir(parents=True, exist_ok=True)
        clips = ["Password123!", "Meet me at 5", self.fake.address()]
        for i, clip in enumerate(clips):
            try:
                with open(path / f"clip_{i+1}", "w") as f: f.write(clip)
            except OSError: pass

    def generate_battery_stats(self):
        path = self.fs.get_path("system") / "batterystats"; path.mkdir(parents=True, exist_ok=True)
        log = "Battery History:\n"
        start_time = datetime.now() - timedelta(hours=24)
        for i in range(24):
            ts = start_time + timedelta(hours=i)
            level = 100 - (i * 3) if i < 12 else 50 - ((i-12) * 2)
            log += f"{ts.strftime('%Y-%m-%d %H:%M:%S')} Level={level} status=discharging\n"
        try:
            with open(path / "batterystats.txt", "w") as f: f.write(log)
        except OSError: pass

    def generate_system_dropbox(self):
        path = self.fs.get_path("dropbox"); path.mkdir(parents=True, exist_ok=True)
        ts = int(datetime.now().timestamp() * 1000)
        fname = f"data_app_crash@{ts}.txt"
        content = "Process: org.thoughtcrime.securesms\nFlags: 0x20c8be\nPackage: org.thoughtcrime.securesms v1337\n\njava.lang.NullPointerException..."
        try:
            with open(path / fname, "w") as f: f.write(content)
        except OSError: pass

    def generate_vpn_logs(self):
        path = self.fs.get_path("data") / "com.nordvpn.android" / "files"; path.mkdir(parents=True, exist_ok=True)
        log = f"{datetime.now()} [INFO] Connecting to us.nordvpn.com\n{datetime.now()} [INFO] Tunnel established."
        try:
            with open(path / "connection_log.txt", "w") as f: f.write(log)
        except OSError: pass

    def generate_multi_user_artifacts(self):
        path = self.fs.get_path("user_10") / "files"; path.mkdir(parents=True, exist_ok=True)
        try:
            with open(path / "secret_project.txt", "w") as f:
                f.write("This file is hidden in User 10 partition.")
        except OSError: pass

    def generate_vault_app(self):
        path = self.fs.get_path("data") / "com.calculator.vault" / "files" / ".secret_data"; path.mkdir(parents=True, exist_ok=True)
        try:
            if PIL_AVAILABLE:
                img = Image.new('RGB', (100, 100), color='red')
                img.save(path / "hidden_photo.jpg")
        except: pass

    def generate_lock_settings(self):
        path = self.fs.get_path("system"); path.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(path / "locksettings.db") as conn:
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS locksettings (_id INTEGER PRIMARY KEY, name TEXT, user INTEGER, value TEXT)")
                c.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)", ("lockscreen.password_type", 0, "131072"))
                c.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)", ("lockscreen.disabled", 0, "0"))
                c.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)", ("lockscreen.password_salt", 0, self.fake.hexify(text="^" * 16)))
                conn.commit()
        except sqlite3.Error: pass
        try:
            with open(path / "gatekeeper.password.key", "wb") as f: f.write(os.urandom(64))
        except OSError: pass

    def generate_build_prop(self):
        path = self.fs.get_path("root") / "system"; path.mkdir(parents=True, exist_ok=True)
        content = "\n# build properties\nro.build.id=UQ1A.240105.004\nro.product.brand=google\nro.product.model=Pixel 8 Pro\nro.board.platform=zuma\n"
        try:
            with open(path / "build.prop", "w") as f: f.write(content.strip())
        except OSError: pass

    def generate_secure_settings(self):
        path = self.fs.get_path("system_users"); path.mkdir(parents=True, exist_ok=True)
        root = ET.Element("settings", version="190")
        ET.SubElement(root, "setting", id="1", name="android_id", value=self.fake.hexify(text="^" * 16), package="android")
        ET.SubElement(root, "setting", id="2", name="adb_enabled", value="1", package="android")
        ET.SubElement(root, "setting", id="3", name="install_non_market_apps", value="1", package="android")
        ET.SubElement(root, "setting", id="4", name="lock_screen_show_notifications", value="1", package="android")
        try:
            with open(path / "settings_secure.xml", "w") as f: f.write(self._prettify_xml(root))
        except OSError: pass

    def generate_app_ops(self, installed_apps: Dict[str, str]):
        path = self.fs.get_path("system"); path.mkdir(parents=True, exist_ok=True)
        root = ET.Element("app-ops")
        for pkg in installed_apps.values():
            pkg_elem = ET.SubElement(root, "pkg", n=pkg)
            ops = [("1", "ACCESS_FINE_LOCATION"), ("26", "CAMERA")]
            for op_code, _ in ops:
                ts = int((datetime.now() - timedelta(hours=random.randint(0, 24))).timestamp() * 1000)
                ET.SubElement(pkg_elem, "op", n=op_code, t=str(ts), d=str(random.randint(100, 5000)))
        try:
            with open(path / "appops.xml", "w") as f: f.write(self._prettify_xml(root))
        except OSError: pass

    def generate_sync_history(self, owner_email: str):
        path = self.fs.get_path("system") / "sync"; path.mkdir(parents=True, exist_ok=True)
        root = ET.Element("accounts")
        ET.SubElement(root, "authority", id="0", account=owner_email, type="com.google", authority="com.android.contacts", enabled="true")
        ET.SubElement(root, "authority", id="1", account=owner_email, type="com.google", authority="com.google.android.gm.email.provider", enabled="true")
        try:
            with open(path / "accounts.xml", "w") as f: f.write(self._prettify_xml(root))
        except OSError: pass

    def generate_recovery_logs(self):
        path = self.fs.get_path("root") / "cache" / "recovery"; path.mkdir(parents=True, exist_ok=True)
        log_content = """-- Wiping data...\nFormatting /data...\nFormatting /cache...\nData wipe complete.\n-- Install /package...\nFinding update package...\nOpening update package...\nVerifying update package...\nInstalling update...\nTarget: google/husky/husky:14/UQ1A.240105.004/11204736:user/release-keys\nPatching system image after verification.\nScript succeeded: result was [1.000000]\n"""
        try:
            with open(path / "last_log", "w") as f: f.write(log_content)
        except OSError: pass

    def generate_user_profile(self, start_date: datetime):
        path = self.fs.get_path("system") / "users"; path.mkdir(parents=True, exist_ok=True)
        try:
            with open(path / "0.xml", "w") as f: f.write("<user/>")
        except OSError: pass

    def generate_setup_wizard_data(self, start_date: datetime):
        data_root = self.fs.get_path("data")
        wiz_dir = data_root / "com.google.android.setupwizard" / "shared_prefs"; wiz_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(wiz_dir / "setup_wizard.xml", "w") as f: f.write("<map/>")
        except OSError: pass

    def generate_samsung_secure_folder(self):
        secure_folder_root = self.fs.get_path("secure_folder")
        secure_files = secure_folder_root / "files"
        users_system_path = self.fs.get_path("system_users_base")
        secure_files.mkdir(parents=True, exist_ok=True)
        users_system_path.mkdir(parents=True, exist_ok=True)
        root = ET.Element("user", id="150", serialNumber="150", flags="30")
        ET.SubElement(root, "name").text = "Secure Folder"
        try:
            with open(users_system_path / "150.xml", "w") as f: f.write(self._prettify_xml(root))
        except OSError: pass
        try:
            with open(secure_files / "My_Secret_Note.txt", "w") as f: f.write("Secret")
        except OSError: pass

    # --- NEW: PIXEL PRIVATE SPACE ---
    def generate_pixel_private_space(self):
        """
        Feature: Creates artifacts for Android 15 'Private Space' (User 11).
        """
        # 1. Paths (User 11)
        private_root = self.fs.get_path("user_11") # /data/user/11
        private_files = private_root / "files"
        users_system_path = self.fs.get_path("system_users_base")
        
        private_files.mkdir(parents=True, exist_ok=True)
        users_system_path.mkdir(parents=True, exist_ok=True)

        # 2. User Profile XML (User 11)
        # flags="32" often denotes a private/managed profile
        root = ET.Element("user", id="11", serialNumber="11", flags="32", created=str(int(datetime.now().timestamp()*1000)))
        ET.SubElement(root, "name").text = "Private Space"
        ET.SubElement(root, "profileGroupId").text = "0"
        ET.SubElement(root, "userType").text = "android.os.usertype.profile.PRIVATE" # Valid Android 15 tag
        
        try:
            with open(users_system_path / "11.xml", "w") as f:
                f.write(self._prettify_xml(root))
        except OSError: pass

        # 3. Private Artifacts
        # Create a private Chrome download
        try:
            private_dl = private_root / "com.android.chrome" / "files" / "Download"
            private_dl.mkdir(parents=True, exist_ok=True)
            with open(private_dl / "flight_tickets_secret.pdf", "w") as f:
                f.write("This file exists only in the Private Space partition.")
        except OSError: pass