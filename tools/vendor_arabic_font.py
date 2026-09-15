from __future__ import annotations

import hashlib
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "frontend" / "app" / "assets" / "fonts" / "NotoSansArabic-Regular.ttf"
SOURCE_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansarabic/NotoSansArabic%5Bwdth%2Cwght%5D.ttf"
SYSTEM_CANDIDATES = (
    Path("/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"),
    Path("C:/Windows/Fonts/NotoSansArabic-Regular.ttf"),
)


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.is_file() and TARGET.stat().st_size > 100_000:
        print(f"Arabic font already present: {TARGET} ({TARGET.stat().st_size} bytes)")
        return 0

    for source in SYSTEM_CANDIDATES:
        if source.is_file() and source.stat().st_size > 100_000:
            shutil.copy2(source, TARGET)
            print(f"Vendored Arabic font from system: {source}")
            break
    else:
        print(f"Downloading official Google Fonts source: {SOURCE_URL}")
        urllib.request.urlretrieve(SOURCE_URL, TARGET)

    if not TARGET.is_file() or TARGET.stat().st_size < 100_000:
        raise RuntimeError("Noto Sans Arabic font was not materialized correctly")

    digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    print(f"Vendored Noto Sans Arabic: {TARGET.stat().st_size} bytes, sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
