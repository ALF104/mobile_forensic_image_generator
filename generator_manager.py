import random
import csv 
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional

from core.file_system import AndroidFileSystem
from utils.logging_utils import setup_logger
from utils.crypto_utils import calculate_md5
from utils.binary_utils import create_obfuscated_file, create_trash_artifact 

from engines.communication import CommunicationEngine
from engines.system import SystemEngine
from engines.media import MediaEngine
from engines.geo import GeoEngine
from engines.browser import BrowserEngine
from engines.personal_data import PersonalDataEngine

class GeneratorManager:
    def __init__(self, config: Dict, scenarios: Dict, base_path: Path):
        self.config = config
        self.scenarios = scenarios
        self.base_path = base_path
        self.is_cancelled = False 
        
        root_name = config.get("root_dir_name", "Android_Extraction")
        self.fs = AndroidFileSystem(base_path, root_name)
        
        log_path = base_path / "generation.log"
        self.logger = setup_logger("Generator", log_path)
        
        self.comm_engine = CommunicationEngine(self.fs, self.logger)
        self.sys_engine = SystemEngine(self.fs, self.logger)
        self.media_engine = MediaEngine(self.fs, self.logger)
        self.geo_engine = GeoEngine(self.fs, self.logger)
        self.browser_engine = BrowserEngine(self.fs, self.logger)
        self.personal_engine = PersonalDataEngine(self.fs, self.logger)

    def stop(self):
        self.is_cancelled = True

    def run(self, params: Dict, callback_progress: Optional[Callable[[int], None]] = None, callback_log: Optional[Callable[[str], None]] = None):
        def log(msg):
            self.logger.info(msg)
            if callback_log: callback_log(msg)
        def progress(val):
            if callback_progress: callback_progress(val)

        try:
            self.is_cancelled = False
            log(f"Starting generation for {params['owner_name']}...")
            log(f"Profile Selected: {params.get('scenario', 'General Use')}")
            progress(5)
            
            self.fs.create_structure()
            if self.is_cancelled: return

            installed_names = list(params['installed_apps'].keys())

            log("Generating System Artifacts...")
            self.sys_engine.generate_wifi_config()
            email = f"{params['owner_name'].replace(' ', '.').lower()}@gmail.com"
            
            self.sys_engine.generate_accounts_db(email, params['installed_apps'])
            self.sys_engine.generate_packages_xml(params['installed_apps'], params['start_date'].timestamp())
            self.sys_engine.generate_protobuf_artifacts()
            self.sys_engine.generate_runtime_permissions(params['installed_apps'])
            self.sys_engine.generate_shared_preferences(params['installed_apps'])
            self.sys_engine.generate_recent_snapshots(params['installed_apps'])
            self.sys_engine.generate_clipboard_history()
            
            # Enterprise System Artifacts
            self.sys_engine.generate_battery_stats()
            self.sys_engine.generate_system_dropbox()
            self.sys_engine.generate_vpn_logs()
            self.sys_engine.generate_multi_user_artifacts()
            self.sys_engine.generate_vault_app()
            self.sys_engine.generate_lock_settings()
            self.sys_engine.generate_build_prop()
            self.sys_engine.generate_secure_settings()
            
            # Deep OS Artifacts
            self.sys_engine.generate_app_ops(params['installed_apps'])
            self.sys_engine.generate_sync_history(email)
            self.sys_engine.generate_recovery_logs()
            self.sys_engine.generate_user_profile(params['start_date'])
            self.sys_engine.generate_setup_wizard_data(params['start_date'])
            
            # NEW: SECURE SPACES
            self.sys_engine.generate_samsung_secure_folder()
            self.sys_engine.generate_pixel_private_space()
            
            progress(15)
            
            log("Building Social Graph...")
            graph = self.comm_engine.generate_social_graph(
                params['owner_name'], self.scenarios, params.get('network_size', 20), installed_names
            )
            
            scenario_name = params.get('scenario', 'General Use')
            allowed_topics = self.scenarios.get("profiles", {}).get(scenario_name, ["default"])
            for p_name in graph:
                graph[p_name]['Topics'] = [t for t in graph[p_name]['Topics'] if t in allowed_topics]
                if not graph[p_name]['Topics']: graph[p_name]['Topics'] = ["default"]

            progress(25)
            
            log("Simulating User Activity...")
            current_time = params['start_date']
            end_time = params['end_date']
            total_msgs = params['num_messages']
            
            all_messages = []
            all_calls = []
            geo_points = []
            browser_history = []
            reaction_queue = []
            
            msg_count = 0
            avg_gap_sec = (end_time - current_time).total_seconds() / max(total_msgs, 1)
            participants = list(graph.keys())
            
            while msg_count < total_msgs and current_time < end_time:
                if self.is_cancelled: return

                jump = random.randint(int(avg_gap_sec * 0.2), int(avg_gap_sec * 1.5))
                current_time += timedelta(seconds=jump)
                if current_time > end_time: break

                lat_lon = self.geo_engine.get_location_for_time(current_time)
                geo_points.append({
                    "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "latitude": lat_lon[0], "longitude": lat_lon[1]
                })

                if reaction_queue:
                    react_item = reaction_queue.pop(0)
                    react_time = current_time + timedelta(minutes=2) 
                    all_messages.append({
                        "Platform": "Messages (SMS)",
                        "Sender": params['owner_name'], "Recipient": react_item['partner'],
                        "SenderNum": "Self", "RecipientNum": react_item['number'],
                        "Direction": "Outgoing", "Body": "Sorry, can't talk right now.",
                        "Timestamp": react_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "Attachment": None
                    })
                    msg_count += 1

                partner_name = random.choice(participants)
                p_data = graph[partner_name]
                
                platform = random.choice(p_data['Platforms'])
                
                if platform == "Phone" and random.random() < 0.3:
                    direction = random.choice(["Incoming", "Outgoing"])
                    status = "Connected"
                    if direction == "Incoming" and random.random() < 0.4:
                        status = "Missed"
                        reaction_queue.append({"partner": partner_name, "number": p_data['PhoneNumber']})
                    
                    all_calls.append({
                        "Caller": partner_name if direction=="Incoming" else params['owner_name'],
                        "CallerNum": p_data['PhoneNumber'] if direction=="Incoming" else "Self",
                        "Direction": direction, "Status": status,
                        "Duration": random.randint(10, 600) if status=="Connected" else 0,
                        "Timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                else:
                    topic_key = random.choice(p_data['Topics'])
                    convo_lines = self.scenarios['conversations'].get(topic_key, self.scenarios['conversations']['default'])
                    
                    for line in convo_lines:
                        if msg_count >= total_msgs: break
                        is_owner = (line['role'] == "Owner")
                        sender = params['owner_name'] if is_owner else partner_name
                        recipient = partner_name if is_owner else params['owner_name']
                        direction = "Outgoing" if is_owner else "Incoming"
                        s_num = "Self" if is_owner else p_data.get('PhoneNumber')
                        r_num = p_data.get('PhoneNumber') if is_owner else "Self"

                        attachment_path = None
                        content = line['content']
                        
                        if "{time}" in content:
                            future_time = current_time + timedelta(hours=2)
                            content = content.replace("{time}", future_time.strftime("%I:%M %p"))

                        if "." in content and len(content) < 40:
                            ext = content.split(".")[-1].lower()
                            if ext in ['jpg', 'png', 'jpeg']:
                                self.media_engine.generate_image_file(content, current_time, lat_lon)
                                attachment_path = f"/sdcard/DCIM/{content}"
                            elif ext in ['pdf', 'docx']:
                                browser_history.append({
                                    "URL": f"https://docs.google.com/viewer?file={content}",
                                    "Title": f"View - {content}",
                                    "Timestamp": (current_time - timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
                                })

                        final_text = self.comm_engine.humanizer.humanize(content, intensity=1)
                        all_messages.append({
                            "Platform": platform,
                            "Sender": sender, "Recipient": recipient,
                            "SenderNum": s_num, "RecipientNum": r_num,
                            "Direction": direction, "Body": final_text,
                            "Timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "Attachment": attachment_path
                        })
                        current_time += timedelta(seconds=random.randint(20, 120))
                        msg_count += 1
                
                if random.random() < 0.15:
                    urls = self.config.get("common_urls", [])
                    if urls:
                        site = random.choice(urls)
                        browser_history.append({
                            "URL": site['url'], "Title": site['title'],
                            "Timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S")
                        })

                if random.random() < 0.03:
                    dl_path = self.fs.get_path("downloads")
                    create_obfuscated_file(dl_path, f"invoice_{random.randint(1000,9999)}.jpg", "pdf")
                    
                progress_val = 25 + int((msg_count / total_msgs) * 60)
                progress(min(progress_val, 85))

            log("Writing Database Artifacts...")
            self.comm_engine.create_sms_db(all_messages)
            self.comm_engine.create_whatsapp_db(all_messages)
            self.comm_engine.generate_call_log(all_calls)
            self.comm_engine.generate_sim_info()
            self.comm_engine.generate_cell_tower_db(geo_points)
            
            self.browser_engine.generate_chrome_history(browser_history)
            self.browser_engine.generate_cookies(browser_history)
            self.browser_engine.generate_web_data(params['owner_name'])
            
            self.media_engine.build_media_store_db()
            self.media_engine.generate_financial_receipts(params['installed_apps'])
            self.media_engine.generate_download_manager_db()
            self.media_engine.generate_thumbnail_cache()
            self.media_engine.generate_office_docs()
            
            self.geo_engine.generate_track_file(geo_points)
            
            log("Generating Pattern of Life...")
            self.personal_engine.generate_calendar_db()
            self.personal_engine.generate_notes_db()
            self.personal_engine.generate_health_data()
            self.personal_engine.generate_keyboard_cache()
            self.personal_engine.generate_voice_memos()
            self.comm_engine.generate_emails(email)
            
            log("Generating Deep System Logs...")
            self.sys_engine.generate_cloud_takeout(email)
            self.sys_engine.generate_bluetooth_config()
            self.sys_engine.generate_digital_wellbeing(params['installed_apps'])
            self.sys_engine.generate_wifi_scan_logs(geo_points)
            self.sys_engine.generate_notification_history(all_messages)
            
            self.sys_engine.generate_json_artifacts(params['installed_apps'])
            
            progress(90)
            log("Generating Hash Manifest (MD5)...")
            manifest_path = self.fs.root / "hash_manifest.csv"
            with open(manifest_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['FilePath', 'MD5'])
                for path in self.fs.root.rglob('*'):
                    if path.is_file() and path.name != "hash_manifest.csv":
                        md5_val = calculate_md5(path)
                        rel_path = path.relative_to(self.fs.root)
                        writer.writerow([str(rel_path), md5_val])
            
            progress(95)
            if self.is_cancelled: return

            log("Compressing Forensic Image (.zip and .tar)...")
            zip_name = f"Forensic_Image_{params['owner_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
            self.fs.zip_extraction(zip_name)
            self.fs.tar_extraction(zip_name)
            
            progress(100)
            log("Generation Complete successfully.")
            
        except Exception as e:
            self.logger.error("Critical Failure in Generator Manager", exc_info=True)
            if callback_log: callback_log(f"ERROR: {str(e)}")
            raise e