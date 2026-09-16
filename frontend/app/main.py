import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QDialog

from backend.app.core.database import initialize_database
from backend.app.core.daily_operations import DailyMaintenanceController
from backend.app.core.licensing import verify_license
from frontend.app.ui.font_setup import setup_application_font, apply_font_to_window
from frontend.app.ui.license_dialog import LicenseDialog
from frontend.app.ui.authenticated_main_window import AuthenticatedMainWindow
from frontend.app.ui.permissions_page import PermissionsPage
from frontend.app.ui.products_page import ProductsPage
from frontend.app.ui.revenues_page import RevenuesPage
from frontend.app.ui.settings_page import SettingsPage
from frontend.app.ui.users_page import UsersPage
from frontend.app.ui.login_dialog import LoginDialog


def _add_admin_modules(window):
    root_layout = window.centralWidget().layout()
    sidebar = root_layout.itemAt(0).widget()
    nav_layout = sidebar.layout()
    modules = [
        ("الإيرادات", RevenuesPage),
        ("المستخدمون", UsersPage),
        ("الصلاحيات", PermissionsPage),
        ("الإعدادات", SettingsPage),
    ]
    for label, page_type in modules:
        if label in window._pages:
            continue
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
        nav_layout.insertWidget(max(2, nav_layout.count() - 2), button)
        window._nav_buttons[label] = button
        window._specs[label] = (label, "إدارة الأصناف والإيرادات والمستخدمين والصلاحيات وإعدادات النظام.", [])


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
        QMessageBox.warning(dialog, "البرنامج غير مفعل", f"{license_status.message}\n\nمعرّف التثبيت:\n{license_status.installation_id}")
        return app.exec()

    while True:
        login = LoginDialog()
        if login.exec() != QDialog.DialogCode.Accepted:
            return 0
        user = login.authenticated_user
        window = AuthenticatedMainWindow(user)
        _add_admin_modules(window)
        apply_font_to_window(window, app)
        window._notification_timer.setInterval(30000)
        window.refresh_dashboard()
        maintenance = DailyMaintenanceController(window)
        window.daily_maintenance = maintenance
        maintenance.start()
        window.show()
        window._show_page("الرئيسية")

        logged_out = {"value": False}

        def logout():
            logged_out["value"] = True
            window.close()

        window.logout_requested.connect(logout)
        app.processEvents()
        while window.isVisible():
            app.processEvents()
        if not logged_out["value"]:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
