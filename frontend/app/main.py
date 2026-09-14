import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from backend.app.core.database import initialize_database
from frontend.app.ui.main_window import MainWindow


def main():
    initialize_database()
    app = QApplication(sys.argv)
    app.setApplicationName("نظام إدارة البقالات")
    app.setLayoutDirection(Qt.RightToLeft)
    window = MainWindow()
    window.refresh_dashboard()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
