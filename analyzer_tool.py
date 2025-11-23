import os
import sqlite3
import zipfile
import tempfile
import base64
import io
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget, 
                               QTextEdit, QTableWidget, QTableWidgetItem, 
                               QFileDialog, QHeaderView, QMessageBox, QPushButton, 
                               QHBoxLayout, QLabel, QLineEdit)
from PySide6.QtCore import Qt

try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

class ForensicParserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Forensic Analyzer Lite")
        self.resize(1000, 750)
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: white; }
            QTabWidget::pane { border: 1px solid #444; }
            QTableWidget { background-color: #333; color: #ddd; gridline-color: #555; }
            QHeaderView::section { background-color: #444; color: white; padding: 4px; }
            QPushButton { background-color: #007acc; padding: 5px; border-radius: 3px; color: white; }
            QLineEdit { background-color: #3a3a3a; border: 1px solid #555; padding: 5px; color: white; }
        """)
        
        self.extraction_path = ""
        self.temp_dir = None
        self.current_figure = None
        
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        toolbar = QHBoxLayout()
        btn_load = QPushButton("Load Folder")
        btn_load.clicked.connect(self.load_folder)
        btn_zip = QPushButton("Load Zip Image")
        btn_zip.clicked.connect(self.load_zip)
        btn_export = QPushButton("Export Report")
        btn_export.clicked.connect(self.export_report)
        
        # NEW BUTTONS
        btn_map = QPushButton("Export Map")
        btn_map.clicked.connect(self.export_map)
        
        btn_graph = QPushButton("Show Social Graph")
        btn_graph.clicked.connect(self.show_social_graph)

        toolbar.addWidget(btn_load)
        toolbar.addWidget(btn_zip)
        toolbar.addWidget(btn_export)
        toolbar.addWidget(btn_map)
        toolbar.addWidget(btn_graph)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search chats or calls...")
        self.search_bar.textChanged.connect(self.filter_tables)
        toolbar.addWidget(self.search_bar)
        
        layout.addLayout(toolbar)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.txt_info = QTextEdit()
        self.txt_info.setReadOnly(True)
        self.tabs.addTab(self.txt_info, "Device Info")
        
        self.tbl_sms = QTableWidget()
        self.tabs.addTab(self.tbl_sms, "SMS / Chats")
        
        self.tbl_calls = QTableWidget()
        self.tabs.addTab(self.tbl_calls, "Call Logs")

        self.tab_heatmap = QWidget()
        self.heatmap_layout = QVBoxLayout(self.tab_heatmap)
        if not MATPLOTLIB_AVAILABLE:
            self.heatmap_layout.addWidget(QLabel("Matplotlib not found."))
        self.tabs.addTab(self.tab_heatmap, "Pattern of Life")
        
        self.tab_graph = QWidget()
        self.graph_layout = QVBoxLayout(self.tab_graph)
        self.tabs.addTab(self.tab_graph, "Social Graph")

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
                possible_root = os.path.join(self.temp_dir, "Android_Extraction")
                if os.path.exists(possible_root):
                    self.extraction_path = possible_root
                else:
                    self.extraction_path = self.temp_dir
                self.run_parsers()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Invalid Zip: {e}")

    def run_parsers(self):
        self.parse_info()
        self.parse_sms()
        self.parse_calls()
        self.generate_heatmap()
        QMessageBox.information(self, "Loaded", f"Data loaded from {os.path.basename(self.extraction_path)}")

    def filter_tables(self, text):
        text = text.lower()
        for table in [self.tbl_sms, self.tbl_calls]:
            for row in range(table.rowCount()):
                match = False
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item and text in item.text().lower():
                        match = True; break
                table.setRowHidden(row, not match)

    def parse_info(self):
        info_text = "Artifacts Found:\n"
        if os.path.exists(os.path.join(self.extraction_path, "data/system/packages.xml")): info_text += "- packages.xml (Installed Apps)\n"
        if os.path.exists(os.path.join(self.extraction_path, "data/misc/wifi/WifiConfigStore.xml")): info_text += "- WifiConfigStore.xml (WiFi Networks)\n"
        self.txt_info.setText(info_text)

    def parse_sms(self):
        db_path = os.path.join(self.extraction_path, "data/data/com.android.providers.telephony/databases/mmssms.db")
        self.tbl_sms.setRowCount(0)
        if not os.path.exists(db_path): return
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT address, date, body, type FROM sms ORDER BY date DESC")
            rows = c.fetchall()
            self.tbl_sms.setRowCount(len(rows))
            self.tbl_sms.setColumnCount(4)
            self.tbl_sms.setHorizontalHeaderLabels(["Address", "Date", "Body", "Type"])
            self.tbl_sms.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            for i, row in enumerate(rows):
                self.tbl_sms.setItem(i, 0, QTableWidgetItem(str(row[0])))
                dt = datetime.fromtimestamp(row[1]/1000).strftime('%Y-%m-%d %H:%M:%S')
                self.tbl_sms.setItem(i, 1, QTableWidgetItem(dt))
                self.tbl_sms.setItem(i, 2, QTableWidgetItem(str(row[2])))
                self.tbl_sms.setItem(i, 3, QTableWidgetItem("Inbox" if row[3] == 1 else "Sent"))
            conn.close()
        except Exception: pass

    def parse_calls(self):
        db_path = os.path.join(self.extraction_path, "data/data/com.android.providers.contacts/databases/calllog.db")
        self.tbl_calls.setRowCount(0)
        if not os.path.exists(db_path): return
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT number, date, duration, type FROM calls ORDER BY date DESC")
            rows = c.fetchall()
            self.tbl_calls.setRowCount(len(rows))
            self.tbl_calls.setColumnCount(4)
            self.tbl_calls.setHorizontalHeaderLabels(["Number", "Date", "Duration", "Type"])
            for i, row in enumerate(rows):
                self.tbl_calls.setItem(i, 0, QTableWidgetItem(str(row[0])))
                dt = datetime.fromtimestamp(row[1]/1000).strftime('%Y-%m-%d %H:%M:%S')
                self.tbl_calls.setItem(i, 1, QTableWidgetItem(dt))
                self.tbl_calls.setItem(i, 2, QTableWidgetItem(str(row[2])))
                self.tbl_calls.setItem(i, 3, QTableWidgetItem("Incoming" if row[3] == 1 else "Outgoing"))
            conn.close()
        except Exception: pass

    def generate_heatmap(self):
        if not MATPLOTLIB_AVAILABLE: return
        for i in reversed(range(self.heatmap_layout.count())): 
            self.heatmap_layout.itemAt(i).widget().setParent(None)
        db_path = os.path.join(self.extraction_path, "data/data/com.android.providers.telephony/databases/mmssms.db")
        if not os.path.exists(db_path): return
        hours = [0] * 24
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT date FROM sms")
            rows = c.fetchall()
            for r in rows:
                dt = datetime.fromtimestamp(r[0]/1000)
                hours[dt.hour] += 1
            conn.close()
        except: pass
        self.current_figure = Figure(figsize=(5, 4), dpi=100, facecolor="#2b2b2b")
        canvas = FigureCanvas(self.current_figure)
        ax = self.current_figure.add_subplot(111)
        ax.set_facecolor("#333333")
        ax.bar(range(24), hours, color="#00acc1")
        ax.set_title("Message Activity by Hour", color="white")
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        self.heatmap_layout.addWidget(canvas)

    def export_report(self):
        if not self.extraction_path:
            QMessageBox.warning(self, "Error", "No extraction loaded.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "Forensic_Report.html", "HTML Files (*.html)")
        if not path: return
        img_str = ""
        if self.current_figure:
            buf = io.BytesIO()
            self.current_figure.savefig(buf, format="png", facecolor="#2b2b2b")
            img_str = base64.b64encode(buf.getvalue()).decode()
        html = f"<html><head><style>body{{font-family:sans-serif;background:#eee;padding:20px}}.container{{background:white;padding:20px;max-width:800px;margin:auto}}h1{{color:#00acc1}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #ddd;padding:8px}}th{{background:#00acc1;color:white}}</style></head><body><div class='container'><h1>Forensic Report</h1><p>Generated: {datetime.now()}</p><h2>Pattern of Life</h2><img src='data:image/png;base64,{img_str}'/><h2>Messages</h2><table><tr><th>Address</th><th>Date</th><th>Body</th></tr>"
        for i in range(min(10, self.tbl_sms.rowCount())):
            html += f"<tr><td>{self.tbl_sms.item(i,0).text()}</td><td>{self.tbl_sms.item(i,1).text()}</td><td>{self.tbl_sms.item(i,2).text()}</td></tr>"
        html += "</table></div></body></html>"
        try:
            with open(path, "w", encoding="utf-8") as f: f.write(html)
            QMessageBox.information(self, "Success", "Report exported successfully.")
        except Exception as e: QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def export_map(self):
        if not FOLIUM_AVAILABLE:
            QMessageBox.critical(self, "Error", "Folium library not installed.")
            return
        if not self.extraction_path: return
        
        # Load Points
        loc_path = os.path.join(self.extraction_path, "sdcard/Location/history.json")
        if not os.path.exists(loc_path): return
        
        try:
            import json
            with open(loc_path, "r") as f: points = json.load(f)
            
            # Create Map
            if points:
                start = [points[0]['latitude'], points[0]['longitude']]
                m = folium.Map(location=start, zoom_start=12)
                
                line_points = []
                for p in points:
                    coord = [p['latitude'], p['longitude']]
                    line_points.append(coord)
                    folium.CircleMarker(location=coord, radius=2, color='red').add_to(m)
                
                folium.PolyLine(line_points, color="blue", weight=2.5, opacity=1).add_to(m)
                
                path, _ = QFileDialog.getSaveFileName(self, "Save Map", "Map.html", "HTML Files (*.html)")
                if path:
                    m.save(path)
                    QMessageBox.information(self, "Success", "Interactive map saved.")
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def show_social_graph(self):
        if not NETWORKX_AVAILABLE or not MATPLOTLIB_AVAILABLE:
            QMessageBox.critical(self, "Error", "NetworkX or Matplotlib not installed.")
            return
        
        # Extract contacts from SMS
        db_path = os.path.join(self.extraction_path, "data/data/com.android.providers.telephony/databases/mmssms.db")
        if not os.path.exists(db_path): return
        
        G = nx.Graph()
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT address, COUNT(*) FROM sms GROUP BY address")
            rows = c.fetchall()
            
            G.add_node("DEVICE OWNER", color='red')
            for row in rows:
                contact = row[0]
                count = row[1]
                G.add_node(contact, color='blue')
                G.add_edge("DEVICE OWNER", contact, weight=count)
            conn.close()
            
            # Draw
            for i in reversed(range(self.graph_layout.count())): 
                self.graph_layout.itemAt(i).widget().setParent(None)
                
            fig = Figure(figsize=(5, 4), dpi=100, facecolor="#2b2b2b")
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)
            ax.set_facecolor("#333333")
            
            pos = nx.spring_layout(G)
            nx.draw(G, pos, ax=ax, with_labels=True, node_color='skyblue', edge_color='white', font_color='white')
            self.graph_layout.addWidget(canvas)
            
        except Exception as e: QMessageBox.critical(self, "Error", str(e))