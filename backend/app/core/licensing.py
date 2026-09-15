from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from backend.app.core.database import DATA_DIR

LICENSE_DIR = DATA_DIR / "license"
LICENSE_FILE = LICENSE_DIR / "license.json"
INSTALLATION_ID_FILE = LICENSE_DIR / "installation_id"
PUBLIC_KEY_FILE = LICENSE_DIR / "public_key.pem"
TRIAL_DAYS = 30
SCHEMA_VERSION = 1


class LicenseError(Exception):
    pass


@dataclass(frozen=True)
class LicenseStatus:
    state: str
    message: str
    license_id: str | None = None
    customer_name: str | None = None
    store_name: str | None = None
    expires_at: date | None = None
    days_remaining: int | None = None
    installation_id: str | None = None

    @property
    def usable(self) -> bool:
        return self.state in {"TRIAL", "LICENSED"}


def _canonical_json(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def installation_id() -> str:
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    if INSTALLATION_ID_FILE.exists():
        value = INSTALLATION_ID_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    seed = f"{uuid.uuid4()}|{platform.system()}|{platform.machine()}|{platform.node()}".encode()
    value = hashlib.sha256(seed).hexdigest().upper()
    INSTALLATION_ID_FILE.write_text(value, encoding="utf-8")
    return value


def ensure_trial_start() -> date:
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    path = LICENSE_DIR / "trial_start"
    if path.exists():
        return date.fromisoformat(path.read_text(encoding="utf-8").strip())
    today = date.today()
    path.write_text(today.isoformat(), encoding="utf-8")
    return today


def load_public_key(path: Path = PUBLIC_KEY_FILE) -> Ed25519PublicKey | None:
    env_key = os.getenv("GROCERY_LICENSE_PUBLIC_KEY")
    data = env_key.encode("utf-8") if env_key else (path.read_bytes() if path.exists() else None)
    if not data:
        return None
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise LicenseError("مفتاح التحقق ليس من نوع Ed25519 المدعوم.")
    return key


def verify_license(path: Path = LICENSE_FILE, public_key_path: Path = PUBLIC_KEY_FILE) -> LicenseStatus:
    iid = installation_id()
    if not path.exists():
        start = ensure_trial_start()
        expires = start + timedelta(days=TRIAL_DAYS)
        remaining = (expires - date.today()).days
        if remaining > 0:
            return LicenseStatus("TRIAL", f"الفترة التجريبية: متبقي {remaining} يومًا.", expires_at=expires, days_remaining=remaining, installation_id=iid)
        return LicenseStatus("EXPIRED", "انتهت الفترة التجريبية. يرجى إدخال ترخيص صالح.", expires_at=expires, days_remaining=0, installation_id=iid)

    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        payload = envelope["payload"]
        signature = _unb64(envelope["signature"])
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise LicenseError("إصدار ملف الترخيص غير مدعوم.")
        public_key = load_public_key(public_key_path)
        if public_key is None:
            return LicenseStatus("CONFIG_ERROR", "مفتاح التحقق العام للترخيص غير موجود.", installation_id=iid)
        public_key.verify(signature, _canonical_json(payload))
        if payload.get("product") != "grocery-management-system":
            raise LicenseError("الترخيص لا يخص هذا البرنامج.")
        if payload.get("installation_id") != iid:
            raise LicenseError("الترخيص مرتبط بتثبيت مختلف.")
        expires = date.fromisoformat(payload["expires_at"])
        if expires < date.today():
            return LicenseStatus("EXPIRED", "انتهى الترخيص. يرجى التجديد.", license_id=payload.get("license_id"), customer_name=payload.get("customer_name"), store_name=payload.get("store_name"), expires_at=expires, days_remaining=0, installation_id=iid)
        remaining = (expires - date.today()).days
        return LicenseStatus("LICENSED", f"الترخيص صالح حتى {expires.isoformat()}.", license_id=payload.get("license_id"), customer_name=payload.get("customer_name"), store_name=payload.get("store_name"), expires_at=expires, days_remaining=remaining, installation_id=iid)
    except Exception as exc:
        return LicenseStatus("INVALID", f"ملف الترخيص غير صالح: {exc}", installation_id=iid)


def license_payload(*, license_id: str, customer_name: str, store_name: str, installation_id_value: str, expires_at: date, edition: str = "Standard", issued_at: date | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "product": "grocery-management-system",
        "license_id": license_id,
        "customer_name": customer_name.strip(),
        "store_name": store_name.strip(),
        "installation_id": installation_id_value.strip().upper(),
        "issued_at": (issued_at or date.today()).isoformat(),
        "expires_at": expires_at.isoformat(),
        "edition": edition,
    }


def sign_license(payload: dict, private_key: Ed25519PrivateKey) -> dict:
    return {"payload": payload, "signature": _b64(private_key.sign(_canonical_json(payload)))}


def load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise LicenseError("مفتاح الإصدار ليس من نوع Ed25519 المدعوم.")
    return key


def generate_authority_keys(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    private_path = directory / "license_private_key.pem"
    public_path = directory / "license_public_key.pem"
    if private_path.exists():
        private = load_private_key(private_path)
        public_path.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        return private_path, public_path
    private = Ed25519PrivateKey.generate()
    private_path.write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    try:
        os.chmod(private_path, 0o600)
    except OSError:
        pass
    public_path.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return private_path, public_path


def create_signed_license(*, private_key_path: Path, customer_name: str, store_name: str, installation_id_value: str, expires_at: date, edition: str = "Standard", license_id: str | None = None) -> dict:
    private_key = load_private_key(private_key_path)
    payload = license_payload(license_id=license_id or f"GMS-{uuid.uuid4().hex[:12].upper()}", customer_name=customer_name, store_name=store_name, installation_id_value=installation_id_value, expires_at=expires_at, edition=edition)
    return sign_license(payload, private_key)


def save_license(envelope: dict, path: Path = LICENSE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
