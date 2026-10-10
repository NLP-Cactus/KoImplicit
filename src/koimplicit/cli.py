"""Workspace utilities. `status` never opens corpus files; `audit` prints counts only;
`parse` writes corpus-derived files under data/ only."""

import argparse
import json
from pathlib import Path

from .audit import run_audit, run_audit_sample
from .corpus import run_parse


def workspace_status(root: Path) -> dict:
    root = root.resolve()
    config = json.loads((root / "configs" / "study.json").read_text(encoding="utf-8"))
    paths = {}
    for label, relative in config["paths"].items():
        folder = (root / relative).resolve()
        if not folder.is_relative_to(root):
            raise ValueError(f"Workspace path escapes root: {label}")
        paths[label] = {"path": relative, "exists": folder.is_dir()}
    return {
        "project": config["project"],
        "design_version": config["design_version"],
        "stage": config["stage"],
        "root": str(root),
        "source_acquired": config["source"]["acquired"],
        "structure_audited": config["source"]["structure_audited"],
        "budget": config["budget"],
        "configured_models": sum(bool(model["model_id"]) for model in config["models"]),
        "paths": paths,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="KoImplicit workspace utilities")
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="Show configuration and folder availability")
    status.add_argument("--root", type=Path, default=Path.cwd())
    status.add_argument("--json", action="store_true", help="Print machine-readable status")
    audit = commands.add_parser("audit", help="Count corpus structure and annotation patterns")
    audit.add_argument("--root", type=Path, default=Path.cwd())
    audit.add_argument("--corpus", type=Path, help="ZA 2025 spoken JSON (default: found under data/raw)")
    audit.add_argument("--cases", type=Path, help="Write cross-speaker pronoun links under data/")
    parse = commands.add_parser("parse", help="Flatten the ZA 2025 spoken release into data/interim JSONL")
    parse.add_argument("--root", type=Path, default=Path.cwd())
    parse.add_argument("--raw", type=Path, help="ZA 2025 spoken JSON (default: found under data/raw)")
    parse.add_argument("--out", type=Path, help="Output folder under data/ (default: data/interim)")
    sample = commands.add_parser("audit-sample", help="Write a stratified review sheet for the human structure audit")
    sample.add_argument("--root", type=Path, default=Path.cwd())
    sample.add_argument("--corpus", type=Path, help="ZA 2025 spoken JSON (default: found under data/raw)")
    sample.add_argument("--out", type=Path, help="Output folder under data/ (default: data/interim)")
    sample.add_argument("--seed", type=int, default=20261010)
    args = parser.parse_args(argv)
    if args.command == "audit-sample":
        try:
            report = run_audit_sample(args.root, args.corpus, args.out, args.seed)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.exit(2, f"Audit sample error: {error}\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.command == "parse":
        try:
            report = run_parse(args.root, args.raw, args.out)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.exit(2, f"Parse error: {error}\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.command == "audit":
        try:
            report = run_audit(args.root, args.corpus, args.cases)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.exit(2, f"Audit error: {error}\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    try:
        report = workspace_status(args.root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Workspace configuration error: {error}\n")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['project']} | design {report['design_version']} | {report['stage']}")
        print(f"Root: {report['root']}")
        print(f"Source acquired: {report['source_acquired']}")
        print(f"Structure audited: {report['structure_audited']}")
        print(f"Configured models: {report['configured_models']}")
        for label, info in report["paths"].items():
            state = "OK" if info["exists"] else "MISSING"
            print(f"[{state}] {label}: {info['path']}")
    return 0 if all(info["exists"] for info in report["paths"].values()) else 1
