from __future__ import annotations

import struct
from pathlib import Path


def validate_dictionary(ifo_path: Path) -> list[str]:
    issues: list[str] = []
    base = ifo_path.with_suffix("")
    idx_path = base.with_suffix(".idx")
    dict_path = base.with_suffix(".dict")
    syn_path = base.with_suffix(".syn")
    for path in (ifo_path, idx_path, dict_path, syn_path):
        if not path.exists():
            issues.append(f"missing file: {path}")
    if issues:
        return issues
    ifo = _read_ifo(ifo_path)
    idx_records = _read_idx(idx_path, issues)
    dict_size = dict_path.stat().st_size
    for word, offset, size in idx_records:
        try:
            word.encode("utf-8").decode("utf-8")
        except UnicodeDecodeError:
            issues.append(f"invalid UTF-8 word: {word!r}")
        if offset + size > dict_size:
            issues.append(f"index target outside dict: {word}")
    if idx_records != sorted(idx_records, key=lambda item: (item[0], item[1], item[2])):
        issues.append("index records are not sorted")
    expected_wordcount = int(ifo.get("wordcount", "-1"))
    if expected_wordcount != len(idx_records):
        issues.append(f"wordcount mismatch: ifo={expected_wordcount}, idx={len(idx_records)}")
    expected_idx_size = int(ifo.get("idxfilesize", "-1"))
    actual_idx_size = idx_path.stat().st_size
    if expected_idx_size != actual_idx_size:
        issues.append(f"idxfilesize mismatch: ifo={expected_idx_size}, actual={actual_idx_size}")
    syn_records = _read_syn(syn_path, issues)
    for word, target in syn_records:
        if target < 0 or target >= len(idx_records):
            issues.append(f"synonym target invalid: {word} -> {target}")
    expected_syn_count = int(ifo.get("synwordcount", "-1"))
    if expected_syn_count != len(syn_records):
        issues.append(f"synwordcount mismatch: ifo={expected_syn_count}, syn={len(syn_records)}")
    return issues


def _read_ifo(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def _read_idx(path: Path, issues: list[str]) -> list[tuple[str, int, int]]:
    data = path.read_bytes()
    records: list[tuple[str, int, int]] = []
    position = 0
    while position < len(data):
        end = data.find(b"\0", position)
        if end < 0 or end + 9 > len(data):
            issues.append("truncated idx record")
            break
        try:
            word = data[position:end].decode("utf-8")
        except UnicodeDecodeError:
            word = repr(data[position:end])
            issues.append(f"invalid UTF-8 idx word at byte {position}")
        offset, size = struct.unpack(">II", data[end + 1 : end + 9])
        records.append((word, offset, size))
        position = end + 9
    return records


def _read_syn(path: Path, issues: list[str]) -> list[tuple[str, int]]:
    data = path.read_bytes()
    records: list[tuple[str, int]] = []
    position = 0
    while position < len(data):
        end = data.find(b"\0", position)
        if end < 0 or end + 5 > len(data):
            issues.append("truncated syn record")
            break
        try:
            word = data[position:end].decode("utf-8")
        except UnicodeDecodeError:
            word = repr(data[position:end])
            issues.append(f"invalid UTF-8 syn word at byte {position}")
        (target,) = struct.unpack(">I", data[end + 1 : end + 5])
        records.append((word, target))
        position = end + 5
    return records

