from __future__ import annotations

import gzip
import textwrap
from pathlib import Path

import pytest

from jmdict_stardict.build import build_dictionary, inspect_entry
from jmdict_stardict.download import DownloadError, ensure_jmdict
from jmdict_stardict.jmnedict import build_jmnedict, parse_jmnedict, render_name_records
from jmdict_stardict.labels import compact_label
from jmdict_stardict.lexemes import generate_lexemes
from jmdict_stardict.parser import parse_jmdict
from jmdict_stardict.stardict import BuildOptions
from jmdict_stardict.validate import validate_dictionary

XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE JMdict [
<!ENTITY vt "Ichidan verb">
<!ENTITY uk "word usually written using kana alone">
<!ENTITY n "noun (common) (futsuumeishi)">
<!ENTITY n-suf "noun, used as a suffix">
]>
<JMdict>
<entry>
<ent_seq>100</ent_seq>
<k_ele><keb>褒める</keb><ke_pri>news1</ke_pri></k_ele>
<k_ele><keb>誉める</keb></k_ele>
<r_ele><reb>ほめる</reb><re_restr>褒める</re_restr><re_pri>ichi1</re_pri></r_ele>
<r_ele><reb>ほめる</reb><re_restr>誉める</re_restr></r_ele>
<sense><pos>&vt;</pos><stagk>褒める</stagk><gloss>to praise</gloss></sense>
<sense><stagk>誉める</stagk><misc>&uk;</misc><gloss>to commend</gloss></sense>
</entry>
<entry>
<ent_seq>101</ent_seq>
<r_ele><reb>だけ</reb></r_ele>
<sense><pos>&n;</pos><pos>&n-suf;</pos><gloss>only</gloss><gloss xml:lang="dut">maar</gloss></sense>
</entry>
</JMdict>
"""

NAMES_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE JMnedict [
<!ENTITY surname "surname or family name">
<!ENTITY masc "male given name or forename">
<!ENTITY fem "female given name or forename">
]>
<JMnedict>
<entry>
<ent_seq>200</ent_seq>
<k_ele><keb>愛</keb></k_ele>
<k_ele><keb>藍</keb></k_ele>
<r_ele><reb>あい</reb></r_ele>
<r_ele><reb>いとし</reb></r_ele>
<trans><name_type>&masc;</name_type><trans_det>Love</trans_det></trans>
<trans><name_type>&fem;</name_type><trans_det>Love</trans_det></trans>
<trans><name_type>&surname;</name_type><trans_det>Indigo</trans_det></trans>
</entry>
<entry>
<ent_seq>201</ent_seq>
<k_ele><keb>愛</keb></k_ele>
<r_ele><reb>まな</reb></r_ele>
<trans><name_type>&fem;</name_type><trans_det>Love</trans_det></trans>
</entry>
</JMnedict>
"""


def write_xml(path: Path) -> Path:
    with gzip.open(path, "wb") as output:
        output.write(XML.encode("utf-8"))
    return path


def write_names_xml(path: Path) -> Path:
    with gzip.open(path, "wb") as output:
        output.write(NAMES_XML.encode("utf-8"))
    return path


def test_parse_entities_and_generate_restricted_lexemes(tmp_path: Path) -> None:
    entries = list(parse_jmdict(write_xml(tmp_path / "JMdict_e.xml.gz"), strict=True))
    lexemes = [lexeme for entry in entries for lexeme in generate_lexemes(entry, strict=True)]
    assert [lexeme.identifier for lexeme in lexemes] == [
        "100:褒める:ほめる",
        "100:誉める:ほめる",
        "101::だけ",
    ]
    assert lexemes[0].senses[0].part_of_speech == ("Ichidan verb",)
    assert lexemes[1].senses[0].glosses[0].text == "to commend"
    assert lexemes[2].senses[0].glosses == lexemes[2].senses[0].glosses[:1]


def test_build_validate_and_inspect(tmp_path: Path) -> None:
    input_path = write_xml(tmp_path / "JMdict_e.xml.gz")
    output_dir = tmp_path / "dist"
    count = build_dictionary(input_path, output_dir, BuildOptions(include_source_id=True), strict=True)
    assert count == 3
    assert validate_dictionary(output_dir / "jmdict-koreader.ifo") == []
    article = (output_dir / "jmdict-koreader.dict").read_text(encoding="utf-8")
    ifo = (output_dir / "jmdict-koreader.ifo").read_text(encoding="utf-8")
    index = (output_dir / "jmdict-koreader.idx").read_bytes().decode("utf-8", errors="ignore")
    assert "褒める【ほめる】" in index
    assert "誉める【ほめる】" in index
    assert "sametypesequence=m" in ifo
    assert not (output_dir / "jmdict-koreader.css").exists()
    assert "<" not in article
    assert "[v1] to praise" in article
    assert "[uk] to commend" in article
    assert "[n | n-suf] only" in article
    assert "noun (common) (futsuumeishi)" not in article
    inspected = inspect_entry(input_path, "褒める", strict=True)
    assert "100:褒める:ほめる" in inspected
    assert "to praise" in inspected
    assert "to commend" not in textwrap.dedent(inspected).split("ID: 100:褒める:ほめる", 1)[1].split("ID:", 1)[0]


def test_no_download_requires_local_file(tmp_path: Path) -> None:
    with pytest.raises(DownloadError):
        ensure_jmdict(tmp_path / "missing.gz", no_download=True)


def test_compact_label_uses_yomitan_remapper() -> None:
    assert compact_label("adjective (keiyoushi)") == "adj-i"
    assert compact_label("nouns which may take the genitive case particle 'no'") == "adj-no"
    assert compact_label("female given name or forename") == "fem"
    assert compact_label("unknown label") == "unknown label"


def test_jmnedict_groups_readings_by_name_type(tmp_path: Path) -> None:
    input_path = write_names_xml(tmp_path / "JMnedict.xml.gz")
    entries = list(parse_jmnedict(input_path, strict=True))
    records = render_name_records(entries[0])
    assert len(records) == 2
    assert records[0].word == "愛"
    assert records[0].synonyms == ("あい", "いとし", "藍")
    assert "<" not in records[0].article
    assert "[masc]" in records[0].article
    assert "[fem]" in records[0].article
    assert "[surname]" in records[0].article
    assert "あい | いとし" in records[0].article
    assert "Love" not in records[0].article
    assert build_jmnedict(input_path, tmp_path / "dist", BuildOptions(), strict=True) == 2
    assert validate_dictionary(tmp_path / "dist" / "jmnedict-koreader.ifo") == []
    built_ifo = (tmp_path / "dist" / "jmnedict-koreader.ifo").read_text(encoding="utf-8")
    built_index = (tmp_path / "dist" / "jmnedict-koreader.idx").read_bytes().decode(
        "utf-8",
        errors="ignore",
    )
    built_article = (tmp_path / "dist" / "jmnedict-koreader.dict").read_text(encoding="utf-8")
    assert "sametypesequence=m" in built_ifo
    assert not (tmp_path / "dist" / "jmnedict-koreader.css").exists()
    assert built_index.count("愛") == 1
    assert built_index.count("藍") == 1
    assert "あい | いとし | まな" in built_article
    assert "Love" not in built_article
    assert "Indigo" not in built_article
