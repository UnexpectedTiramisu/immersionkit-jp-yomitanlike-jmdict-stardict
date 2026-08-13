from __future__ import annotations

from pathlib import Path

from .jmnedict import build_jmnedict
from .lexemes import generate_lexemes
from .model import Entry, Lexeme
from .parser import parse_jmdict
from .stardict import BuildOptions, write_dictionary


def build_dictionary(input_path: Path, output_dir: Path, options: BuildOptions, *, strict: bool) -> int:
    lexemes: list[Lexeme] = []
    for entry in parse_jmdict(input_path, strict=strict):
        lexemes.extend(generate_lexemes(entry, strict=strict))
    write_dictionary(lexemes, output_dir, options)
    return len(lexemes)


def build_all(
    jmdict_path: Path,
    jmnedict_path: Path,
    output_dir: Path,
    options: BuildOptions,
    *,
    strict: bool,
) -> tuple[int, int]:
    jmdict_count = build_dictionary(jmdict_path, output_dir / "jmdict", options, strict=strict)
    jmnedict_count = build_jmnedict(jmnedict_path, output_dir / "jmnedict", options, strict=strict)
    return jmdict_count, jmnedict_count


def inspect_entry(input_path: Path, query: str, *, strict: bool) -> str:
    lines: list[str] = []
    for entry in parse_jmdict(input_path, strict=strict):
        if not _entry_matches(entry, query):
            continue
        for lexeme in generate_lexemes(entry, strict=strict):
            lines.append(f"ID: {lexeme.identifier}")
            lines.append(f"HEADWORD: {lexeme.headword}")
            lines.append(f"READING: {lexeme.reading}")
            lines.append("SENSES:")
            for sense in lexeme.senses:
                glosses = "; ".join(gloss.text for gloss in sense.glosses)
                lines.append(f"  {sense.source_position}. {glosses}")
            lines.append("")
    return "\n".join(lines).rstrip() or f"No matching entries for {query}"


def _entry_matches(entry: Entry, query: str) -> bool:
    return any(form.text == query for form in entry.kanji_forms) or any(
        reading.text == query for reading in entry.readings
    )
