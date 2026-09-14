import sys

from PySide6.QtWidgets import QApplication

from frontend.app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("نظام إدارة البقالات")
    app.setLayoutDirection(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.RightToLeft)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
