import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from backend.app.core.database import initialize_database
from backend.app.core.daily_operations import DailyMaintenanceController
from frontend.app.ui.main_window import MainWindow


def main():
    initialize_database()
    app = QApplication(sys.argv)
    app.setApplicationName("نظام إدارة البقالات")
    app.setLayoutDirection(Qt.RightToLeft)
    window = MainWindow()
    window.refresh_dashboard()

    # Automatic daily closing + backup runs on startup and then every minute.
    # The controller is owned by the window so it stops cleanly on exit.
    maintenance = DailyMaintenanceController(window)
    window.daily_maintenance = maintenance
    maintenance.start()

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
