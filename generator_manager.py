import random
import csv 
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional, List

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
        
        # Select a random device profile (Improvement #4)
        profile_key = random.choice(list(config.get("device_profiles", {}).keys())) if config.get("device_profiles") else "pixel_8"
        # Since device_profiles.json is separate, we assume it's loaded into config or we load default
        # Ideally, main_window passes the loaded JSON. For now, we mock a default if missing.
        device_profile = config.get("device_profiles", {}).get(profile_key)

        self.comm_engine = CommunicationEngine(self.fs, self.logger)
        self.sys_engine = SystemEngine(self.fs, self.logger, device_profile)
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
            log(f"Scenario: {params.get('scenario', 'General Use')}")
            progress(5)
            
            self.fs.create_structure()
            if self.is_cancelled: return

            installed_names = list(params['installed_apps'].keys())

            # --- SYSTEM ARTIFACTS ---
            log("Generating System Artifacts...")
            self.sys_engine.generate_wifi_config()
            email = f"{params['owner_name'].replace(' ', '.').lower()}@gmail.com"
            
            # MODERN ACCOUNTS & LISTS
            self.sys_engine.generate_modern_accounts_db(email, params['installed_apps'])
            self.sys_engine.generate_packages_list(params['installed_apps'])
            
            # GOOGLE SUITE ARTIFACTS (NEW)
            self.sys_engine.generate_play_store_data(email, params['installed_apps'])
            
            # Legacy Support (optional, kept for completeness)
            self.sys_engine.generate_accounts_db(email, params['installed_apps'])
            
            self.sys_engine.generate_packages_xml(params['installed_apps'], params['start_date'].timestamp())
            self.sys_engine.generate_protobuf_artifacts()
            self.sys_engine.generate_runtime_permissions(params['installed_apps'])
            self.sys_engine.generate_shared_preferences(params['installed_apps'])
            self.sys_engine.generate_recent_snapshots(params['installed_apps'])
            self.sys_engine.generate_clipboard_history()
            
            # --- NEW: DEEP REALISM ARTIFACTS ---
            self.sys_engine.generate_anr_artifacts()        
            self.sys_engine.generate_tombstones()           
            self.sys_engine.generate_dalvik_cache(params['installed_apps']) 
            self.sys_engine.generate_app_dir_structure(params['installed_apps']) 
            
            # Enterprise/Deep Artifacts
            self.sys_engine.generate_battery_stats()
            self.sys_engine.generate_system_dropbox()
            self.sys_engine.generate_vpn_logs()
            self.sys_engine.generate_multi_user_artifacts()
            self.sys_engine.generate_vault_app()
            self.sys_engine.generate_lock_settings()
            self.sys_engine.generate_build_prop()
            self.sys_engine.generate_secure_settings()
            self.sys_engine.generate_app_ops(params['installed_apps'])
            self.sys_engine.generate_sync_history(email)
            self.sys_engine.generate_recovery_logs()
            self.sys_engine.generate_user_profile(params['start_date'])
            self.sys_engine.generate_setup_wizard_data(params['start_date'])
            self.sys_engine.generate_samsung_secure_folder()
            self.sys_engine.generate_pixel_private_space()
            
            progress(15)
            
            # --- SOCIAL GRAPH ---
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
            
            # --- BURST LOGIC (Improvement #3) ---
            log("Simulating User Activity (Burst Mode)...")
            current_time = params['start_date']
            end_time = params['end_date']
            total_msgs = params['num_messages']
            
            all_messages = []
            all_calls = []
            geo_points = []
            browser_history = []
            
            msg_count = 0
            participants = list(graph.keys())
            
            # Queue for burst messages: (timestamp, data_dict)
            burst_queue: List[tuple] = []

            while current_time < end_time:
                if self.is_cancelled: return

                # 1. Check if we need to schedule a new conversation
                if not burst_queue:
                    # Long gap between conversations (30 mins to 3 hours)
                    gap_seconds = random.randint(1800, 10800)
                    current_time += timedelta(seconds=gap_seconds)
                    
                    if current_time >= end_time: break
                    
                    # Select Partner & Topic
                    partner_name = random.choice(participants)
                    p_data = graph[partner_name]
                    platform = random.choice(p_data['Platforms'])
                    topic_key = random.choice(p_data['Topics'])
                    
                    # Generate Conversation Lines
                    convo_lines = self.scenarios['conversations'].get(topic_key, self.scenarios['conversations']['default'])
                    
                    burst_clock = current_time
                    
                    # Handle Calls
                    if platform == "Phone":
                        # Single event, maybe missed
                        direction = random.choice(["Incoming", "Outgoing"])
                        status = "Connected"
                        duration = random.randint(10, 600)
                        
                        if direction == "Incoming" and random.random() < 0.4:
                            status = "Missed"
                            duration = 0
                            # If missed, maybe schedule a text back later
                            burst_queue.append((burst_clock + timedelta(minutes=5), {
                                "type": "msg",
                                "Platform": "Messages (SMS)",
                                "Sender": params['owner_name'], "Recipient": partner_name,
                                "SenderNum": "Self", "RecipientNum": p_data['PhoneNumber'],
                                "Direction": "Outgoing", "Body": "Sorry I missed you.",
                                "Attachment": None
                            }))
                        
                        all_calls.append({
                            "Caller": partner_name if direction=="Incoming" else params['owner_name'],
                            "CallerNum": p_data['PhoneNumber'] if direction=="Incoming" else "Self",
                            "Direction": direction, "Status": status,
                            "Duration": duration,
                            "Timestamp": burst_clock.strftime("%Y-%m-%d %H:%M:%S")
                        })
                    
                    else:
                        # Message Flow
                        for line in convo_lines:
                            # Short delay between texts (10s - 90s)
                            burst_clock += timedelta(seconds=random.randint(10, 90))
                            
                            is_owner = (line['role'] == "Owner")
                            sender = params['owner_name'] if is_owner else partner_name
                            recipient = partner_name if is_owner else params['owner_name']
                            direction = "Outgoing" if is_owner else "Incoming"
                            s_num = "Self" if is_owner else p_data.get('PhoneNumber')
                            r_num = p_data.get('PhoneNumber') if is_owner else "Self"
                            
                            content = line['content']
                            # Text Replacement
                            if "{time}" in content:
                                content = content.replace("{time}", (burst_clock + timedelta(hours=2)).strftime("%I:%M %p"))

                            attachment = None
                            # Handle Attachments
                            if "." in content and len(content) < 40:
                                ext = content.split(".")[-1].lower()
                                if ext in ['jpg', 'png', 'jpeg']:
                                    # We generate the file NOW with the burst timestamp
                                    lat_lon = self.geo_engine.get_location_for_time(burst_clock)
                                    self.media_engine.generate_image_file(content, burst_clock, lat_lon)
                                    attachment = f"/sdcard/DCIM/{content}"
                                elif ext in ['pdf', 'docx']:
                                    browser_history.append({
                                        "URL": f"https://docs.google.com/viewer?file={content}",
                                        "Title": f"View - {content}",
                                        "Timestamp": (burst_clock - timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
                                    })
                            
                            # Humanize
                            final_text = self.comm_engine.humanizer.humanize(content, intensity=1)
                            
                            burst_queue.append((burst_clock, {
                                "type": "msg",
                                "Platform": platform,
                                "Sender": sender, "Recipient": recipient,
                                "SenderNum": s_num, "RecipientNum": r_num,
                                "Direction": direction, "Body": final_text,
                                "Attachment": attachment
                            }))

                # 2. Process Queue
                if burst_queue:
                    # Pop first item
                    ts, data = burst_queue.pop(0)
                    
                    # Generate Location for this timestamp
                    lat_lon = self.geo_engine.get_location_for_time(ts)
                    geo_points.append({
                        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "latitude": lat_lon[0], "longitude": lat_lon[1]
                    })
                    
                    if data["type"] == "msg":
                        all_messages.append({
                            "Platform": data['Platform'],
                            "Sender": data['Sender'], "Recipient": data['Recipient'],
                            "SenderNum": data['SenderNum'], "RecipientNum": data['RecipientNum'],
                            "Direction": data['Direction'], "Body": data['Body'],
                            "Timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                            "Attachment": data['Attachment']
                        })
                        msg_count += 1

                    # Chance for random browser activity or receipt during day
                    if random.random() < 0.05:
                        self.media_engine.generate_financial_receipts(params['installed_apps'], ts)
                    
                    if random.random() < 0.05:
                        urls = self.config.get("common_urls", [])
                        if urls:
                            site = random.choice(urls)
                            browser_history.append({
                                "URL": site['url'], "Title": site['title'],
                                "Timestamp": ts.strftime("%Y-%m-%d %H:%M:%S")
                            })

                progress_val = 25 + int((msg_count / max(total_msgs, 1)) * 60)
                progress(min(progress_val, 85))
                
                # If we've hit the message limit, break
                if msg_count >= total_msgs: break

            # --- WRITING DATABASES ---
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