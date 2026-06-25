import sys
import threading
import logging

logging.getLogger("werkzeug").setLevel(logging.ERROR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from server import run_server
from ui.main_window import MainWindow
from ui.styles import THEME


def main():
    # Flask agent server — background thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(THEME)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
