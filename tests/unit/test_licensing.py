from datetime import date, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.app.core import licensing


def test_signed_license_round_trip_and_installation_binding(tmp_path, monkeypatch):
    license_dir = tmp_path / "license"
    monkeypatch.setattr(licensing, "LICENSE_DIR", license_dir)
    monkeypatch.setattr(licensing, "LICENSE_FILE", license_dir / "license.json")
    monkeypatch.setattr(licensing, "INSTALLATION_ID_FILE", license_dir / "installation_id")
    monkeypatch.setattr(licensing, "PUBLIC_KEY_FILE", license_dir / "public_key.pem")
    monkeypatch.setattr(licensing, "installation_id", lambda: "ABC123")

    private = Ed25519PrivateKey.generate()
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"
    private_path.write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    public_path.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))

    envelope = licensing.create_signed_license(
        private_key_path=private_path,
        customer_name="عميل الاختبار",
        store_name="بقالة الاختبار",
        installation_id_value="ABC123",
        expires_at=date.today() + timedelta(days=30),
    )
    licensing.save_license(envelope, license_dir / "license.json")
    status = licensing.verify_license(license_dir / "license.json", public_path)
    assert status.state == "LICENSED"
    assert status.customer_name == "عميل الاختبار"

    wrong = licensing.license_payload(
        license_id="GMS-WRONG",
        customer_name="عميل",
        store_name="منشأة",
        installation_id_value="OTHER",
        expires_at=date.today() + timedelta(days=30),
    )
    wrong_envelope = licensing.sign_license(wrong, private)
    licensing.save_license(wrong_envelope, license_dir / "wrong.json")
    wrong_status = licensing.verify_license(license_dir / "wrong.json", public_path)
    assert wrong_status.state == "INVALID"


def test_tampered_license_is_rejected(tmp_path, monkeypatch):
    license_dir = tmp_path / "license"
    monkeypatch.setattr(licensing, "LICENSE_DIR", license_dir)
    monkeypatch.setattr(licensing, "LICENSE_FILE", license_dir / "license.json")
    monkeypatch.setattr(licensing, "INSTALLATION_ID_FILE", license_dir / "installation_id")
    monkeypatch.setattr(licensing, "PUBLIC_KEY_FILE", license_dir / "public_key.pem")
    monkeypatch.setattr(licensing, "installation_id", lambda: "ABC123")

    private = Ed25519PrivateKey.generate()
    public_path = tmp_path / "public.pem"
    public_path.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    payload = licensing.license_payload(
        license_id="GMS-TAMPER",
        customer_name="عميل",
        store_name="منشأة",
        installation_id_value="ABC123",
        expires_at=date.today() + timedelta(days=30),
    )
    envelope = licensing.sign_license(payload, private)
    envelope["payload"]["store_name"] = "منشأة معدلة"
    licensing.save_license(envelope, license_dir / "license.json")
    status = licensing.verify_license(license_dir / "license.json", public_path)
    assert status.state == "INVALID"
