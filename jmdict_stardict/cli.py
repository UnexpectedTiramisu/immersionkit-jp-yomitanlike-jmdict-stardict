from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .build import build_all, inspect_entry
from .download import DownloadError, ensure_jmdict, ensure_jmnedict
from .stardict import BuildOptions
from .validate import validate_dictionary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jmdict-stardict")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("input", nargs="?")
    build_parser.add_argument("--jmnedict")
    build_parser.add_argument("--output", required=True)
    _add_common_flags(build_parser)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("ifo")
    validate_parser.add_argument("--jm-dict")
    validate_parser.add_argument("--no-download", action="store_true")
    validate_parser.add_argument("--strict", action="store_true")
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("input", nargs="?")
    inspect_parser.add_argument("query")
    inspect_parser.add_argument("--no-download", action="store_true")
    inspect_parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            jmdict_path = ensure_jmdict(Path(args.input) if args.input else None, no_download=args.no_download)
            jmnedict_path = ensure_jmnedict(
                Path(args.jmnedict) if args.jmnedict else None,
                no_download=args.no_download,
            )
            options = BuildOptions(
                book_name=args.book_name,
                language=args.language,
                show_alternatives=args.show_alternatives,
                include_priority_tags=args.include_priority_tags,
                include_cross_references=args.include_cross_references,
                include_source_id=args.include_source_id,
                dictzip=args.dictzip,
            )
            jmdict_count, jmnedict_count = build_all(
                jmdict_path,
                jmnedict_path,
                Path(args.output),
                options,
                strict=args.strict,
            )
            print(
                f"Built {jmdict_count} JMdict lexemes and {jmnedict_count} JMnedict articles "
                f"into {args.output}"
            )
            return 0
        if args.command == "validate":
            ensure_jmdict(Path(args.jm_dict) if args.jm_dict else None, no_download=args.no_download)
            ensure_jmnedict(None, no_download=args.no_download)
            issues = validate_dictionary(Path(args.ifo))
            if issues:
                for issue in issues:
                    print(issue, file=sys.stderr)
                return 1
            print("Validation OK")
            return 0
        if args.command == "inspect":
            input_path = ensure_jmdict(Path(args.input) if args.input else None, no_download=args.no_download)
            print(inspect_entry(input_path, args.query, strict=args.strict))
            return 0
    except DownloadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--book-name", default="JMdict KOReader")
    parser.add_argument("--language", default="eng")
    parser.add_argument("--show-alternatives", dest="show_alternatives", action="store_true", default=True)
    parser.add_argument("--hide-alternatives", dest="show_alternatives", action="store_false")
    parser.add_argument("--include-priority-tags", dest="include_priority_tags", action="store_true")
    parser.add_argument("--hide-priority-tags", dest="include_priority_tags", action="store_false")
    parser.add_argument(
        "--include-cross-references", dest="include_cross_references", action="store_true", default=True
    )
    parser.add_argument("--hide-cross-references", dest="include_cross_references", action="store_false")
    parser.add_argument("--include-source-id", dest="include_source_id", action="store_true")
    parser.add_argument("--hide-source-id", dest="include_source_id", action="store_false")
    parser.add_argument("--dictzip", action="store_true")
    parser.add_argument("--config")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--no-download", action="store_true")


if __name__ == "__main__":
    raise SystemExit(main())
