from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KanjiForm:
    text: str
    information: tuple[str, ...]
    priority: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Reading:
    text: str
    no_kanji: bool
    restricted_to: tuple[str, ...]
    information: tuple[str, ...]
    priority: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoanwordSource:
    text: str
    language: str | None
    source_type: str | None
    wasei: bool


@dataclass(frozen=True, slots=True)
class Gloss:
    text: str
    language: str
    gloss_type: str | None


@dataclass(frozen=True, slots=True)
class Sense:
    source_position: int
    restricted_to_kanji: tuple[str, ...]
    restricted_to_readings: tuple[str, ...]
    part_of_speech: tuple[str, ...]
    cross_references: tuple[str, ...]
    antonyms: tuple[str, ...]
    fields: tuple[str, ...]
    miscellaneous: tuple[str, ...]
    sense_information: tuple[str, ...]
    loanword_sources: tuple[LoanwordSource, ...]
    dialects: tuple[str, ...]
    glosses: tuple[Gloss, ...]


@dataclass(frozen=True, slots=True)
class Entry:
    sequence: int
    kanji_forms: tuple[KanjiForm, ...]
    readings: tuple[Reading, ...]
    senses: tuple[Sense, ...]


@dataclass(frozen=True, slots=True)
class Lexeme:
    entry_sequence: int
    written_form: str | None
    reading: str
    kanji_information: tuple[str, ...]
    reading_information: tuple[str, ...]
    kanji_priority: tuple[str, ...]
    reading_priority: tuple[str, ...]
    senses: tuple[Sense, ...]
    alternative_written_forms: tuple[str, ...]

    @property
    def headword(self) -> str:
        return self.written_form or self.reading

    @property
    def identifier(self) -> str:
        return f"{self.entry_sequence}:{self.written_form or ''}:{self.reading}"

