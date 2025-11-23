import sys
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QSpinBox, QPushButton, 
                               QTextEdit, QProgressBar, QGroupBox, QLineEdit, 
                               QCheckBox, QTreeWidget, QTreeWidgetItem, 
                               QDateTimeEdit, QComboBox, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal

from core.generator_manager import GeneratorManager
from gui.analyzer_tool import ForensicParserWindow

MODERN_STYLE = """
QMainWindow { background-color: #2b2b2b; color: #ffffff; }
QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
QGroupBox { 
    border: 1px solid #555; border-radius: 5px; margin-top: 10px; font-weight: bold; color: #00acc1; 
}
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
QLineEdit, QSpinBox, QDateTimeEdit, QComboBox { 
    background-color: #3a3a3a; border: 1px solid #555; padding: 5px; border-radius: 3px; color: white; 
}
QTreeWidget { background-color: #3a3a3a; border: 1px solid #555; border-radius: 3px; }
QPushButton { 
    background-color: #007acc; color: white; border: none; padding: 8px 15px; border-radius: 4px; font-weight: bold; 
}
QPushButton:hover { background-color: #0098ff; }
QPushButton:pressed { background-color: #005c99; }
QProgressBar { 
    border: 1px solid #555; border-radius: 4px; text-align: center; background-color: #3a3a3a; 
}
QProgressBar::chunk { background-color: #00acc1; width: 10px; margin: 0.5px; }
QTextEdit { background-color: #1e1e1e; border: 1px solid #444; font-family: Consolas, monospace; font-size: 12px; }
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
        self.setWindowTitle("ALF Forensics - Generator V3.1")
        self.resize(1100, 850)
        self.setStyleSheet(MODERN_STYLE)
        
        self.load_config()
        self.setup_ui()
        self.worker = None

    def load_config(self):
        try:
            base = Path(__file__).parent.parent / "config"
            with open(base / "settings.json", "r") as f: self.settings = json.load(f)
            with open(base / "scenarios.json", "r") as f: self.scenarios = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Config Error", f"Could not load config files: {e}")
            sys.exit(1)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("ANDROID ARTIFACT GENERATOR")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00acc1;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        btn_analyzer = QPushButton("Launch Analyzer Tool")
        btn_analyzer.clicked.connect(self.launch_analyzer)
        header_layout.addWidget(btn_analyzer)
        layout.addLayout(header_layout)

        # Identity
        gb_id = QGroupBox("Target Identity")
        l_id = QHBoxLayout()
        self.inp_fname = QLineEdit(self.settings.get("default_first_name", "John"))
        self.inp_sname = QLineEdit(self.settings.get("default_surname", "Doe"))
        self.inp_net_size = QSpinBox(); self.inp_net_size.setRange(5, 100); self.inp_net_size.setValue(15)
        l_id.addWidget(QLabel("First Name:")); l_id.addWidget(self.inp_fname)
        l_id.addWidget(QLabel("Surname:")); l_id.addWidget(self.inp_sname)
        l_id.addWidget(QLabel("Network Size:")); l_id.addWidget(self.inp_net_size)
        gb_id.setLayout(l_id)
        layout.addWidget(gb_id)

        # Middle Section
        mid_layout = QHBoxLayout()
        
        # Apps Tree
        gb_apps = QGroupBox("Installed Applications")
        l_apps = QVBoxLayout()
        self.tree_apps = QTreeWidget()
        self.tree_apps.setHeaderHidden(True)
        
        catalog = self.settings.get("app_catalog", {})
        
        for category, apps in catalog.items():
            cat_item = QTreeWidgetItem(self.tree_apps)
            cat_item.setText(0, category)
            # FIX: Changed Qt.ItemIsTristate to Qt.ItemIsAutoTristate
            cat_item.setFlags(cat_item.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
            cat_item.setExpanded(True)
            
            for app_name, pkg_name in apps.items():
                app_item = QTreeWidgetItem(cat_item)
                app_item.setText(0, app_name)
                # Hide package name in a data column or just store it
                app_item.setData(0, Qt.UserRole, pkg_name) 
                app_item.setFlags(app_item.flags() | Qt.ItemIsUserCheckable)
                
                # Default checks for key apps
                if app_name in ["WhatsApp", "Instagram", "Chrome"]:
                    app_item.setCheckState(0, Qt.Checked)
                else:
                    app_item.setCheckState(0, Qt.Unchecked)
                    
        l_apps.addWidget(self.tree_apps)
        gb_apps.setLayout(l_apps)
        mid_layout.addWidget(gb_apps, 1)

        # Params
        gb_time = QGroupBox("Simulation Parameters")
        l_time = QVBoxLayout()
        
        self.combo_scenario = QComboBox()
        profiles = list(self.scenarios.get("profiles", {}).keys())
        if not profiles: profiles = ["General Use"]
        self.combo_scenario.addItems(profiles)
        
        self.date_start = QDateTimeEdit(datetime.now()); self.date_start.setCalendarPopup(True)
        self.date_end = QDateTimeEdit(datetime.now()); self.date_end.setCalendarPopup(True)
        
        self.combo_activity = QComboBox()
        self.combo_activity.addItems(["Low (20 msgs/day)", "Medium (50 msgs/day)", "High (100 msgs/day)"])
        self.combo_activity.setCurrentIndex(1)
        
        l_time.addWidget(QLabel("Scenario Profile:"))
        l_time.addWidget(self.combo_scenario)
        l_time.addWidget(QLabel("Start Date:"))
        l_time.addWidget(self.date_start)
        l_time.addWidget(QLabel("End Date:"))
        l_time.addWidget(self.date_end)
        l_time.addWidget(QLabel("Activity Level:"))
        l_time.addWidget(self.combo_activity)
        l_time.addStretch()
        gb_time.setLayout(l_time)
        mid_layout.addWidget(gb_time, 1)
        
        layout.addLayout(mid_layout)

        # Footer
        btn_layout = QHBoxLayout()
        self.btn_generate = QPushButton("INITIALIZE GENERATION SEQUENCE")
        self.btn_generate.setMinimumHeight(50)
        self.btn_generate.setStyleSheet("font-size: 16px; background-color: #00897b;")
        self.btn_generate.clicked.connect(self.start_generation)
        btn_layout.addWidget(self.btn_generate)
        
        self.btn_cancel = QPushButton("CANCEL")
        self.btn_cancel.setMinimumHeight(50)
        self.btn_cancel.setStyleSheet("font-size: 16px; background-color: #c62828;")
        self.btn_cancel.clicked.connect(self.cancel_generation)
        self.btn_cancel.setEnabled(False)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(150)
        layout.addWidget(self.log_view)

    def get_selected_apps_map(self):
        """Returns a dict {AppName: PackageName}"""
        selected = {}
        # Add Natives (Hardcoded for now or from settings)
        for nat in self.settings.get("native_apps", []):
            # Simple heuristic for native packages if not defined in catalog
            pkg = f"com.android.{nat.lower().replace(' ', '')}"
            if "chrome" in nat.lower(): pkg = "com.android.chrome"
            if "pixel" in nat.lower(): pkg = "com.google.android.apps.nexuslauncher"
            selected[nat] = pkg

        # Walk tree
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
        
        rates = [20, 50, 100]
        msgs_per_day = rates[self.combo_activity.currentIndex()]
        days = (self.date_end.dateTime().toPython() - self.date_start.dateTime().toPython()).days
        total_msgs = max(1, days * msgs_per_day)

        # Pass the map, not just a list
        apps_map = self.get_selected_apps_map()

        params = {
            "owner_name": f"{self.inp_fname.text()} {self.inp_sname.text()}",
            "start_date": self.date_start.dateTime().toPython(),
            "end_date": self.date_end.dateTime().toPython(),
            "installed_apps": apps_map, # DICTIONARY
            "network_size": self.inp_net_size.value(),
            "num_messages": total_msgs,
            "scenario": self.combo_scenario.currentText()
        }

        self.worker = GeneratorWorker(params, self.settings, self.scenarios)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_view.append)
        self.worker.finished.connect(self.generation_finished)
        self.worker.error.connect(self.generation_error)
        self.worker.start()

    def cancel_generation(self):
        if self.worker:
            self.log_view.append("Cancellation requested...")
            self.worker.stop()
            self.btn_cancel.setEnabled(False)

    def generation_finished(self):
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        QMessageBox.information(self, "Status", "Operation Completed (or Cancelled).")

    def generation_error(self, err_msg):
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.log_view.append(f"CRITICAL ERROR: {err_msg}")
        QMessageBox.critical(self, "Error", f"Generation Failed:\n{err_msg}")

    def launch_analyzer(self):
        self.analyzer = ForensicParserWindow()
        self.analyzer.show()