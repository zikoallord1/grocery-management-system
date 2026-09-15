from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
DOCS = ROOT / "build_docs"
PACKAGE = ROOT / "client-package"

PACKAGE.mkdir(parents=True, exist_ok=True)

files = [
    (DIST / "GroceryManagementSystem.exe", PACKAGE / "GroceryManagementSystem.exe"),
    (DIST / "GroceryLicenseManager.exe", PACKAGE / "GroceryLicenseManager.exe"),
    (DOCS / "دليل استخدام البرنامج.pdf", PACKAGE / "دليل استخدام البرنامج.pdf"),
    (DOCS / "تقرير البرنامج.pdf", PACKAGE / "تقرير البرنامج.pdf"),
    (DOCS / "معلومات الإصدار.txt", PACKAGE / "معلومات الإصدار.txt"),
]

for source, target in files:
    if not source.is_file():
        raise FileNotFoundError(f"Missing package file: {source}")
    shutil.copy2(source, target)

screens_source = DOCS / "screens"
screens_target = PACKAGE / "صور-الشرح"
if not screens_source.is_dir():
    raise FileNotFoundError(f"Missing screenshots directory: {screens_source}")
if screens_target.exists():
    shutil.rmtree(screens_target)
shutil.copytree(screens_source, screens_target)

readme = """Grocery Management System V1.0

Client package contents:
- GroceryManagementSystem.exe - Main application
- GroceryLicenseManager.exe - License manager
- Illustrated user manual PDF
- Illustrated program report PDF
- Interface screenshots
- Version and support information

Security notice:
The private license signing key must remain with the license administrator.
Never distribute the private signing key to customers.
"""
(PACKAGE / "README.txt").write_text(readme, encoding="utf-8")
print(f"Client package prepared: {PACKAGE}")
