"""KoImplicit CLI. 독립 창작 데이터셋 구축·검증·주석·평가 명령.

status / check-prompts / scenarios / generate / validate / review-doc / pairs /
annotate (sheets|agreement|pair-sheet|adjudicate) / payload / benchmark / baselines / metrics / run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _read_jsonl(path):
    from .schema import read_jsonl
    return read_jsonl(Path(path))


def _load_scenarios(path):
    from .scenarios import load_scenarios
    return load_scenarios(Path(path)) if path else None


def workspace_status(root: Path) -> dict:
    root = root.resolve()
    config = json.loads((root / "configs" / "study.json").read_text(encoding="utf-8"))
    paths = {}
    for label, relative in config["paths"].items():
        folder = (root / relative).resolve()
        if not folder.is_relative_to(root):
            raise ValueError(f"Workspace path escapes root: {label}")
        paths[label] = {"path": relative, "exists": folder.is_dir()}
    models = json.loads((root / "configs" / "models.json").read_text(encoding="utf-8"))["models"]
    return {
        "project": config["project"], "design_version": config["design_version"], "stage": config["stage"], "root": str(root),
        "datasets": config.get("datasets", {}), "budget": config.get("budget", {}),
        "configured_models": {k: v.get("model_id") for k, v in models.items()}, "paths": paths,
    }


def command_status(args, parser) -> int:
    try:
        report = workspace_status(args.root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Workspace configuration error: {error}\n")
    if args.json:
        _print(report)
    else:
        print(f"{report['project']} | design {report['design_version']} | {report['stage']}")
        print(f"Root: {report['root']}")
        print(f"Models: {report['configured_models']}")
        for label, info in report["paths"].items():
            print(f"[{'OK' if info['exists'] else 'MISSING'}] {label}: {info['path']}")
    return 0 if all(info["exists"] for info in report["paths"].values()) else 1


def command_check_prompts(args, parser) -> int:
    from .generate import GENERATE_SLOTS
    from .runner import PROMPT_SLOTS, load_prompt, validate_prompt

    failed = 0
    for path in sorted(Path(args.prompts).glob("*.json")):
        slots = GENERATE_SLOTS if path.name.startswith("generate") else PROMPT_SLOTS
        prompt = load_prompt(path, allowed_slots=slots)
        problems = validate_prompt(prompt)
        state = "approved" if prompt["template"].strip() else "template empty"
        print(f"{path.name}: {state}; version={prompt['version']}; slots={prompt['slots']}" + (f"; problems={problems}" if problems else ""))
        failed += bool(problems)
    return 1 if failed else 0


def command_scenarios(args, parser) -> int:
    from .scenarios import scenario_summary

    try:
        scenarios = _load_scenarios(args.file)
    except ValueError as e:
        parser.exit(2, f"{e}\n")
    _print(scenario_summary(scenarios))
    if args.list:
        for s in scenarios:
            print(f"{s.scenario_id}\t{s.dataset}\t{s.title}\tvariants={[v.variant for v in s.variants]}")
    return 0


def command_generate(args, parser) -> int:
    from .benchmark import load_model_config
    from .generate import generate_drafts, load_generation_prompt
    from .providers import get_adapter

    scenarios = _load_scenarios(args.scenarios)
    if args.scenario_id:
        scenarios = [s for s in scenarios if s.scenario_id in set(args.scenario_id.split(","))]
    model = load_model_config(Path(args.models), args.model)
    prompt = load_generation_prompt(Path(args.prompt))
    adapter = get_adapter(model["provider"], **model.get("adapter_options", {}))
    summary = generate_drafts(scenarios, adapter, prompt, {**model, "seed": args.seed}, Path(args.out), variants=args.variants)
    _print(summary)
    return 0 if summary["ok"] else 1


def command_validate(args, parser) -> int:
    from .validate import validate_dataset

    report = validate_dataset(Path(args.dataset), _load_scenarios(args.scenarios), Path(args.prompt) if args.prompt else None)
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.quiet:
        _print({k: v for k, v in report.items() if k != "issues"})
    else:
        _print(report)
    return 1 if (args.strict and report["n_errors"]) else 0


def command_review_doc(args, parser) -> int:
    from .schema import load_dataset
    from .validate import review_markdown, validate_samples

    samples = load_dataset(Path(args.dataset))
    report = validate_samples(samples, _load_scenarios(args.scenarios), Path(args.prompt) if args.prompt else None)
    text = review_markdown(samples, report)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"wrote {args.out} ({len(samples)} samples)")
    return 0


def command_pairs(args, parser) -> int:
    from .schema import load_dataset
    from .variations import pair_manifest

    manifest = pair_manifest(load_dataset(Path(args.dataset)))
    if args.out:
        Path(args.out).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _print({k: v for k, v in manifest.items() if k != "pairs"} if args.quiet else manifest)
    return 1 if manifest["problems"] else 0


def command_annotate(args, parser) -> int:
    from . import annotation as A
    from .schema import load_dataset, write_jsonl

    if args.step == "sheets":
        paths = A.make_sheets(load_dataset(Path(args.dataset)), args.annotators.split(","), Path(args.out), seed=args.seed, condition=args.condition)
        print("\n".join(str(p) for p in paths))
    elif args.step == "pair-sheet":
        print(A.make_pair_sheet(load_dataset(Path(args.dataset)), Path(args.out)))
    elif args.step == "agreement":
        rows = [r for p in args.sheets for r in A.load_sheet(Path(p))]
        report = A.agreement(rows)
        if args.out:
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        _print(report)
    elif args.step == "adjudicate":
        samples = load_dataset(Path(args.dataset))
        rows = [r for p in args.sheets for r in A.load_sheet(Path(p))]
        labels, summary = A.adjudicate(samples, rows, A.load_decisions(Path(args.decisions) if args.decisions else None))
        write_jsonl((l.model_dump(mode="json") for l in labels), Path(args.out))
        _print({**summary, "written": args.out})
    return 0


def command_payload(args, parser) -> int:
    from .payload import build_payload
    from .schema import load_dataset, write_jsonl

    from .benchmark import load_model_config
    from .validate import check_payload

    items, gold, skipped = build_payload(load_dataset(Path(args.dataset)), seed=args.seed, include_unreviewed=args.include_unreviewed)
    out = Path(args.out)
    write_jsonl(items, out / "items.jsonl")
    write_jsonl(gold, out / "gold.jsonl")
    # 실제로 쓴 파일과 실제 모델 설정으로 누수 검사
    written_items, written_gold = _read_jsonl(out / "items.jsonl"), _read_jsonl(out / "gold.jsonl")
    model = load_model_config(Path(args.models), args.model)
    leaks = check_payload(written_items, written_gold, model, Path(args.mcq_prompt), Path(args.qa_prompt))
    (out / "payload_manifest.json").write_text(json.dumps({"seed": args.seed, "n_items": len(items), "include_unreviewed": args.include_unreviewed,
                                                           "skipped": skipped, "dataset": str(args.dataset), "leak_check": leaks}, ensure_ascii=False, indent=2), encoding="utf-8")
    _print({"n_items": len(items), "n_skipped": len(skipped), "leak_issues": leaks, "out": str(out)})
    return 1 if leaks else 0


def command_benchmark(args, parser) -> int:
    from .benchmark import load_model_config, run_benchmark
    from .providers import get_adapter
    from .runner import load_prompt

    model = load_model_config(Path(args.models), args.model)
    try:
        adapter = get_adapter(model["provider"], **model.get("adapter_options", {}))
    except Exception as e:  # 키 없음 등
        parser.exit(2, f"provider error: {e}\n")
    items, gold = _read_jsonl(args.items), _read_jsonl(args.gold)
    try:
        report = run_benchmark(items, gold, args.conditions.split(","), adapter, load_prompt(Path(args.prompt)), model,
                               Path(args.run_dir), seed=args.seed, items_path=Path(args.items), prompt_path=Path(args.prompt),
                               allow_unreviewed=args.allow_unreviewed)
    except ValueError as e:
        parser.exit(2, f"benchmark refused: {e}\n")
    if report["contains_unreviewed"]:
        print("WARNING: run contains unreviewed samples (pilot check only; not an official evaluation)")
    _print({k: v for k, v in report.items() if k != "metrics"})
    _print({k: {kk: vv["overall_accuracy"] for kk, vv in v.items()} if k == "by_model_condition" else v for k, v in report["metrics"].items()})
    return 0


def command_baselines(args, parser) -> int:
    from .benchmark import run_baselines, write_per_sample

    out = run_baselines(_read_jsonl(args.items), _read_jsonl(args.gold))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, result in out.items():
        write_per_sample(result["rows"], out_dir / f"{name}_per_sample.csv")
        summary[name] = {"metrics": result["metrics"], "mapping_failure": result["mapping_failure"]}
    (out_dir / "baselines.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _print({name: {k: v["overall_accuracy"] for k, v in r["metrics"]["by_model_condition"].items()} for name, r in summary.items()})
    return 0


def command_metrics(args, parser) -> int:
    from .benchmark import join_gold
    from .bootstrap import cluster_bootstrap
    from .metrics import benchmark_summary, entity_accuracy

    rows = join_gold(_read_jsonl(args.normalized), _read_jsonl(args.gold))
    report = benchmark_summary(rows)
    if args.n_boot:
        report["bootstrap"] = {}
        for key in report["by_model_condition"]:
            model, condition = key.split("|")
            subset = [r for r in rows if r.get("model_label") == model and r.get("condition") == condition]
            report["bootstrap"][key] = cluster_bootstrap(subset, args.cluster, entity_accuracy, n_boot=args.n_boot, seed=args.seed)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def command_run(args, parser) -> int:
    from .providers import get_adapter
    from .runner import load_prompt, run_items

    config = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {}
    config.setdefault("model_id", args.model_id or "unset")
    config.setdefault("model_label", args.model_label)
    config.setdefault("provider", args.provider)
    summary = run_items(_read_jsonl(args.items), args.conditions.split(","), get_adapter(args.provider), load_prompt(Path(args.prompt)), config, Path(args.run_dir), seed=args.seed)
    _print(summary)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="KoImplicit: 한국어 대화 생략 주어 평가 데이터셋 구축·평가")
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("status", help="설정과 폴더 상태")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=command_status)

    p = commands.add_parser("check-prompts", help="prompt slot 파일 검사")
    p.add_argument("--prompts", default="prompts")
    p.set_defaults(func=command_check_prompts)

    p = commands.add_parser("scenarios", help="시나리오 명세 검증·요약")
    p.add_argument("--file", required=True)
    p.add_argument("--list", action="store_true")
    p.set_defaults(func=command_scenarios)

    p = commands.add_parser("generate", help="시나리오로 대화 초안 생성(mock 가능)")
    p.add_argument("--scenarios", required=True)
    p.add_argument("--scenario-id", help="쉼표 구분 scenario_id")
    p.add_argument("--variants", choices=["all", "base"], default="all")
    p.add_argument("--model", default="mock", help="configs/models.json의 모델 라벨")
    p.add_argument("--models", default="configs/models.json")
    p.add_argument("--prompt", default="prompts/generate_v1.json")
    p.add_argument("--out", required=True, help="data/generated/... (Git 제외)")
    p.add_argument("--seed", type=int, default=20261010)
    p.set_defaults(func=command_generate)

    p = commands.add_parser("validate", help="데이터셋 자동 검증")
    p.add_argument("--dataset", required=True, help="dialogues.jsonl, labels.jsonl이 있는 폴더")
    p.add_argument("--scenarios")
    p.add_argument("--prompt", default="prompts/mcq_v1.json", help="gold 누수 검사용 prompt")
    p.add_argument("--out")
    p.add_argument("--strict", action="store_true", help="오류가 있으면 종료 코드 1")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=command_validate)

    p = commands.add_parser("review-doc", help="사람이 읽는 Pilot Review Markdown 생성")
    p.add_argument("--dataset", required=True)
    p.add_argument("--scenarios")
    p.add_argument("--prompt", default="prompts/mcq_v1.json")
    p.add_argument("--out", required=True)
    p.set_defaults(func=command_review_doc)

    p = commands.add_parser("pairs", help="pair별 실제 차이와 주장한 조작 대조")
    p.add_argument("--dataset", required=True)
    p.add_argument("--out")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=command_pairs)

    p = commands.add_parser("annotate", help="사람 검수 시트·일치도·조정")
    p.add_argument("step", choices=["sheets", "pair-sheet", "agreement", "adjudicate"])
    p.add_argument("--condition", choices=["full", "local"], default="full", help="sheets: full(전체 문맥) 또는 local(목표 발화만)")
    p.add_argument("--dataset")
    p.add_argument("--annotators", default="annotator1,annotator2")
    p.add_argument("--sheets", nargs="*", default=[])
    p.add_argument("--decisions")
    p.add_argument("--out")
    p.add_argument("--seed", type=int, default=20261010)
    p.set_defaults(func=command_annotate)

    p = commands.add_parser("payload", help="평가 입력(items)과 정답(gold) 분리 생성")
    p.add_argument("--dataset", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=20261010)
    p.add_argument("--include-unreviewed", action="store_true", help="검수 전 후보도 포함(pilot 점검용)")
    p.add_argument("--models", default="configs/models.json")
    p.add_argument("--model", default="mock", help="누수 검사에 쓸 system/output_schema 설정의 모델 라벨")
    p.add_argument("--mcq-prompt", default="prompts/mcq_v1.json")
    p.add_argument("--qa-prompt", default="prompts/qa_v1.json")
    p.set_defaults(func=command_payload)

    p = commands.add_parser("benchmark", help="모델 실행 + 파싱 + 지표")
    p.add_argument("--items", required=True)
    p.add_argument("--gold", required=True)
    p.add_argument("--model", required=True, help="configs/models.json의 라벨")
    p.add_argument("--models", default="configs/models.json")
    p.add_argument("--conditions", default="full_mcq,target_only_mcq")
    p.add_argument("--prompt", default="prompts/mcq_v1.json")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--seed", type=int, default=20261010)
    p.add_argument("--allow-unreviewed", action="store_true", help="검수 전 표본 포함 허용(pilot 점검용, 결과에 표시됨)")
    p.set_defaults(func=command_benchmark)

    p = commands.add_parser("baselines", help="휴리스틱 기준선 평가")
    p.add_argument("--items", required=True)
    p.add_argument("--gold", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=command_baselines)

    p = commands.add_parser("metrics", help="normalized.jsonl + gold.jsonl로 지표 재계산")
    p.add_argument("--normalized", required=True)
    p.add_argument("--gold", required=True)
    p.add_argument("--cluster", default="conversation_id")
    p.add_argument("--n-boot", type=int, default=0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out")
    p.set_defaults(func=command_metrics)

    p = commands.add_parser("run", help="저수준 실행기(provider 요청만)")
    p.add_argument("--items", required=True)
    p.add_argument("--conditions", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--provider", default="dry")
    p.add_argument("--model-id")
    p.add_argument("--model-label", default="model_a")
    p.add_argument("--config")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=command_run)

    args = parser.parse_args(argv)
    return args.func(args, parser)
