import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QMessageBox, QPushButton

from backend.app.core.database import initialize_database
from backend.app.core.daily_operations import DailyMaintenanceController
from backend.app.core.licensing import verify_license
from backend.app.mobile_server import start_mobile_server
from frontend.app.ui.font_setup import setup_application_font, apply_font_to_window
from frontend.app.ui.license_dialog import LicenseDialog
from frontend.app.ui.authenticated_main_window import AuthenticatedMainWindow
from frontend.app.ui.revenues_page import RevenuesPage
from frontend.app.ui.login_dialog import LoginDialog
from frontend.app.ui.first_run_wizard import FirstRunWizard


def _add_admin_modules(window):
    """Add only administration/finance pages that are not already in MainWindow.

    Users, permissions and license registration are intentionally opened from
    the Settings page rather than becoming separate top-level tabs.
    """
    nav = window.findChild(QFrame, "topNavigation")
    nav_layout = nav.layout() if nav is not None else None

    if "الإيرادات" not in window._pages:
        page = RevenuesPage()
        if hasattr(page, "back_requested"):
            page.back_requested.connect(window._show_dashboard)
        window._pages["الإيرادات"] = page
        window.stack.addWidget(page)
        if nav_layout is not None:
            button = QPushButton("الإيرادات")
            button.setObjectName("navButton")
            button.setProperty("active", False)
            button.setMinimumWidth(94)
            button.clicked.connect(lambda checked=False: window._show_page("الإيرادات"))
            nav_layout.insertWidget(max(0, nav_layout.count() - 1), button)
            window._nav_buttons["الإيرادات"] = button
        window._specs["الإيرادات"] = ("الإيرادات", "إدارة الإيرادات الأخرى والحركات المرتبطة بها.", [])


def _login(app):
    dialog = LoginDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return getattr(dialog, "authenticated_user", None) or dialog.user


def _show_login(dialog):
    return dialog.exec() == QDialog.DialogCode.Accepted


def main():
    initialize_database()

    app = QApplication(sys.argv)
    app.setApplicationName("نظام إدارة البقالات")
    app.setLayoutDirection(Qt.RightToLeft)
    setup_application_font(app)

    try:
        start_mobile_server()
    except OSError:
        # Keep desktop startup available if the LAN sync port is already in use.
        pass

    license_status = verify_license()
    if not license_status.usable:
        dialog = LicenseDialog()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        QMessageBox.warning(dialog, "البرنامج غير مفعل", f"{license_status.message}\n\nمعرّف التثبيت:\n{license_status.installation_id}")
        return app.exec()

    # Fresh installations stop here once for a clear, guided initialization.
    # initialize_database() has already created the database and repaired the
    # guaranteed admin/admin login before this dialog is shown.
    if not FirstRunWizard.already_completed():
        wizard = FirstRunWizard()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return 0

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
