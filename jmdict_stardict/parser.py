from __future__ import annotations

import gzip
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO, cast

from lxml import etree

from .model import Entry, Gloss, KanjiForm, LoanwordSource, Reading, Sense

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def parse_jmdict(path: Path, *, strict: bool = False) -> Iterator[Entry]:
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
                yield _parse_entry(element)
            except Exception:
                if strict:
                    raise
            finally:
                element.clear()
                parent = element.getparent()
                while parent is not None and element.getprevious() is not None:
                    del parent[0]


def _open_xml(path: Path) -> BinaryIO:
    if path.suffix == ".gz":
        return cast(BinaryIO, gzip.open(path, "rb"))
    return path.open("rb")


def _texts(element: etree._Element, name: str) -> tuple[str, ...]:
    return tuple(child.text.strip() for child in element.findall(name) if child.text and child.text.strip())


def _parse_entry(element: etree._Element) -> Entry:
    sequence_text = element.findtext("ent_seq")
    if sequence_text is None:
        raise ValueError("entry without ent_seq")
    kanji_forms = tuple(
        KanjiForm(
            text=keb,
            information=_texts(k_ele, "ke_inf"),
            priority=_texts(k_ele, "ke_pri"),
        )
        for k_ele in element.findall("k_ele")
        if (keb := k_ele.findtext("keb"))
    )
    readings = tuple(
        Reading(
            text=reb,
            no_kanji=r_ele.find("re_nokanji") is not None,
            restricted_to=_texts(r_ele, "re_restr"),
            information=_texts(r_ele, "re_inf"),
            priority=_texts(r_ele, "re_pri"),
        )
        for r_ele in element.findall("r_ele")
        if (reb := r_ele.findtext("reb"))
    )
    senses = tuple(_parse_sense(sense, index + 1) for index, sense in enumerate(element.findall("sense")))
    return Entry(int(sequence_text), kanji_forms, readings, senses)


def _parse_sense(element: etree._Element, position: int) -> Sense:
    glosses = []
    for gloss in element.findall("gloss"):
        language = gloss.get(XML_LANG, "eng")
        if language in {"eng", "en"} and gloss.text and gloss.text.strip():
            glosses.append(Gloss(gloss.text.strip(), "eng", gloss.get("g_type")))
    loanword_sources = tuple(
        LoanwordSource(
            text=(source.text or "").strip(),
            language=source.get(XML_LANG),
            source_type=source.get("ls_type"),
            wasei=source.get("ls_wasei") == "y",
        )
        for source in element.findall("lsource")
    )
    return Sense(
        source_position=position,
        restricted_to_kanji=_texts(element, "stagk"),
        restricted_to_readings=_texts(element, "stagr"),
        part_of_speech=_texts(element, "pos"),
        cross_references=_texts(element, "xref"),
        antonyms=_texts(element, "ant"),
        fields=_texts(element, "field"),
        miscellaneous=_texts(element, "misc"),
        sense_information=_texts(element, "s_inf"),
        loanword_sources=loanword_sources,
        dialects=_texts(element, "dial"),
        glosses=tuple(glosses),
    )
