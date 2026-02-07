from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED

from paths import get_portable_dir
from settings import Settings


def create_backup() -> Path:
    data_dir = get_portable_dir("data")
    backups_dir = get_portable_dir("backups")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = backups_dir / f"backup_{ts}.zip"

    files: list[Path] = []
    db_path = data_dir / "orzalan.db"
    if db_path.exists():
        files.append(db_path)

    settings_path = data_dir / "empresa.json"
    if settings_path.exists():
        files.append(settings_path)

    logo_path = Settings.load().get("logo_path")
    if logo_path:
        logo_file = Path(str(logo_path))
        if logo_file.exists():
            files.append(logo_file)

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f.name)

    return zip_path


def restore_backup(zip_file: Path) -> None:
    data_dir = get_portable_dir("data")
    if not zip_file.exists():
        raise FileNotFoundError(str(zip_file))

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with ZipFile(zip_file, "r") as zf:
            zf.extractall(tmp_path)

        for name in ["orzalan.db", "empresa.json"]:
            src = tmp_path / name
            if src.exists():
                (data_dir / name).write_bytes(src.read_bytes())

        # Restore logo if present
        for logo in tmp_path.glob("logo.*"):
            (data_dir / logo.name).write_bytes(logo.read_bytes())
