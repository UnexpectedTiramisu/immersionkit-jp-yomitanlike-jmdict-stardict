from __future__ import annotations

from .model import Entry, KanjiForm, Lexeme, Reading, Sense


def generate_lexemes(entry: Entry, *, strict: bool = False) -> tuple[Lexeme, ...]:
    lexemes: list[Lexeme] = []
    if entry.kanji_forms:
        for reading in entry.readings:
            if reading.no_kanji:
                continue
            kanji_candidates = _restricted_kanji(entry.kanji_forms, reading)
            for kanji_form in kanji_candidates:
                senses = tuple(
                    sense for sense in entry.senses if _sense_applies(sense, kanji_form.text, reading.text)
                )
                if senses:
                    lexemes.append(
                        Lexeme(
                            entry_sequence=entry.sequence,
                            written_form=kanji_form.text,
                            reading=reading.text,
                            kanji_information=kanji_form.information,
                            reading_information=reading.information,
                            kanji_priority=kanji_form.priority,
                            reading_priority=reading.priority,
                            senses=senses,
                            alternative_written_forms=tuple(
                                form.text for form in entry.kanji_forms if form.text != kanji_form.text
                            ),
                        )
                    )
                elif strict:
                    raise ValueError(f"entry {entry.sequence} has lexeme without senses")
    else:
        for reading in entry.readings:
            senses = tuple(sense for sense in entry.senses if _sense_applies(sense, None, reading.text))
            if senses:
                lexemes.append(
                    Lexeme(
                        entry_sequence=entry.sequence,
                        written_form=None,
                        reading=reading.text,
                        kanji_information=(),
                        reading_information=reading.information,
                        kanji_priority=(),
                        reading_priority=reading.priority,
                        senses=senses,
                        alternative_written_forms=(),
                    )
                )
            elif strict:
                raise ValueError(f"entry {entry.sequence} has kana lexeme without senses")
    return tuple(lexemes)


def _restricted_kanji(kanji_forms: tuple[KanjiForm, ...], reading: Reading) -> tuple[KanjiForm, ...]:
    if not reading.restricted_to:
        return kanji_forms
    allowed = set(reading.restricted_to)
    return tuple(form for form in kanji_forms if form.text in allowed)


def _sense_applies(sense: Sense, written_form: str | None, reading: str) -> bool:
    if sense.restricted_to_kanji and (
        written_form is None or written_form not in sense.restricted_to_kanji
    ):
        return False
    if sense.restricted_to_readings and reading not in sense.restricted_to_readings:
        return False
    return bool(sense.glosses)
