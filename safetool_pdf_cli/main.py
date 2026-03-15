# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""CLI entry point — ``safetool-pdf`` command with subcommands."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from pathlib import Path

from safetool_pdf_core.constants import APP_NAME, OUTPUT_SUFFIX, VERSION
from safetool_pdf_core.models import PresetName, ProgressInfo, ToolResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared across all subcommands."""
    parser.add_argument(
        "files", nargs="+", type=Path,
        help="One or more PDF files.",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=None,
        help="Output directory (default: same as input).",
    )
    parser.add_argument(
        "--suffix", type=str, default=OUTPUT_SUFFIX,
        help=f"Output file suffix (default: '{OUTPUT_SUFFIX}').",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose output.",
    )


def _validate_files(paths: list[Path]) -> list[Path]:
    """Return only existing .pdf files, printing warnings for the rest."""
    valid: list[Path] = []
    for f in paths:
        if not f.is_file():
            print(f"ERROR: File not found: {f}", file=sys.stderr)
            continue
        if f.suffix.lower() != ".pdf":
            print(f"WARNING: Skipping non-PDF file: {f}", file=sys.stderr)
            continue
        valid.append(f)
    return valid


def _setup_cancel() -> threading.Event:
    """Install Ctrl+C handler and return a cancellation event."""
    cancel_event = threading.Event()

    def _handle_sigint(_sig, _frame):
        print("\nCancelling…", file=sys.stderr)
        cancel_event.set()

    signal.signal(signal.SIGINT, _handle_sigint)
    return cancel_event


def _cli_progress(info: ProgressInfo) -> None:
    """Print progress info to stderr."""
    prefix = ""
    if info.file_total > 1:
        prefix = f"[{info.file_index}/{info.file_total}] "
    sys.stderr.write(f"\r{prefix}{info.stage}: {info.message} ({info.percent:.0f}%)  ")
    sys.stderr.flush()


# ---------------------------------------------------------------------------
# Result printers
# ---------------------------------------------------------------------------

def _print_optimize_result(result) -> None:
    """Pretty-print an OptimizeResult."""
    if result.skipped:
        print(f"SKIPPED: {result.input_path}")
        print(f"  Reason: {result.skipped_reason}")
        return

    print(f"OK: {result.input_path}")
    print(f"  → {result.output_path}")
    print(f"  Original:  {result.original_size:>12,} bytes")
    print(f"  Optimized: {result.optimized_size:>12,} bytes")
    sign = "-" if result.reduction_bytes >= 0 else "+"
    print(f"  Saved:     {sign}{abs(result.reduction_bytes):>11,} bytes ({result.reduction_pct}%)")
    if result.warnings:
        for w in result.warnings:
            print(f"  ⚠ {w}")


def _print_tool_result(result: ToolResult) -> None:
    """Pretty-print a ToolResult."""
    status = "OK" if result.success else "FAIL"
    inputs = ", ".join(str(p) for p in result.input_paths)
    print(f"{status}: {inputs}")
    if result.output_path:
        print(f"  → {result.output_path}")
    if result.message:
        print(f"  {result.message}")
    if result.warnings:
        for w in result.warnings:
            print(f"  ⚠ {w}")


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="safetool-pdf",
        description=f"{APP_NAME} {VERSION} — PDF toolkit from the command line.",
        epilog=(
            "Examples:\n"
            "  safetool-pdf optimize report.pdf\n"
            "  safetool-pdf optimize *.pdf --preset moderate -o output/\n"
            "  safetool-pdf merge a.pdf b.pdf c.pdf\n"
            "  safetool-pdf number *.pdf --start 1\n"
            "  safetool-pdf strip-metadata doc.pdf\n"
            "  safetool-pdf unlock secret.pdf --password s3cret\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version",
        version=f"{APP_NAME} {VERSION}",
    )

    sub = parser.add_subparsers(dest="command")

    # -- optimize -----------------------------------------------------------
    opt = sub.add_parser(
        "optimize", help="Optimize (compress) PDF files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(opt)
    opt.add_argument(
        "-p", "--preset",
        choices=["lossless", "moderate", "aggressive"],
        default="lossless",
        help="Optimization preset (default: lossless).",
    )
    opt.add_argument(
        "--password", type=str, default=None,
        help="Password for encrypted PDFs.",
    )
    opt.add_argument(
        "--simplify", action="store_true",
        help="Use 'Simplify' preservation mode (removes interactive features).",
    )
    opt.add_argument(
        "--dry-run", action="store_true",
        help="Analyze files without optimizing.",
    )
    custom_group = opt.add_argument_group(
        "custom mode",
        "Use --custom to enable custom optimization parameters.",
    )
    custom_group.add_argument("--custom", action="store_true",
        help="Enable custom optimization mode (ignores --preset).")
    custom_group.add_argument("--dpi", type=int, default=150,
        help="Target DPI for image recompression (default: 150).")
    custom_group.add_argument("--quality", type=int, default=80,
        help="JPEG quality for image recompression (default: 80).")
    custom_group.add_argument("--gs-font-subset", action="store_true",
        help="Enable Ghostscript font subsetting.")
    custom_group.add_argument("--gs-full-rewrite", action="store_true",
        help="Enable Ghostscript full PDF rewrite.")
    custom_group.add_argument("--remove-metadata", action="store_true",
        help="Remove document metadata.")
    custom_group.add_argument("--flatten-forms", action="store_true",
        help="Flatten interactive forms.")
    custom_group.add_argument("--remove-js", action="store_true",
        help="Remove JavaScript from the PDF.")

    # -- merge --------------------------------------------------------------
    mg = sub.add_parser("merge", help="Merge multiple PDFs into one.")
    _add_common_args(mg)

    # -- number -------------------------------------------------------------
    nm = sub.add_parser("number", help="Stamp correlative page numbers on PDFs.")
    _add_common_args(nm)
    nm.add_argument(
        "--start", type=int, default=1,
        help="Starting number (default: 1).",
    )

    # -- strip-metadata -----------------------------------------------------
    sm = sub.add_parser("strip-metadata", help="Remove all metadata from PDFs.")
    _add_common_args(sm)

    # -- unlock -------------------------------------------------------------
    ul = sub.add_parser("unlock", help="Remove password protection from PDFs.")
    _add_common_args(ul)
    ul.add_argument(
        "--password", type=str, required=True,
        help="Password to decrypt the PDF(s).",
    )

    return parser


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def _cmd_optimize(args: argparse.Namespace) -> int:
    """Handle the *optimize* subcommand."""
    from safetool_pdf_core.tools.optimize import optimize, optimize_batch
    from safetool_pdf_core.tools.optimize import preset_by_name

    # Build options
    if args.custom:
        from safetool_pdf_core.models import (
            CleanupOptions,
            GhostscriptOptions,
            LossyImageOptions,
            OptimizeOptions,
        )

        options = OptimizeOptions(
            preset=PresetName.CUSTOM,
            lossy_images=LossyImageOptions(
                enabled=True,
                target_dpi=args.dpi,
                jpeg_quality=args.quality,
            ),
            ghostscript=GhostscriptOptions(
                enabled=args.gs_font_subset or args.gs_full_rewrite,
                font_subsetting=args.gs_font_subset,
                full_rewrite=args.gs_full_rewrite,
            ),
            cleanup=CleanupOptions(
                remove_metadata=args.remove_metadata,
                flatten_forms=args.flatten_forms,
                remove_javascript=args.remove_js,
            ),
        )
    else:
        preset_map = {
            "lossless": PresetName.LOSSLESS,
            "moderate": PresetName.MODERATE,
            "aggressive": PresetName.AGGRESSIVE,
        }
        options = preset_by_name(preset_map[args.preset])

    options.output_suffix = args.suffix

    if args.password:
        options.password = args.password

    if args.simplify:
        from safetool_pdf_core.models import PreservationMode
        from safetool_pdf_core.tools.optimize import cleanup_for

        options.preservation = PreservationMode.SIMPLIFY
        options.cleanup = cleanup_for(PreservationMode.SIMPLIFY)

    valid_files = _validate_files(args.files)
    if not valid_files:
        print("No valid PDF files to process.", file=sys.stderr)
        return 1

    # Dry-run
    if args.dry_run:
        from safetool_pdf_core.analyzer import analyze

        for f in valid_files:
            print(f"\n{'='*60}")
            print(f"File: {f}")
            try:
                result = analyze(f, password=args.password)
                print(f"  Pages:      {result.page_count}")
                print(f"  Size:       {result.file_size:,} bytes")
                print(f"  Images:     {len(result.images)}")
                print(f"  Fonts:      {len(result.fonts)}")
                print(f"  Encrypted:  {result.is_encrypted}")
                print(f"  Signatures: {result.has_signatures}")
                print(f"  PDF/A:      {result.is_pdfa} {result.pdfa_level}")
                print(f"  Optimized:  {result.already_optimized}")
                print(f"  Est. reduction: ~{result.estimated_reduction_pct}%")
                if result.warnings:
                    for w in result.warnings:
                        print(f"  ⚠ {w}")
            except Exception as exc:
                print(f"  ERROR: {exc}", file=sys.stderr)
        return 0

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    cancel_event = _setup_cancel()
    progress_cb = _cli_progress if args.verbose else None

    try:
        if len(valid_files) == 1:
            result = optimize(
                valid_files[0],
                options=options,
                output_dir=args.output_dir,
                progress_cb=progress_cb,
                cancel=cancel_event,
            )
            print()
            _print_optimize_result(result)
        else:
            results = optimize_batch(
                valid_files,
                options=options,
                output_dir=args.output_dir,
                progress_cb=progress_cb,
                cancel=cancel_event,
            )
            print()
            for r in results:
                _print_optimize_result(r)
                print()
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    """Handle the *merge* subcommand."""
    from safetool_pdf_core.tools.merge import execute

    valid_files = _validate_files(args.files)
    if len(valid_files) < 2:
        print("Merge requires at least 2 PDF files.", file=sys.stderr)
        return 1

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    cancel_event = _setup_cancel()
    progress_cb = _cli_progress if args.verbose else None

    try:
        results = execute(
            valid_files,
            output_dir=args.output_dir,
            output_suffix=args.suffix,
            progress_cb=progress_cb,
            cancel=cancel_event,
        )
        print()
        for r in results:
            _print_tool_result(r)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    return 0


def _cmd_number(args: argparse.Namespace) -> int:
    """Handle the *number* subcommand."""
    from safetool_pdf_core.tools.numbering import execute

    valid_files = _validate_files(args.files)
    if not valid_files:
        print("No valid PDF files to process.", file=sys.stderr)
        return 1

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    cancel_event = _setup_cancel()
    progress_cb = _cli_progress if args.verbose else None

    try:
        results = execute(
            valid_files,
            output_dir=args.output_dir,
            output_suffix=args.suffix,
            start_number=args.start,
            progress_cb=progress_cb,
            cancel=cancel_event,
        )
        print()
        for r in results:
            _print_tool_result(r)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    return 0


def _cmd_strip_metadata(args: argparse.Namespace) -> int:
    """Handle the *strip-metadata* subcommand."""
    from safetool_pdf_core.tools.metadata import execute

    valid_files = _validate_files(args.files)
    if not valid_files:
        print("No valid PDF files to process.", file=sys.stderr)
        return 1

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    cancel_event = _setup_cancel()
    progress_cb = _cli_progress if args.verbose else None

    try:
        results = execute(
            valid_files,
            output_dir=args.output_dir,
            output_suffix=args.suffix,
            progress_cb=progress_cb,
            cancel=cancel_event,
        )
        print()
        for r in results:
            _print_tool_result(r)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    return 0


def _cmd_unlock(args: argparse.Namespace) -> int:
    """Handle the *unlock* subcommand."""
    from safetool_pdf_core.tools.unlock import execute

    valid_files = _validate_files(args.files)
    if not valid_files:
        print("No valid PDF files to process.", file=sys.stderr)
        return 1

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    cancel_event = _setup_cancel()
    progress_cb = _cli_progress if args.verbose else None

    try:
        results = execute(
            valid_files,
            password=args.password,
            output_dir=args.output_dir,
            output_suffix=args.suffix,
            progress_cb=progress_cb,
            cancel=cancel_event,
        )
        print()
        for r in results:
            _print_tool_result(r)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    return 0


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_COMMANDS = {
    "optimize": _cmd_optimize,
    "merge": _cmd_merge,
    "number": _cmd_number,
    "strip-metadata": _cmd_strip_metadata,
    "unlock": _cmd_unlock,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Logging
    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    if not args.command:
        parser.print_help()
        return 2

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 2

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
