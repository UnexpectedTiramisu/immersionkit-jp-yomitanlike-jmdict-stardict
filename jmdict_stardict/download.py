from __future__ import annotations

import ftplib
import os
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

JM_DICT_FTP_HOST = "ftp.edrdg.org"
JM_DICT_FTP_PATH = "/pub/Nihongo/JMdict_e.gz"
JM_NEDICT_FTP_PATH = "/pub/Nihongo/JMnedict.xml.gz"
JM_DICT_CACHE_FILENAME = "JMdict_e.xml.gz"
JM_NEDICT_CACHE_FILENAME = "JMnedict.xml.gz"


class DownloadError(RuntimeError):
    pass


def cache_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "jmdict_stardict" / "cache"
    return Path.home() / ".cache" / "jmdict_stardict"


def cached_jmdict_path() -> Path:
    return cache_dir() / JM_DICT_CACHE_FILENAME


def cached_jmnedict_path() -> Path:
    return cache_dir() / JM_NEDICT_CACHE_FILENAME


def is_fresh(path: Path, now: datetime | None = None) -> bool:
    if not path.exists():
        return False
    checked_now = now or datetime.now(UTC)
    if checked_now.tzinfo is None:
        checked_now = checked_now.replace(tzinfo=UTC)
    modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    return checked_now - modified < timedelta(days=7)


def ensure_jmdict(
    explicit_path: Path | None,
    *,
    no_download: bool,
    warn: Callable[[str], None] = lambda message: print(message, file=sys.stderr),
) -> Path:
    if explicit_path is not None:
        if explicit_path.exists():
            return explicit_path
        if no_download:
            raise DownloadError(f"JMdict file does not exist: {explicit_path}")

    target = cached_jmdict_path()
    if is_fresh(target):
        return target
    if no_download:
        raise DownloadError(f"JMdict cache is missing or stale: {target}")
    try:
        download_file(target, remote_path=JM_DICT_FTP_PATH, label="JMdict")
    except Exception as exc:
        if target.exists():
            warn(f"warning: download failed; using cached JMdict: {exc}")
            return target
        raise DownloadError(f"failed to download JMdict and no cache exists: {exc}") from exc
    return target


def ensure_jmnedict(
    explicit_path: Path | None,
    *,
    no_download: bool,
    warn: Callable[[str], None] = lambda message: print(message, file=sys.stderr),
) -> Path:
    if explicit_path is not None:
        if explicit_path.exists():
            return explicit_path
        if no_download:
            raise DownloadError(f"JMnedict file does not exist: {explicit_path}")

    target = cached_jmnedict_path()
    if is_fresh(target):
        return target
    if no_download:
        raise DownloadError(f"JMnedict cache is missing or stale: {target}")
    try:
        download_file(target, remote_path=JM_NEDICT_FTP_PATH, label="JMnedict")
    except Exception as exc:
        if target.exists():
            warn(f"warning: download failed; using cached JMnedict: {exc}")
            return target
        raise DownloadError(f"failed to download JMnedict and no cache exists: {exc}") from exc
    return target


def download_file(target: Path, *, remote_path: str, label: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    temporary = Path(temporary_name)
    bytes_written = 0
    expected_size: int | None = None
    try:
        with os.fdopen(fd, "wb") as output, ftplib.FTP(JM_DICT_FTP_HOST, timeout=60) as ftp:
            ftp.login()
            ftp.set_pasv(True)
            try:
                expected_size = ftp.size(remote_path)
            except ftplib.all_errors:
                expected_size = None

            def write_chunk(chunk: bytes) -> None:
                nonlocal bytes_written
                output.write(chunk)
                bytes_written += len(chunk)
                if expected_size:
                    percent = min(100, int(bytes_written * 100 / expected_size))
                    print(f"\rDownloading {label}: {percent:3d}%", end="", file=sys.stderr)
                else:
                    print(f"\rDownloading {label}: {bytes_written // 1024} KiB", end="", file=sys.stderr)

            ftp.retrbinary(f"RETR {remote_path}", write_chunk)
        print(file=sys.stderr)
        if expected_size is not None and bytes_written != expected_size:
            raise DownloadError(f"incomplete download: got {bytes_written}, expected {expected_size}")
        if bytes_written == 0:
            raise DownloadError("downloaded file is empty")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
