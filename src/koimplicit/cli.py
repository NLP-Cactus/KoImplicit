"""Read-only workspace status; corpus contents are never opened."""

import argparse
import json
from pathlib import Path


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
    args = parser.parse_args(argv)
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
