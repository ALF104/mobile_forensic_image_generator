import sqlite3
import json
import random
import shutil
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging
from pathlib import Path
from typing import Dict, List, Union, Optional
from faker import Faker
from datetime import datetime, timedelta

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from core.file_system import AndroidFileSystem
from core.db_manager import SQLiteDB

class SystemEngine:
    def __init__(self, fs: AndroidFileSystem, logger: logging.Logger, device_profile: Optional[Dict] = None):
        self.fs = fs
        self.logger = logger
        self.fake = Faker()
        self.profile = device_profile or {
            "manufacturer": "Google",
            "model": "Pixel 8",
            "board": "shiba",
            "device": "husky",
            "android_version": "14",
            "build_id": "UD1A.230803.022"
        }

    def _prettify_xml(self, elem) -> str:
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def generate_build_prop(self):
        path = self.fs.get_path("root") / "system"
        path.mkdir(parents=True, exist_ok=True)
        
        # Generate random Serial Number (8-12 chars)
        serial_no = self.fake.bothify(text="????????").upper()
        
        # Generate Primary IMEI (15 digits)
        imei1 = str(self.fake.random_number(digits=15))
        
        # Generate Secondary IMEI (Dual SIM) - 70% chance
        imei2 = ""
        if random.random() < 0.7:
            imei2 = f"\ngsm.imei2={self.fake.random_number(digits=15)}"

        content = f"""
# build properties
ro.build.id={self.profile.get('build_id', 'UNKNOWN')}
ro.build.display.id={self.profile.get('build_id', 'UNKNOWN')}
ro.build.version.incremental={random.randint(1000000, 9999999)}
ro.build.version.sdk={self.profile.get('android_version', '10')}
ro.build.version.release={self.profile.get('android_version', '10')}
ro.product.brand={self.profile.get('manufacturer', 'Generic')}
ro.product.model={self.profile.get('model', 'Generic Phone')}
ro.product.board={self.profile.get('board', 'generic_board')}
ro.product.device={self.profile.get('device', 'generic_device')}
ro.product.manufacturer={self.profile.get('manufacturer', 'Generic')}
ro.board.platform={self.profile.get('board', 'platform')}
# Identifiers
ro.serialno={serial_no}
gsm.version.baseband={self.profile.get('board', 'generic')}-123456-7890
gsm.imei={imei1}{imei2}
"""
        try:
            with open(path / "build.prop", "w") as f: f.write(content.strip())
        except OSError as e: self.logger.error(f"Build Prop Error: {e}")

    def generate_packages_xml(self, installed_apps: Dict[str, str], start_time_ts: float):
        """
        Generates packages.xml with randomized installation dates.
        """
        root = ET.Element("packages")
        ET.SubElement(root, "version", sdkVersion=self.profile.get("android_version", "13"), databaseVersion="3")
        
        sorted_items = sorted(installed_apps.items(), key=lambda x: x[1])
        
        for i, (name, pkg) in enumerate(sorted_items):
            uid = 10000 + i
            
            # Logic for Install Date:
            # Native apps (com.android.*, com.google.*) -> often install at "Setup Wizard" time (start_time_ts)
            # Third party apps -> installed randomly AFTER start time
            if "com.android" in pkg or "com.google" in pkg:
                install_ts = start_time_ts
            else:
                random_offset = random.randint(0, 30 * 24 * 3600) 
                install_ts = start_time_ts + random_offset

            ET.SubElement(root, "package", name=pkg, codePath=f"/data/app/{pkg}-1", userId=str(uid), it=str(int(install_ts*1000)))
            
        path = self.fs.get_path("system") / "packages.xml"
        try:
            with open(path, "w") as f: f.write(self._prettify_xml(root))
        except OSError as e: self.logger.error(f"Packages XML Error: {e}")

    def generate_play_store_data(self, owner_email: str, installed_apps: Dict[str, str]):
        """
        Generates Google Play Store artifacts (library.db) linking apps to the account.
        """
        path = self.fs.get_path("data") / "com.android.vending" / "databases"
        path.mkdir(parents=True, exist_ok=True)
        db_path = path / "library.db"

        with SQLiteDB(db_path, self.logger) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS ownership (
                account TEXT, 
                doc_id TEXT, 
                purchase_time_ms INTEGER, 
                preordered INTEGER
            )""")
            
            for pkg in installed_apps.values():
                # Random purchase time in the last 2 years
                purchase_ts = int((datetime.now() - timedelta(days=random.randint(5, 700))).timestamp() * 1000)
                c.execute("INSERT INTO ownership (account, doc_id, purchase_time_ms, preordered) VALUES (?, ?, ?, ?)", 
                          (owner_email, pkg, purchase_ts, 0))

        path_local = self.fs.get_path("data") / "com.android.vending" / "databases"
        db_local = path_local / "localappstate.db"
        with SQLiteDB(db_local, self.logger) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS appstate (
                package_name TEXT PRIMARY KEY, 
                auto_update INTEGER, 
                last_update_timestamp_ms INTEGER
            )""")
            for pkg in installed_apps.values():
                update_ts = int((datetime.now() - timedelta(days=random.randint(1, 30))).timestamp() * 1000)
                c.execute("INSERT INTO appstate (package_name, auto_update, last_update_timestamp_ms) VALUES (?, ?, ?)", 
                          (pkg, 1, update_ts))

    def generate_modern_accounts_db(self, owner_email: str, installed_apps: Dict[str, str]):
        """
        Generates split DE/CE account databases found in Android 7+.
        """
        path_de = self.fs.get_path("system_de") / "0"
        path_ce = self.fs.get_path("system_ce") / "0"
        path_de.mkdir(parents=True, exist_ok=True)
        path_ce.mkdir(parents=True, exist_ok=True)

        db_de = path_de / "accounts_de.db"
        db_ce = path_ce / "accounts_ce.db"

        accounts = []
        accounts.append({
            "name": owner_email,
            "type": "com.google",
            "password": None,
            "userdata": {"sub": self.fake.uuid4(), "given_name": owner_email.split('@')[0]}
        })

        username_base = owner_email.split('@')[0]
        for app_name, pkg in installed_apps.items():
            if "whatsapp" in pkg: 
                accounts.append({"name": self.fake.phone_number(), "type": "com.whatsapp", "userdata": {"push_name": username_base}})
            elif "telegram" in pkg:
                accounts.append({"name": self.fake.phone_number(), "type": "org.telegram.messenger", "userdata": {}})
            elif "facebook" in pkg:
                accounts.append({"name": self.fake.uuid4(), "type": "com.facebook.auth.login", "userdata": {"access_token": self.fake.sha1()}})
            elif "twitter" in pkg:
                accounts.append({"name": f"@{username_base}", "type": "com.twitter.android.auth.login", "userdata": {}})

        with SQLiteDB(db_de, self.logger) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS accounts (
                _id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT NOT NULL, 
                type TEXT NOT NULL, 
                password TEXT, 
                previous_name TEXT, 
                last_password_entry_time_millis_epoch INTEGER DEFAULT 0
            )""")
            c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY NOT NULL, value TEXT)")
            c.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", ("android_version", self.profile.get("android_version")))

            for acc in accounts:
                c.execute("INSERT INTO accounts (name, type) VALUES (?, ?)", (acc['name'], acc['type']))
                acc['_id'] = c.lastrowid 

        with SQLiteDB(db_ce, self.logger) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS accounts (
                _id INTEGER PRIMARY KEY, 
                name TEXT NOT NULL, 
                type TEXT NOT NULL, 
                password TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS authtokens (
                _id INTEGER PRIMARY KEY AUTOINCREMENT, 
                accounts_id INTEGER, 
                type TEXT, 
                authtoken TEXT, 
                FOREIGN KEY(accounts_id) REFERENCES accounts(_id)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS extras (
                _id INTEGER PRIMARY KEY AUTOINCREMENT, 
                accounts_id INTEGER, 
                key TEXT, 
                value TEXT, 
                FOREIGN KEY(accounts_id) REFERENCES accounts(_id)
            )""")

            for acc in accounts:
                c.execute("INSERT INTO accounts (_id, name, type) VALUES (?, ?, ?)", (acc['_id'], acc['name'], acc['type']))
                token_type = f"weblogin:{acc['type']}"
                fake_token = self.fake.sha256()
                c.execute("INSERT INTO authtokens (accounts_id, type, authtoken) VALUES (?, ?, ?)", 
                          (acc['_id'], token_type, fake_token))
                for k, v in acc.get("userdata", {}).items():
                    c.execute("INSERT INTO extras (accounts_id, key, value) VALUES (?, ?, ?)", 
                              (acc['_id'], k, v))

    def generate_packages_list(self, installed_apps: Dict[str, str]):
        path = self.fs.get_path("system")
        path.mkdir(parents=True, exist_ok=True)
        lines = []
        sorted_apps = sorted(installed_apps.items(), key=lambda x: x[1])
        for i, (name, pkg) in enumerate(sorted_apps):
            uid = 10000 + i
            line = f"{pkg} {uid} 0 /data/user/0/{pkg} default:targetSdkVersion=33 3003"
            lines.append(line)
        try:
            with open(path / "packages.list", "w") as f:
                f.write("\n".join(lines))
        except OSError: pass

    def generate_anr_artifacts(self):
        path = self.fs.get_path("anr")
        path.mkdir(parents=True, exist_ok=True)
        trace_content = f"""
----- pid 1234 at {datetime.now()} -----
Cmd line: com.google.android.youtube
"main" prio=5 tid=1 Native
  | group="main" sCount=1 dsCount=0 flags=1 obj=0x7368c880 self=0x7b44615c00
  | sysTid=1234 nice=-10 cgrp=default sched=0/0 handle=0x7b4580b4f8
  | state=S schedstat=( 58682969 13548958 128 ) utm=4 stm=1 core=5 HZ=100
  | stack=0x7fe6e69000-0x7fe6e6b000 stackSize=8MB
  | held mutexes=
  native: #00 pc 000000000004a4bc  /system/lib64/libc.so (syscall+28)
  native: #01 pc 00000000000e4708  /system/lib64/libart.so (art::ConditionVariable::Wait(art::Thread*)+140)
  at com.android.server.am.ActivityManagerService.broadcastIntent(ActivityManagerService.java:14560)
"""
        try:
            with open(path / "traces.txt", "w") as f:
                f.write(trace_content.strip())
        except OSError: pass

    def generate_tombstones(self):
        path = self.fs.get_path("tombstones")
        path.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            ts = datetime.now() - timedelta(days=random.randint(0, 5))
            content = f"""*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***
Build fingerprint: '{self.profile.get('manufacturer')}/{self.profile.get('device')}/{self.profile.get('device')}:14/{self.profile.get('build_id')}/10808092:user/release-keys'
Revision: '0'
ABI: 'arm64'
Timestamp: {ts}
pid: {random.randint(1000, 9999)}, tid: {random.randint(1000, 9999)}, name: RenderThread  >>> com.instagram.android <<<
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0
x0  0000000000000000  x1  00000076a43f8000  x2  0000000000000000  x3  0000000000000000
x4  0000000000000000  x5  0000000000000000  x6  0000000000000000  x7  0000000000000000
"""
            try:
                with open(path / f"tombstone_{i:02d}", "w") as f:
                    f.write(content)
            except OSError: pass

    def generate_dalvik_cache(self, installed_apps: Dict[str, str]):
        path = self.fs.get_path("dalvik_cache") / "arm64"
        path.mkdir(parents=True, exist_ok=True)
        dex_magic = b"dex\n035\x00"
        for pkg in installed_apps.values():
            rand_suffix = self.fake.bothify(text="##====")
            fname = f"data@app@@{pkg}-{rand_suffix}==@base.apk@classes.dex"
            try:
                with open(path / fname, "wb") as f:
                    f.write(dex_magic)
                    f.write(os.urandom(1024 * 50)) 
            except OSError: pass

    def generate_app_dir_structure(self, installed_apps: Dict[str, str]):
        app_root = self.fs.get_path("app")
        for pkg in installed_apps.values():
            folder_name = f"{pkg}-{self.fake.bothify(text='????==')}"
            app_dir = app_root / folder_name
            app_dir.mkdir(parents=True, exist_ok=True)
            try:
                with open(app_dir / "base.apk", "wb") as f:
                    f.write(b"PK\x03\x04") 
                    f.write(os.urandom(1024 * 10)) 
                oat_dir = app_dir / "oat" / "arm64"
                oat_dir.mkdir(parents=True, exist_ok=True)
                with open(oat_dir / "base.odex", "wb") as f:
                    f.write(os.urandom(1024))
            except OSError: pass

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
        except OSError as e: self.logger.error(f"Wifi Config Error: {e}")

    def generate_accounts_db(self, owner_email: str, installed_apps: Dict[str, str]):
        """Legacy Account Generation"""
        db_path = self.fs.get_path("system_users") / "accounts.db"
        with SQLiteDB(db_path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS accounts (_id INTEGER PRIMARY KEY, name TEXT, type TEXT)")
            c.execute("INSERT INTO accounts (name, type) VALUES (?, ?)", (owner_email, "com.google"))
            for app_name, pkg in installed_apps.items():
                account_type, account_name = None, None
                if "whatsapp" in pkg: account_type, account_name = "com.whatsapp", self.fake.phone_number()
                elif "telegram" in pkg: account_type, account_name = "org.telegram.messenger", self.fake.phone_number()
                elif "instagram" in pkg: account_type, account_name = "com.instagram", self.fake.user_name()
                if account_type:
                    c.execute("INSERT INTO accounts (name, type) VALUES (?, ?)", (account_name, account_type))

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
                "device": self.profile.get("model", "Generic"),
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
        db_path = path / "app_usage.db"
        with SQLiteDB(db_path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS events (_id INTEGER PRIMARY KEY, timestamp INTEGER, package_name TEXT, type INTEGER)")
            pkgs = list(installed_apps.values())
            if not pkgs: pkgs = ["com.android.chrome"]
            start_ts = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
            for i in range(50):
                ts = start_ts + (i * 1000 * 60 * random.randint(10, 60))
                pkg = random.choice(pkgs)
                c.execute("INSERT INTO events (timestamp, package_name, type) VALUES (?, ?, ?)", (ts, pkg, 1))

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
        path = self.fs.get_path("system") / "notification_log.db"
        with SQLiteDB(path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS log (_id INTEGER PRIMARY KEY, package_name TEXT, post_time INTEGER, title TEXT, text TEXT)")
            for msg in messages[-20:]:
                pkg = "com.whatsapp" if "WhatsApp" in msg.get('Platform', '') else "com.google.android.apps.messaging"
                ts = int(datetime.strptime(msg['Timestamp'], "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
                c.execute("INSERT INTO log (package_name, post_time, title, text) VALUES (?, ?, ?, ?)", (pkg, ts, msg['Sender'], msg['Body']))

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
        path = self.fs.get_path("system") / "locksettings.db"
        with SQLiteDB(path, self.logger) as c:
            c.execute("CREATE TABLE IF NOT EXISTS locksettings (_id INTEGER PRIMARY KEY, name TEXT, user INTEGER, value TEXT)")
            c.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)", ("lockscreen.password_type", 0, "131072"))
            c.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)", ("lockscreen.disabled", 0, "0"))
            c.execute("INSERT INTO locksettings (name, user, value) VALUES (?, ?, ?)", ("lockscreen.password_salt", 0, self.fake.hexify(text="^" * 16)))
        
        try:
            with open(path.parent / "gatekeeper.password.key", "wb") as f: f.write(os.urandom(64))
        except OSError: pass

    def generate_build_prop(self):
        path = self.fs.get_path("root") / "system"
        path.mkdir(parents=True, exist_ok=True)
        content = f"""
# build properties
ro.build.id={self.profile.get('build_id', 'UNKNOWN')}
ro.build.display.id={self.profile.get('build_id', 'UNKNOWN')}
ro.build.version.incremental={random.randint(1000000, 9999999)}
ro.build.version.sdk={self.profile.get('android_version', '10')}
ro.build.version.release={self.profile.get('android_version', '10')}
ro.product.brand={self.profile.get('manufacturer', 'Generic')}
ro.product.model={self.profile.get('model', 'Generic Phone')}
ro.product.board={self.profile.get('board', 'generic_board')}
ro.product.device={self.profile.get('device', 'generic_device')}
ro.product.manufacturer={self.profile.get('manufacturer', 'Generic')}
ro.board.platform={self.profile.get('board', 'platform')}
"""
        try:
            with open(path / "build.prop", "w") as f: f.write(content.strip())
        except OSError as e: self.logger.error(f"Build Prop Error: {e}")

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

    def generate_pixel_private_space(self):
        private_root = self.fs.get_path("user_11") # /data/user/11
        private_files = private_root / "files"
        users_system_path = self.fs.get_path("system_users_base")
        
        private_files.mkdir(parents=True, exist_ok=True)
        users_system_path.mkdir(parents=True, exist_ok=True)

        root = ET.Element("user", id="11", serialNumber="11", flags="32", created=str(int(datetime.now().timestamp()*1000)))
        ET.SubElement(root, "name").text = "Private Space"
        ET.SubElement(root, "profileGroupId").text = "0"
        ET.SubElement(root, "userType").text = "android.os.usertype.profile.PRIVATE" 
        
        try:
            with open(users_system_path / "11.xml", "w") as f:
                f.write(self._prettify_xml(root))
        except OSError: pass

        try:
            private_dl = private_root / "com.android.chrome" / "files" / "Download"
            private_dl.mkdir(parents=True, exist_ok=True)
            with open(private_dl / "flight_tickets_secret.pdf", "w") as f:
                f.write("This file exists only in the Private Space partition.")
        except OSError: pass