import sys
import logging

# Setup basic console logging before GUI starts
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def check_requirements():
    try:
        import PySide6
        import pandas
        import faker
        return True
    except ImportError as e:
        print(f"Missing Requirement: {e.name}")
        print("Please run: pip install PySide6 pandas faker pillow")
        return False

if __name__ == "__main__":
    if not check_requirements():
        sys.exit(1)

    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    
    # Global Font adjustment for High DPI
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())