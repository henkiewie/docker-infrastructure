#!/usr/bin/env python3
"""Create a consistent, sensitive backup of wg-easy and Gotify runtime state."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import sqlite3
import tarfile


WG_DATABASE = Path("/home/mint/Templates/wg-easy/config/wg-easy.db")
WG_CONFIG = Path("/home/mint/Templates/wg-easy/config/wg0.conf")
WG_COMPOSE = Path("/home/henk/docker-compose.yml")
GOTIFY_DATABASE = Path("/home/henk/gotify/data/gotify.db")
STREAM_MONITOR_COMPOSE = Path("/home/henk/stream-monitor/docker-compose.yml")
DEFAULT_DESTINATION = Path("/home/henk/container-backups")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--owner", default="henk", help="Owner of completed archives")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate source availability and SQLite integrity without writing a backup",
    )
    return parser.parse_args()


def require_root() -> None:
    if os.geteuid() != 0:
        raise SystemExit("This backup must run as root to read the WireGuard configuration.")


def sqlite_quick_check(path: Path) -> None:
    uri = f"file:{path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=30) as connection:
        result = connection.execute("PRAGMA quick_check").fetchone()
    if not result or result[0] != "ok":
        raise RuntimeError(f"SQLite integrity check failed for {path}: {result}")


def backup_sqlite(source: Path, destination: Path) -> None:
    source_uri = f"file:{source.as_posix()}?mode=ro"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_uri, uri=True, timeout=30) as source_db:
        with sqlite3.connect(destination) as destination_db:
            source_db.backup(destination_db)
    sqlite_quick_check(destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sources() -> None:
    required = (
        WG_DATABASE,
        WG_CONFIG,
        WG_COMPOSE,
        GOTIFY_DATABASE,
        STREAM_MONITOR_COMPOSE,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required source files: " + ", ".join(missing))
    sqlite_quick_check(WG_DATABASE)
    sqlite_quick_check(GOTIFY_DATABASE)


def set_owner(path: Path, owner: str) -> None:
    account = pwd.getpwnam(owner)
    os.chown(path, account.pw_uid, account.pw_gid)


def create_backup(destination: Path, owner: str) -> tuple[Path, Path]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_name = f"container-state-{timestamp}-utc"
    destination.mkdir(parents=True, exist_ok=True)
    os.chmod(destination, 0o700)
    set_owner(destination, owner)

    staging = destination / f".{backup_name}.staging"
    archive = destination / f"{backup_name}.tar.gz"
    checksum_file = destination / f"{archive.name}.sha256"
    if staging.exists() or archive.exists() or checksum_file.exists():
        raise FileExistsError(f"Backup target already exists for {timestamp}")

    try:
        (staging / "wg-easy").mkdir(parents=True)
        (staging / "gotify").mkdir(parents=True)
        (staging / "compose").mkdir(parents=True)

        backup_sqlite(WG_DATABASE, staging / "wg-easy" / "wg-easy.db")
        shutil.copy2(WG_CONFIG, staging / "wg-easy" / "wg0.conf")
        backup_sqlite(GOTIFY_DATABASE, staging / "gotify" / "gotify.db")
        shutil.copy2(WG_COMPOSE, staging / "compose" / "wg-easy-docker-compose.yml")
        shutil.copy2(
            STREAM_MONITOR_COMPOSE,
            staging / "compose" / "stream-monitor-docker-compose.yml",
        )

        files = sorted(path for path in staging.rglob("*") if path.is_file())
        manifest = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "warning": "Sensitive backup: contains WireGuard keys and application databases.",
            "files": [
                {
                    "path": path.relative_to(staging).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
                for path in files
            ],
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        temporary_archive = archive.with_suffix(archive.suffix + ".tmp")
        with tarfile.open(temporary_archive, "w:gz") as tar:
            tar.add(staging, arcname=backup_name)
        os.chmod(temporary_archive, 0o600)
        temporary_archive.replace(archive)

        archive_hash = sha256(archive)
        checksum_file.write_text(f"{archive_hash}  {archive.name}\n", encoding="ascii")
        os.chmod(archive, 0o600)
        os.chmod(checksum_file, 0o600)
        set_owner(archive, owner)
        set_owner(checksum_file, owner)
        return archive, checksum_file
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> int:
    args = parse_args()
    if not args.check:
        require_root()
    validate_sources()
    if args.check:
        print("Source files and SQLite integrity checks passed.")
        return 0

    archive, checksum_file = create_backup(args.destination, args.owner)
    print(f"Backup created: {archive}")
    print(f"Checksum created: {checksum_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
