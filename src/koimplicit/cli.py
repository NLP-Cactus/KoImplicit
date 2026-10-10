"""Workspace status and evaluation utilities; corpus contents are never opened by `status`."""

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


def read_jsonl(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def join_rows(normalized: list[dict], items: list[dict]) -> list[dict]:
    """normalized 행에 items의 gold·후보·대화 정보를 item_id로 붙인다."""
    by_item = {i["item_id"]: i for i in items}
    rows = []
    for r in normalized:
        item = by_item.get(r["item_id"])
        if item is None:
            continue
        rows.append({
            **r,
            "gold_entity_id": item.get("gold_entity_id"),
            "conversation_id": item.get("conversation_id"),
            "family_id": item.get("family_id"),
            "pair_id": item.get("pair_id"),
            "version": item.get("version"),
            "designated_distractor_id": item.get("designated_distractor_id"),
            "candidates": item.get("candidates"),
            "entity_roles": {c["entity_id"]: c.get("role") for c in item.get("candidates") or []},
        })
    return rows


def command_check_prompts(args) -> int:
    from .runner import load_prompt, validate_prompt

    failed = 0
    for path in sorted(Path(args.prompts).glob("*.json")):
        prompt = load_prompt(path)
        problems = validate_prompt(prompt)
        approved = bool(prompt["template"].strip())
        state = "approved" if approved else "template empty"
        print(f"{path.name}: {state}; slots={prompt['slots']}" + (f"; problems={problems}" if problems else ""))
        failed += bool(problems)
    return 1 if failed else 0


def command_metrics(args) -> int:
    from .bootstrap import cluster_bootstrap
    from .metrics import controlled_summary, entity_accuracy, natural_summary

    rows = join_rows(read_jsonl(args.normalized), read_jsonl(args.items))
    report = {}
    if args.experiment == "N":
        for condition in sorted({r["condition"] for r in rows}):
            subset = [r for r in rows if r["condition"] == condition]
            report[condition] = natural_summary(subset)
            report[condition]["entity_accuracy_ci"] = cluster_bootstrap(subset, "conversation_id", entity_accuracy, n_boot=args.n_boot, seed=args.seed)
    else:
        first, second = ("v1", "v2") if args.experiment == "A" else ("early", "late")
        report[args.experiment] = controlled_summary(rows, first, second)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def command_run(args) -> int:
    from .providers import get_adapter
    from .runner import load_prompt, run_items

    config = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {}
    config.setdefault("model_id", args.model_id or "unset")
    config.setdefault("model_label", args.model_label)
    config.setdefault("provider", args.provider)
    items = read_jsonl(args.items)
    if args.split:
        items = [i for i in items if i.get("split") == args.split]
    prompt = load_prompt(Path(args.prompt))
    adapter = get_adapter(args.provider)
    summary = run_items(items, args.conditions.split(","), adapter, prompt, config, Path(args.run_dir), seed=args.seed)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="KoImplicit workspace utilities")
    commands = parser.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Show configuration and folder availability")
    status.add_argument("--root", type=Path, default=Path.cwd())
    status.add_argument("--json", action="store_true", help="Print machine-readable status")

    check = commands.add_parser("check-prompts", help="Validate prompt slot files")
    check.add_argument("--prompts", default="prompts")
    check.set_defaults(func=command_check_prompts)

    metrics = commands.add_parser("metrics", help="Compute metrics from normalized outputs and items")
    metrics.add_argument("--normalized", required=True)
    metrics.add_argument("--items", required=True)
    metrics.add_argument("--experiment", choices=["N", "A", "B"], default="N")
    metrics.add_argument("--n-boot", type=int, default=2000)
    metrics.add_argument("--seed", type=int, default=0)
    metrics.add_argument("--out")
    metrics.set_defaults(func=command_metrics)

    run = commands.add_parser("run", help="Run items through a provider adapter and record responses")
    run.add_argument("--items", required=True)
    run.add_argument("--split")
    run.add_argument("--conditions", required=True, help="comma-separated, e.g. full_mcq,local_mcq")
    run.add_argument("--prompt", required=True)
    run.add_argument("--provider", default="dry")
    run.add_argument("--model-id")
    run.add_argument("--model-label", default="model_a")
    run.add_argument("--config", help="JSON with model_id, decoding, output_schema, system, seed")
    run.add_argument("--run-dir", required=True)
    run.add_argument("--seed", type=int, default=0)
    run.set_defaults(func=command_run)

    args = parser.parse_args(argv)
    if args.command != "status":
        return args.func(args)
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
