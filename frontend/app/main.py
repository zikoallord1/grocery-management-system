import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from backend.app.core.database import initialize_database
from backend.app.core.daily_operations import DailyMaintenanceController
from backend.app.core.licensing import verify_license
from frontend.app.ui.font_setup import setup_application_font
from frontend.app.ui.license_dialog import LicenseDialog
from frontend.app.ui.main_window import MainWindow
from frontend.app.ui.permissions_page import PermissionsPage
from frontend.app.ui.settings_page import SettingsPage
from frontend.app.ui.users_page import UsersPage


def _add_admin_modules(window):
    """Add administration modules to the existing top navigation without rebuilding the main window."""
    root_layout = window.centralWidget().layout()
    nav = root_layout.itemAt(1).widget()
    nav_layout = nav.layout()
    modules = [
        ("المستخدمون", UsersPage),
        ("الصلاحيات", PermissionsPage),
        ("الإعدادات", SettingsPage),
    ]
    for label, page_type in modules:
        page = page_type()
        if hasattr(page, "back_requested"):
            page.back_requested.connect(window._show_dashboard)
        window._pages[label] = page
        window.stack.addWidget(page)
        button = QPushButton(label)
        button.setObjectName("navButton")
        button.setProperty("active", False)
        button.setSizePolicy(window._nav_buttons["الرئيسية"].sizePolicy())
        button.clicked.connect(lambda checked=False, name=label: window._show_page(name))
        nav_layout.addWidget(button)
        window._nav_buttons[label] = button
        window._specs[label] = (label, "إدارة إعدادات النظام والمستخدمين والصلاحيات.", [])


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
    _add_admin_modules(window)
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
