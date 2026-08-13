from __future__ import annotations

from .yomitan_sense_remapper import to_yomitan_tag


def compact_label(label: str) -> str:
    return to_yomitan_tag(label)
