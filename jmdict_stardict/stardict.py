from __future__ import annotations

import gzip
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path

from .model import Lexeme
from .render import CSS, render_article


@dataclass(frozen=True, slots=True)
class BuildOptions:
    book_name: str = "JMdict KOReader"
    language: str = "eng"
    show_alternatives: bool = True
    include_priority_tags: bool = False
    include_cross_references: bool = True
    include_source_id: bool = False
    dictzip: bool = False


@dataclass(frozen=True, slots=True)
class ArticleRecord:
    identifier: str
    word: str
    html: str
    synonyms: tuple[str, ...] = ()
    sort_key: tuple[str, ...] = ()


def write_dictionary(lexemes: list[Lexeme], output_dir: Path, options: BuildOptions) -> None:
    records: list[ArticleRecord] = []
    sorted_lexemes = sorted(
        lexemes,
        key=lambda item: (item.headword, item.reading, item.entry_sequence, item.written_form or ""),
    )
    for lexeme in sorted_lexemes:
        index_word = _formatted_index_word(lexeme)
        synonym_words = tuple(
            word for word in sorted({lexeme.headword, lexeme.reading}) if word != index_word
        )
        records.append(
            ArticleRecord(
                identifier=lexeme.identifier,
                word=index_word,
                html=render_article(
                    lexeme,
                    show_alternatives=options.show_alternatives,
                    include_priority_tags=options.include_priority_tags,
                    include_cross_references=options.include_cross_references,
                    include_source_id=options.include_source_id,
                ),
                synonyms=synonym_words,
                sort_key=(lexeme.headword, lexeme.reading, str(lexeme.entry_sequence)),
            )
        )
    write_records(records, output_dir, "jmdict-koreader", options)


def write_records(
    records: list[ArticleRecord],
    output_dir: Path,
    base_name: str,
    options: BuildOptions,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / base_name
    dict_bytes = bytearray()
    index_records: list[tuple[str, int, int]] = []
    syn_records: list[tuple[str, int]] = []
    seen_ids: set[str] = set()
    sorted_records = sorted(records, key=lambda record: record.sort_key or (record.word,))
    for article_index, record in enumerate(sorted_records):
        if record.identifier in seen_ids:
            raise ValueError(f"duplicate article identifier: {record.identifier}")
        seen_ids.add(record.identifier)
        html = record.html.encode("utf-8")
        offset = len(dict_bytes)
        dict_bytes.extend(html)
        index_records.append((record.word, offset, len(html)))
        for synonym_word in record.synonyms:
            if synonym_word != record.word:
                syn_records.append((synonym_word, article_index))

    idx_bytes = bytearray()
    for word, offset, size in index_records:
        idx_bytes.extend(word.encode("utf-8") + b"\0" + struct.pack(">II", offset, size))

    (base.with_suffix(".idx")).write_bytes(idx_bytes)
    (base.with_suffix(".dict")).write_bytes(bytes(dict_bytes))
    if options.dictzip:
        with gzip.GzipFile(filename=str(base.with_suffix(".dict.dz")), mode="wb", mtime=0) as output:
            output.write(bytes(dict_bytes))
    syn_bytes = bytearray()
    for word, index in sorted(syn_records, key=lambda item: (item[0], item[1])):
        syn_bytes.extend(word.encode("utf-8") + b"\0" + struct.pack(">I", index))
    base.with_suffix(".syn").write_bytes(syn_bytes)
    base.with_suffix(".css").write_text(CSS, encoding="utf-8")
    ifo = "\n".join(
        [
            "StarDict's dict ifo file",
            "version=3.0.0",
            f"bookname={options.book_name}",
            f"wordcount={len(index_records)}",
            f"synwordcount={len(syn_records)}",
            f"idxfilesize={len(idx_bytes)}",
            "sametypesequence=h",
            f"description=JMdict English converted for KOReader; language={options.language}",
            "",
        ]
    )
    base.with_suffix(".ifo").write_text(ifo, encoding="utf-8")
    _write_manifest(output_dir, base_name, options, sorted_records, idx_bytes, dict_bytes, syn_bytes)
    license_dir = output_dir / "LICENSES"
    license_dir.mkdir(exist_ok=True)
    (license_dir / "JMdict.txt").write_text(
        "This package contains material derived from JMdict. See https://www.edrdg.org/.\n",
        encoding="utf-8",
    )


def _formatted_index_word(lexeme: Lexeme) -> str:
    if lexeme.written_form is None:
        return lexeme.reading
    return f"{lexeme.written_form}【{lexeme.reading}】"


def _write_manifest(
    output_dir: Path,
    base_name: str,
    options: BuildOptions,
    records: list[ArticleRecord],
    idx_bytes: bytearray,
    dict_bytes: bytearray,
    syn_bytes: bytearray,
) -> None:
    manifest = {
        "name": base_name,
        "version": 1,
        "article_count": len(records),
        "idx_size": len(idx_bytes),
        "dict_size": len(dict_bytes),
        "syn_size": len(syn_bytes),
        "options": asdict(options),
    }
    (output_dir / f"{base_name}.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
