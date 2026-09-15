import hashlib
import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from backend.app.core.database import PROJECT_ROOT


USERS_FILE = PROJECT_ROOT / "data" / "users.json"


class UsersPage(QFrame):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self._users = self._load_users()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("المستخدمون")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        desc = QLabel("إضافة وتعديل وتفعيل المستخدمين مع حفظ البيانات فعليًا على الجهاز.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(12)
        self.username = QLineEdit()
        self.username.setPlaceholderText("اسم المستخدم")
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("الاسم الكامل")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("كلمة المرور")
        self.role = QComboBox()
        self.role.addItems(["مدير النظام", "مدير", "محاسب", "بائع", "مخزن", "مستخدم مخصص"])
        form.addRow("اسم المستخدم", self.username)
        form.addRow("الاسم الكامل", self.full_name)
        form.addRow("كلمة المرور", self.password)
        form.addRow("الدور", self.role)
        layout.addLayout(form)

        buttons = QFrame()
        row = QHBoxLayout(buttons)
        self.save_button = QPushButton("حفظ المستخدم")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self._save_user)
        self.edit_button = QPushButton("تعديل المستخدم")
        self.edit_button.clicked.connect(self._edit_user)
        self.toggle_button = QPushButton("تفعيل / إيقاف")
        self.toggle_button.clicked.connect(self._toggle_user)
        row.addWidget(self.save_button)
        row.addWidget(self.edit_button)
        row.addWidget(self.toggle_button)
        layout.addWidget(buttons)

        self.user_list = QListWidget()
        self.user_list.itemClicked.connect(self._load_selected)
        layout.addWidget(self.user_list, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self._refresh_list()

        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignLeft)

    @staticmethod
    def _hash_password(password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _load_users(self):
        try:
            if USERS_FILE.exists():
                data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
        except (OSError, ValueError):
            pass
        return [{"username": "admin", "full_name": "مدير النظام", "password_hash": self._hash_password("admin123"), "role": "مدير النظام", "active": True}]

    def _write_users(self):
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text(json.dumps(self._users, ensure_ascii=False, indent=2), encoding="utf-8")

    def _refresh_list(self):
        self.user_list.clear()
        for user in self._users:
            state = "مفعل" if user.get("active", True) else "موقوف"
            self.user_list.addItem(f"{user.get('username', '')} — {user.get('full_name', '')} — {user.get('role', '')} — {state}")
        self.status.setText(f"عدد المستخدمين: {len(self._users)}")

    def _selected_index(self):
        row = self.user_list.currentRow()
        return row if 0 <= row < len(self._users) else None

    def _load_selected(self, _item):
        index = self._selected_index()
        if index is None:
            return
        user = self._users[index]
        self.username.setText(user.get("username", ""))
        self.full_name.setText(user.get("full_name", ""))
        self.password.clear()
        role_index = self.role.findText(user.get("role", ""))
        if role_index >= 0:
            self.role.setCurrentIndex(role_index)

    def _validate(self):
        username = self.username.text().strip()
        full_name = self.full_name.text().strip()
        password = self.password.text()
        if not username or not full_name:
            self.status.setText("يرجى إدخال اسم المستخدم والاسم الكامل.")
            return None
        return username, full_name, password

    def _save_user(self):
        values = self._validate()
        if values is None:
            return
        username, full_name, password = values
        if not password:
            self.status.setText("يرجى إدخال كلمة المرور عند إضافة مستخدم جديد.")
            return
        if any(u.get("username", "").casefold() == username.casefold() for u in self._users):
            self.status.setText("اسم المستخدم موجود مسبقًا. استخدم زر التعديل بدل الإضافة.")
            return
        self._users.append({
            "username": username,
            "full_name": full_name,
            "password_hash": self._hash_password(password),
            "role": self.role.currentText(),
            "active": True,
        })
        self._write_users()
        self._refresh_list()
        self.username.clear()
        self.full_name.clear()
        self.password.clear()
        self.status.setText("تمت إضافة المستخدم وحفظه بنجاح.")

    def _edit_user(self):
        index = self._selected_index()
        values = self._validate()
        if index is None or values is None:
            self.status.setText("اختر مستخدمًا من القائمة أولًا.")
            return
        username, full_name, password = values
        for i, user in enumerate(self._users):
            if i != index and user.get("username", "").casefold() == username.casefold():
                self.status.setText("اسم المستخدم مستخدم من حساب آخر.")
                return
        user = self._users[index]
        user["username"] = username
        user["full_name"] = full_name
        user["role"] = self.role.currentText()
        if password:
            user["password_hash"] = self._hash_password(password)
        self._write_users()
        self._refresh_list()
        self.status.setText("تم تعديل المستخدم وحفظ التغييرات.")

    def _toggle_user(self):
        index = self._selected_index()
        if index is None:
            self.status.setText("اختر مستخدمًا من القائمة أولًا.")
            return
        self._users[index]["active"] = not self._users[index].get("active", True)
        self._write_users()
        self._refresh_list()
        self.status.setText("تم تحديث حالة المستخدم.")
