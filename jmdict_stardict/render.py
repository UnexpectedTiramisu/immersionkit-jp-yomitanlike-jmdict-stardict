from __future__ import annotations

from html import escape

from .labels import compact_label
from .model import Lexeme, Sense

CSS = """\
body{font-family:sans-serif;line-height:1.35;margin:0;padding:.35em;color:#111;background:#fff}
.meta,.alts,.src{color:#666;font-size:.85em;margin:.15em 0}
ol{margin:.35em 0 0 1.35em;padding:0}
li{margin:.3em 0;padding-left:.1em}
.tags{color:#555;font-size:.9em;font-weight:700}
.refs,.source{color:#555;font-size:.9em}
.gloss{font-weight:500}
"""


def render_article(
    lexeme: Lexeme,
    *,
    show_alternatives: bool = True,
    include_priority_tags: bool = False,
    include_cross_references: bool = True,
    include_source_id: bool = False,
) -> str:
    parts = ['<div class="entry">']
    meta = tuple(lexeme.kanji_information + lexeme.reading_information)
    priorities = tuple(lexeme.kanji_priority + lexeme.reading_priority)
    if meta or (include_priority_tags and priorities):
        labels = meta + (priorities if include_priority_tags else ())
        parts.append(f'<div class="meta">{_render_tags(labels)}</div>')
    if show_alternatives and lexeme.alternative_written_forms:
        parts.append(
            f'<div class="alts">also written: {escape(", ".join(lexeme.alternative_written_forms))}</div>'
        )
    parts.append("<ol>")
    for sense in lexeme.senses:
        parts.append(_render_sense(sense, include_cross_references=include_cross_references))
    parts.append("</ol>")
    if include_source_id:
        parts.append(f'<div class="src">JMdict {lexeme.identifier}</div>')
    parts.append("</div>")
    return "".join(parts)


def _render_sense(sense: Sense, *, include_cross_references: bool) -> str:
    labels = (
        sense.part_of_speech
        + sense.fields
        + sense.miscellaneous
        + sense.dialects
        + sense.sense_information
    )
    glosses = "; ".join(
        f"{gloss.text} ({gloss.gloss_type})" if gloss.gloss_type else gloss.text for gloss in sense.glosses
    )
    body = ""
    if labels:
        body += _render_tags(labels) + " "
    body += f'<span class="gloss">{escape(glosses)}</span>'
    if sense.loanword_sources:
        sources = ", ".join(source.text or source.language or "" for source in sense.loanword_sources)
        if sources:
            body += f' <span class="source">from {escape(sources)}</span>'
    if include_cross_references and (sense.cross_references or sense.antonyms):
        refs = []
        if sense.cross_references:
            refs.append("see " + ", ".join(sense.cross_references))
        if sense.antonyms:
            refs.append("ant. " + ", ".join(sense.antonyms))
        body += f' <span class="refs">{escape(" | ".join(refs))}</span>'
    return f"<li>{body}</li>"


def _render_tags(labels: tuple[str, ...]) -> str:
    compact = " | ".join(compact_label(label) for label in labels)
    original = " | ".join(labels)
    return f'<span class="tags" title="{escape(original)}">{escape(compact)}</span>'
