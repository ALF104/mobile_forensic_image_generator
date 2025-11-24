import sys
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QSpinBox, QPushButton, 
                               QTextEdit, QProgressBar, QGroupBox, QLineEdit, 
                               QTreeWidget, QTreeWidgetItem, 
                               QDateTimeEdit, QComboBox, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QFont

from core.generator_manager import GeneratorManager
from gui.analyzer_tool import ForensicParserWindow

# --- MODERN "CYBER-FORENSIC" THEME ---
CYBER_STYLE = """
/* Global Window Settings */
QMainWindow {
    background-color: #121212; /* Deep background */
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QWidget {
    font-size: 14px;
    color: #cccccc;
}

/* Group Box Styling */
QGroupBox {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 8px;
    margin-top: 22px; /* Leave space for title */
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 5px 10px;
    background-color: #1e1e1e;
    color: #00e5ff; /* Neon Cyan */
    border: 1px solid #333333;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: bold;
}

/* Input Fields */
QLineEdit, QSpinBox, QDateTimeEdit, QComboBox {
    background-color: #2c2c2c;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
    selection-background-color: #00acc1;
}

QLineEdit:focus, QSpinBox:focus, QDateTimeEdit:focus, QComboBox:focus {
    border: 1px solid #00e5ff; /* Cyan focus border */
    background-color: #333333;
}

/* Dropdown Specifics */
QComboBox {
    padding-right: 20px; /* Make room for arrow */
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 1px;
    border-left-color: #444;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background: #252525;
}
QComboBox QAbstractItemView {
    background-color: #2c2c2c;
    color: white;
    selection-background-color: #00acc1;
    border: 1px solid #444;
    outline: none;
}

/* Tree Widget (App Selector) */
QTreeWidget {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 6px;
    outline: none;
}
QTreeWidget::item {
    padding: 5px;
}
QTreeWidget::item:hover {
    background-color: #2a2a2a;
}
QTreeWidget::item:selected {
    background-color: #37474f;
    color: #00e5ff;
}

/* Buttons */
QPushButton {
    background-color: #263238; /* Dark Blue Grey */
    color: #eceff1;
    border: 1px solid #37474f;
    padding: 10px 20px;
    border-radius: 5px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QPushButton:hover {
    background-color: #37474f;
    border: 1px solid #00e5ff;
    color: #00e5ff;
}
QPushButton:pressed {
    background-color: #00e5ff;
    color: #121212;
}
QPushButton:disabled {
    background-color: #1a1a1a;
    color: #555;
    border: 1px solid #333;
}

/* Specific Button Colors */
QPushButton#generate_btn {
    background-color: #00695c; /* Teal */
    border-color: #004d40;
}
QPushButton#generate_btn:hover {
    background-color: #00897b;
    border-color: #00bfa5;
    color: white;
}

QPushButton#cancel_btn {
    background-color: #b71c1c; /* Red */
    border-color: #7f0000;
}
QPushButton#cancel_btn:hover {
    background-color: #d32f2f;
    color: white;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #444;
    border-radius: 5px;
    text-align: center;
    background-color: #1e1e1e;
    color: white;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00acc1, stop:1 #26c6da);
    border-radius: 3px;
}

/* Logs */
QTextEdit {
    background-color: #000000;
    color: #00ff00; /* Matrix Green console text */
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    border: 1px solid #333;
    border-radius: 4px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #1e1e1e;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #555;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

class GeneratorWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, params, config, scenarios):
        super().__init__()
        self.params = params
        self.config = config
        self.scenarios = scenarios
        self.manager = None 

    def stop(self):
        if self.manager:
            self.manager.stop()

    def run(self):
        try:
            base_path = Path.cwd()
            self.manager = GeneratorManager(self.config, self.scenarios, base_path)
            self.manager.run(
                self.params, 
                callback_progress=self.progress.emit, 
                callback_log=self.log.emit
            )
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALF Forensics - Generator V3.4 (Cyber UI)")
        self.resize(1200, 900)
        self.setStyleSheet(CYBER_STYLE)
        
        self.device_profiles = {}
        self.load_config()
        self.setup_ui()
        self.worker = None

    def load_config(self):
        try:
            base = Path(__file__).parent.parent / "config"
            with open(base / "settings.json", "r") as f: self.settings = json.load(f)
            with open(base / "scenarios.json", "r") as f: self.scenarios = json.load(f)
            
            profile_path = base / "device_profiles.json"
            if profile_path.exists():
                with open(profile_path, "r") as f: self.device_profiles = json.load(f)
            else:
                self.device_profiles = {"pixel_8": {"model": "Pixel 8 (Fallback)"}}

        except Exception as e:
            QMessageBox.critical(self, "Config Error", f"Could not load config files: {e}")
            sys.exit(1)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)

        # --- Header ---
        header_layout = QHBoxLayout()
        
        title_container = QVBoxLayout()
        title = QLabel("ANDROID ARTIFACT GENERATOR")
        title.setStyleSheet("font-size: 24px; font-weight: 900; color: #00e5ff; letter-spacing: 2px;")
        subtitle = QLabel("Forensic Dataset Simulation Engine v3.4")
        subtitle.setStyleSheet("font-size: 14px; color: #78909c; font-style: italic;")
        title_container.addWidget(title)
        title_container.addWidget(subtitle)
        
        header_layout.addLayout(title_container)
        header_layout.addStretch()
        
        btn_analyzer = QPushButton("LAUNCH ANALYZER")
        btn_analyzer.setCursor(Qt.PointingHandCursor)
        btn_analyzer.setMinimumHeight(40)
        btn_analyzer.clicked.connect(self.launch_analyzer)
        header_layout.addWidget(btn_analyzer)
        
        layout.addLayout(header_layout)

        # --- Top Section: Identity & Device ---
        gb_id = QGroupBox("TARGET IDENTITY & DEVICE PROFILE")
        l_id = QHBoxLayout()
        l_id.setSpacing(15)
        
        self.inp_fname = QLineEdit(self.settings.get("default_first_name", "John"))
        self.inp_sname = QLineEdit(self.settings.get("default_surname", "Doe"))
        
        self.combo_device = QComboBox()
        self.combo_device.addItems(list(self.device_profiles.keys()))
        self.combo_device.setCursor(Qt.PointingHandCursor)
        
        self.inp_net_size = QSpinBox(); self.inp_net_size.setRange(5, 100); self.inp_net_size.setValue(20)
        
        # Helper to create labeled inputs
        def add_field(label_text, widget):
            v = QVBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold; color: #b0bec5; font-size: 12px;")
            v.addWidget(lbl)
            v.addWidget(widget)
            l_id.addLayout(v)

        add_field("FIRST NAME", self.inp_fname)
        add_field("SURNAME", self.inp_sname)
        add_field("DEVICE MODEL", self.combo_device)
        add_field("NETWORK SIZE", self.inp_net_size)
        
        gb_id.setLayout(l_id)
        layout.addWidget(gb_id)

        # --- Middle Section: Apps & Params ---
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(20)
        
        # Apps Tree
        gb_apps = QGroupBox("INSTALLED APPLICATIONS")
        l_apps = QVBoxLayout()
        self.tree_apps = QTreeWidget()
        self.tree_apps.setHeaderHidden(True)
        self.tree_apps.setAlternatingRowColors(False)
        
        catalog = self.settings.get("app_catalog", {})
        
        for category, apps in catalog.items():
            cat_item = QTreeWidgetItem(self.tree_apps)
            cat_item.setText(0, category)
            cat_item.setFlags(cat_item.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
            cat_item.setExpanded(True)
            # Style category items slightly different if possible, or rely on tree indent
            
            for app_name, pkg_name in apps.items():
                app_item = QTreeWidgetItem(cat_item)
                app_item.setText(0, app_name)
                app_item.setData(0, Qt.UserRole, pkg_name) 
                app_item.setFlags(app_item.flags() | Qt.ItemIsUserCheckable)
                
                if app_name in ["WhatsApp", "Instagram", "Chrome"]:
                    app_item.setCheckState(0, Qt.Checked)
                else:
                    app_item.setCheckState(0, Qt.Unchecked)
                    
        l_apps.addWidget(self.tree_apps)
        gb_apps.setLayout(l_apps)
        mid_layout.addWidget(gb_apps, 2) # Give more width to apps

        # Params
        gb_time = QGroupBox("SIMULATION PARAMETERS")
        l_time = QVBoxLayout()
        l_time.setSpacing(15)
        
        self.combo_scenario = QComboBox()
        profiles = list(self.scenarios.get("profiles", {}).keys())
        if not profiles: profiles = ["General Use"]
        self.combo_scenario.addItems(profiles)
        
        # Dates
        import time
        start_ts = time.time() - (30 * 24 * 3600)
        self.date_start = QDateTimeEdit(datetime.fromtimestamp(start_ts))
        self.date_start.setCalendarPopup(True)
        self.date_end = QDateTimeEdit(datetime.now())
        self.date_end.setCalendarPopup(True)
        
        self.combo_activity = QComboBox()
        self.combo_activity.addItems(["Low (Burst Mode)", "Medium (Burst Mode)", "High (Burst Mode)"])
        self.combo_activity.setCurrentIndex(1)
        
        # Use the helper again for consistent styling
        def add_v_field(label_text, widget):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold; color: #b0bec5; font-size: 12px;")
            l_time.addWidget(lbl)
            l_time.addWidget(widget)

        add_v_field("SCENARIO PROFILE", self.combo_scenario)
        add_v_field("START DATE", self.date_start)
        add_v_field("END DATE", self.date_end)
        add_v_field("ACTIVITY LEVEL", self.combo_activity)
        
        l_time.addStretch()
        
        # Info Label
        info_lbl = QLabel("ℹ Note: Native apps (Phone, SMS, Play Store) are installed automatically.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #546e7a; font-size: 12px;")
        l_time.addWidget(info_lbl)

        gb_time.setLayout(l_time)
        mid_layout.addWidget(gb_time, 1)
        
        layout.addLayout(mid_layout)

        # --- Footer ---
        btn_layout = QHBoxLayout()
        self.btn_generate = QPushButton("INITIALIZE GENERATION SEQUENCE")
        self.btn_generate.setObjectName("generate_btn") # For CSS targeting
        self.btn_generate.setMinimumHeight(55)
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.clicked.connect(self.start_generation)
        btn_layout.addWidget(self.btn_generate, 3)
        
        self.btn_cancel = QPushButton("ABORT")
        self.btn_cancel.setObjectName("cancel_btn")
        self.btn_cancel.setMinimumHeight(55)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.cancel_generation)
        self.btn_cancel.setEnabled(False)
        btn_layout.addWidget(self.btn_cancel, 1)
        layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setTextVisible(False) 
        layout.addWidget(self.progress_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        layout.addWidget(self.log_view)

    def get_selected_apps_map(self):
        selected = {}
        # 1. Add Standard Natives (Hardcoded)
        for nat in self.settings.get("native_apps", []):
            pkg = f"com.android.{nat.lower().replace(' ', '')}"
            if "chrome" in nat.lower(): pkg = "com.android.chrome"
            if "pixel" in nat.lower(): pkg = "com.google.android.apps.nexuslauncher"
            if "play store" in nat.lower(): pkg = "com.android.vending"
            if "play services" in nat.lower(): pkg = "com.google.android.gms"
            if "gmail" in nat.lower(): pkg = "com.google.android.gm"
            if "maps" in nat.lower(): pkg = "com.google.android.apps.maps"
            if "photos" in nat.lower(): pkg = "com.google.android.apps.photos"
            if "youtube" in nat.lower(): pkg = "com.google.android.youtube"
            selected[nat] = pkg

        # 2. Add OEM Specific Apps
        current_device_key = self.combo_device.currentText()
        if current_device_key in self.device_profiles:
            manufacturer = self.device_profiles[current_device_key].get("manufacturer")
            oem_catalog = self.settings.get("oem_apps", {})
            if manufacturer in oem_catalog:
                self.log_view.append(f"Detected {manufacturer} device. Injecting OEM apps...")
                for app_name, pkg in oem_catalog[manufacturer].items():
                    selected[app_name] = pkg

        # 3. Add User Selected Apps from Tree
        root = self.tree_apps.invisibleRootItem()
        for i in range(root.childCount()):
            category = root.child(i)
            for j in range(category.childCount()):
                app_item = category.child(j)
                if app_item.checkState(0) == Qt.Checked:
                    name = app_item.text(0)
                    pkg = app_item.data(0, Qt.UserRole)
                    selected[name] = pkg
        return selected

    def start_generation(self):
        self.log_view.clear()
        self.btn_generate.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.log_view.append(">>> SYSTEM INITIALIZED. STARTING SEQUENCE...")
        
        rates = [200, 500, 1000] 
        msgs_target = rates[self.combo_activity.currentIndex()]

        apps_map = self.get_selected_apps_map()

        params = {
            "owner_name": f"{self.inp_fname.text()} {self.inp_sname.text()}",
            "start_date": self.date_start.dateTime().toPython(),
            "end_date": self.date_end.dateTime().toPython(),
            "installed_apps": apps_map,
            "network_size": self.inp_net_size.value(),
            "num_messages": msgs_target,
            "scenario": self.combo_scenario.currentText()
        }

        selected_device = self.combo_device.currentText()
        run_config = self.settings.copy()
        
        if selected_device in self.device_profiles:
            run_config["device_profiles"] = {selected_device: self.device_profiles[selected_device]}

        self.worker = GeneratorWorker(params, run_config, self.scenarios)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_view.append)
        self.worker.finished.connect(self.generation_finished)
        self.worker.error.connect(self.generation_error)
        self.worker.start()

    def cancel_generation(self):
        if self.worker:
            self.log_view.append("!!! INTERRUPT SIGNAL RECEIVED. STOPPING...")
            self.worker.stop()
            self.btn_cancel.setEnabled(False)

    def generation_finished(self):
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self.log_view.append(">>> SEQUENCE COMPLETE. DATA ARTIFACTS READY.")
        QMessageBox.information(self, "Status", "Generation Complete!")

    def generation_error(self, err_msg):
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.log_view.append(f"CRITICAL ERROR: {err_msg}")
        QMessageBox.critical(self, "Error", f"Generation Failed:\n{err_msg}")

    def launch_analyzer(self):
        self.analyzer = ForensicParserWindow()
        self.analyzer.show()