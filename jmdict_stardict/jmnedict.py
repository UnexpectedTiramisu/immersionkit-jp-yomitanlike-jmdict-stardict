from __future__ import annotations

import gzip
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import BinaryIO, cast

from lxml import etree

from .labels import compact_label
from .stardict import ArticleRecord, BuildOptions, write_records


@dataclass(frozen=True, slots=True)
class NameReading:
    text: str
    restricted_to: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NameTranslation:
    name_types: tuple[str, ...]
    details: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NameEntry:
    sequence: int
    kanji_forms: tuple[str, ...]
    readings: tuple[NameReading, ...]
    translations: tuple[NameTranslation, ...]


@dataclass(slots=True)
class NameGroup:
    headword: str
    categories: dict[str, list[str]]
    synonyms: set[str]
    source_sequences: list[int]


def build_jmnedict(input_path: Path, output_dir: Path, options: BuildOptions, *, strict: bool) -> int:
    groups: dict[str, NameGroup] = {}
    for entry in parse_jmnedict(input_path, strict=strict):
        merge_name_entry(groups, entry)
    records = [
        render_name_group(group, include_source_id=options.include_source_id)
        for group in groups.values()
    ]
    name_options = BuildOptions(
        book_name="JMnedict KOReader",
        language=options.language,
        show_alternatives=options.show_alternatives,
        include_priority_tags=options.include_priority_tags,
        include_cross_references=options.include_cross_references,
        include_source_id=options.include_source_id,
        dictzip=options.dictzip,
    )
    write_records(records, output_dir, "jmnedict-koreader", name_options)
    return len(records)


def parse_jmnedict(path: Path, *, strict: bool = False) -> Iterator[NameEntry]:
    with _open_xml(path) as input_file:
        context = etree.iterparse(
            input_file,
            events=("end",),
            tag="entry",
            load_dtd=True,
            resolve_entities=True,
            no_network=True,
            huge_tree=True,
        )
        for _, element in context:
            try:
                yield _parse_name_entry(element)
            except Exception:
                if strict:
                    raise
            finally:
                element.clear()
                parent = element.getparent()
                while parent is not None and element.getprevious() is not None:
                    del parent[0]


def render_name_records(entry: NameEntry, *, include_source_id: bool = False) -> list[ArticleRecord]:
    groups: dict[str, NameGroup] = {}
    merge_name_entry(groups, entry)
    return [
        render_name_group(group, include_source_id=include_source_id)
        for group in groups.values()
    ]


def merge_name_entry(groups: dict[str, NameGroup], entry: NameEntry) -> None:
    headwords = entry.kanji_forms or (entry.readings[0].text,)
    all_spellings = {*entry.kanji_forms, *(reading.text for reading in entry.readings)}
    for headword in headwords:
        group = groups.setdefault(
            headword,
            NameGroup(headword=headword, categories={}, synonyms=set(), source_sequences=[]),
        )
        group.source_sequences.append(entry.sequence)
        group.synonyms.update(all_spellings - {headword})
        readings = _readings_for_headword(entry, headword)
        grouped = _group_readings(entry, readings)
        for name_type, values in grouped.items():
            category_values = group.categories.setdefault(name_type, [])
            for value in values:
                if value not in category_values:
                    category_values.append(value)


def render_name_group(group: NameGroup, *, include_source_id: bool = False) -> ArticleRecord:
    html = _render_name_article(
        group.headword,
        {name_type: tuple(values) for name_type, values in group.categories.items()},
        source_sequences=tuple(group.source_sequences),
        include_source_id=include_source_id,
    )
    return ArticleRecord(
        identifier=f"jmnedict:{group.headword}",
        word=group.headword,
        html=html,
        synonyms=tuple(sorted(group.synonyms)),
        sort_key=(group.headword,),
    )


def _open_xml(path: Path) -> BinaryIO:
    if path.suffix == ".gz":
        return cast(BinaryIO, gzip.open(path, "rb"))
    return path.open("rb")


def _texts(element: etree._Element, name: str) -> tuple[str, ...]:
    return tuple(child.text.strip() for child in element.findall(name) if child.text and child.text.strip())


def _parse_name_entry(element: etree._Element) -> NameEntry:
    sequence_text = element.findtext("ent_seq")
    if sequence_text is None:
        raise ValueError("JMnedict entry without ent_seq")
    kanji_forms = tuple(
        keb for k_ele in element.findall("k_ele") if (keb := k_ele.findtext("keb"))
    )
    readings = tuple(
        NameReading(text=reb, restricted_to=_texts(r_ele, "re_restr"))
        for r_ele in element.findall("r_ele")
        if (reb := r_ele.findtext("reb"))
    )
    translations = []
    for trans in element.findall("trans"):
        translations.append(
            NameTranslation(
                name_types=_texts(trans, "name_type"),
                details=_texts(trans, "trans_det"),
            )
        )
    return NameEntry(int(sequence_text), kanji_forms, readings, tuple(translations))


def _readings_for_headword(entry: NameEntry, headword: str) -> tuple[str, ...]:
    readings = [
        reading.text
        for reading in entry.readings
        if not reading.restricted_to or headword in reading.restricted_to
    ]
    return tuple(dict.fromkeys(readings))


def _render_name_article(
    headword: str,
    grouped: dict[str, tuple[str, ...]],
    *,
    source_sequences: tuple[int, ...],
    include_source_id: bool,
) -> str:
    parts = ['<div class="entry"><ol>']
    for name_type, values in grouped.items():
        parts.append(
            f'<li><span class="tags">{escape(compact_label(name_type))}</span> '
            f'<span class="gloss">{escape(" | ".join(values))}</span></li>'
        )
    parts.append("</ol>")
    if include_source_id:
        sources = ", ".join(str(sequence) for sequence in source_sequences)
        parts.append(f'<div class="src">JMnedict {escape(sources)}:{escape(headword)}</div>')
    parts.append("</div>")
    return "".join(parts)


def _group_readings(entry: NameEntry, readings: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    values = readings or tuple(reading.text for reading in entry.readings)
    for translation in entry.translations:
        name_types = translation.name_types or ("unclassified name",)
        for name_type in name_types:
            for value in values:
                if value not in grouped[name_type]:
                    grouped[name_type].append(value)
    if not grouped:
        grouped["unclassified name"].extend(values)
    return {name_type: tuple(values) for name_type, values in grouped.items()}
