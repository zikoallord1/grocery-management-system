import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from backend.app.core.database import initialize_database
from backend.app.core.daily_operations import DailyMaintenanceController
from backend.app.core.licensing import verify_license
from frontend.app.ui.font_setup import setup_application_font
from frontend.app.ui.license_dialog import LicenseDialog
from frontend.app.ui.main_window import MainWindow


def main():
    initialize_database()
    app = QApplication(sys.argv)
    app.setApplicationName("نظام إدارة البقالات")
    app.setLayoutDirection(Qt.RightToLeft)
    setup_application_font(app)

    license_status = verify_license()
    if not license_status.usable:
        dialog = LicenseDialog()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        QMessageBox.warning(
            dialog,
            "البرنامج غير مفعل",
            f"{license_status.message}\n\nمعرّف التثبيت:\n{license_status.installation_id}",
        )
        return app.exec()

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
