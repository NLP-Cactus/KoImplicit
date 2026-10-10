"""평가 지표. 설계안 v2.0 12.2의 정의를 함수로 옮긴다.

행(row) 형식은 normalize 결과와 items 파일을 item_id로 join한 dict다.
필수 키: item_id, condition, model_label, gold_entity_id, predicted_entity_id, parse_status.
선택 키: entity_roles(dict: entity_id -> role), pair_id, family_id, version,
        designated_distractor_id, conversation_id.

모든 지표 함수는 Metric(value, numerator, denominator)을 반환한다.
분모가 0이면 value는 None이다.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from typing import Callable, Iterable

PARSE_STATUSES = ("ok", "invalid", "abstain", "missing", "unmapped")


@dataclass(frozen=True)
class Metric:
    value: float | None
    numerator: int
    denominator: int

    def as_dict(self) -> dict:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> Metric:
    value = numerator / denominator if denominator else None
    return Metric(value, numerator, denominator)


def is_correct(row: dict) -> bool:
    """parse_status가 ok이고 예측 entity가 gold와 같을 때만 정답이다."""
    return row.get("parse_status") == "ok" and row.get("predicted_entity_id") == row.get("gold_entity_id")


def role_of(row: dict, entity_id: str | None) -> str | None:
    roles = row.get("entity_roles") or {}
    return roles.get(entity_id)


def entity_accuracy(rows: Iterable[dict]) -> Metric:
    rows = list(rows)
    return _ratio(sum(is_correct(r) for r in rows), len(rows))


def role_accuracy(rows: Iterable[dict]) -> Metric:
    """예측 entity를 목표 발화 기준 role로 바꾼 뒤 gold role과 비교한다."""
    rows = list(rows)
    hits = 0
    for r in rows:
        if r.get("parse_status") != "ok":
            continue
        gold_role = role_of(r, r.get("gold_entity_id"))
        pred_role = role_of(r, r.get("predicted_entity_id"))
        if gold_role is not None and gold_role == pred_role:
            hits += 1
    return _ratio(hits, len(rows))


def same_role_wrong_entity_rate(rows: Iterable[dict]) -> Metric:
    """role은 맞았지만 entity가 다른 오류의 비율."""
    rows = list(rows)
    hits = 0
    for r in rows:
        if r.get("parse_status") != "ok" or is_correct(r):
            continue
        gold_role = role_of(r, r.get("gold_entity_id"))
        if gold_role is not None and gold_role == role_of(r, r.get("predicted_entity_id")):
            hits += 1
    return _ratio(hits, len(rows))


def status_counts(rows: Iterable[dict]) -> dict:
    counts = Counter(r.get("parse_status") for r in rows)
    return {status: counts.get(status, 0) for status in PARSE_STATUSES}


def distractor_rate(rows: Iterable[dict], distractor_key: str = "designated_distractor_id") -> Metric:
    rows = list(rows)
    hits = sum(
        1 for r in rows
        if r.get("parse_status") == "ok" and r.get(distractor_key) and r.get("predicted_entity_id") == r.get(distractor_key)
    )
    return _ratio(hits, len(rows))


def chance_level(rows: Iterable[dict], candidates_key: str = "candidates") -> Metric:
    """후보 수별 무작위 선택 기대치의 평균. candidates가 없는 행은 분모에서 뺀다."""
    expected = [1 / len(r[candidates_key]) for r in rows if r.get(candidates_key)]
    if not expected:
        return Metric(None, 0, 0)
    return Metric(sum(expected) / len(expected), len(expected), len(expected))


@dataclass(frozen=True)
class Pair:
    pair_id: str
    family_id: str | None
    c1: int
    c2: int
    first: dict
    second: dict


def build_pairs(rows: Iterable[dict], first_version: str, second_version: str) -> tuple[list[Pair], list[str]]:
    """pair_id로 두 버전을 묶는다. 한쪽이 없으면 제외하고 그 pair_id를 함께 돌려준다."""
    by_pair: dict[str, dict[str, dict]] = {}
    for r in rows:
        pair_id = r.get("pair_id")
        version = r.get("version")
        if pair_id is None or version not in (first_version, second_version):
            continue
        by_pair.setdefault(pair_id, {})[version] = r
    pairs: list[Pair] = []
    dropped: list[str] = []
    for pair_id, versions in sorted(by_pair.items()):
        if first_version not in versions or second_version not in versions:
            dropped.append(pair_id)
            continue
        first, second = versions[first_version], versions[second_version]
        pairs.append(Pair(pair_id, first.get("family_id"), int(is_correct(first)), int(is_correct(second)), first, second))
    return pairs, dropped


def pair_accuracy(pairs: Iterable[Pair]) -> Metric:
    pairs = list(pairs)
    return _ratio(sum(p.c1 * p.c2 for p in pairs), len(pairs))


def paired_harm(pairs: Iterable[Pair]) -> Metric:
    """첫 버전 정답, 둘째 버전 오답인 쌍의 비율."""
    pairs = list(pairs)
    return _ratio(sum(1 for p in pairs if p.c1 == 1 and p.c2 == 0), len(pairs))


def paired_recovery(pairs: Iterable[Pair]) -> Metric:
    pairs = list(pairs)
    return _ratio(sum(1 for p in pairs if p.c1 == 0 and p.c2 == 1), len(pairs))


def pair_transition_counts(pairs: Iterable[Pair]) -> dict:
    """원시 변화 개수. 적은 family 수에서는 CI보다 이 표를 먼저 본다."""
    counts = Counter((p.c1, p.c2) for p in pairs)
    return {
        "both_correct": counts.get((1, 1), 0),
        "correct_to_wrong": counts.get((1, 0), 0),
        "wrong_to_correct": counts.get((0, 1), 0),
        "both_wrong": counts.get((0, 0), 0),
    }


def paired_condition_difference(rows: Iterable[dict], condition_a: str, condition_b: str) -> Metric:
    """같은 item_id가 두 조건 모두에 있는 행만 써서 정답 여부 차이(a - b)의 평균을 구한다."""
    by_item: dict[str, dict[str, dict]] = {}
    for r in rows:
        if r.get("condition") in (condition_a, condition_b):
            by_item.setdefault(r["item_id"], {})[r["condition"]] = r
    diffs = [
        int(is_correct(v[condition_a])) - int(is_correct(v[condition_b]))
        for v in by_item.values() if condition_a in v and condition_b in v
    ]
    if not diffs:
        return Metric(None, 0, 0)
    return Metric(sum(diffs) / len(diffs), sum(diffs), len(diffs))


def group_by(rows: Iterable[dict], key: str | Callable[[dict], object]) -> dict:
    getter = key if callable(key) else (lambda r: r.get(key))
    groups: dict = {}
    for r in rows:
        groups.setdefault(getter(r), []).append(r)
    return groups


def metric_table(rows: Iterable[dict], key: str | Callable[[dict], object], metric: Callable[[Iterable[dict]], Metric]) -> dict:
    """보조표용. key별로 metric을 계산해 {group: Metric.as_dict()}를 돌려준다."""
    return {str(group): metric(group_rows).as_dict() for group, group_rows in sorted(group_by(rows, key).items(), key=lambda kv: str(kv[0]))}


def natural_summary(rows: Iterable[dict]) -> dict:
    """자연 자료 한 조건·한 모델의 요약. 주지표 1(Full entity accuracy)과 보조표를 함께 낸다."""
    rows = list(rows)
    return {
        "entity_accuracy": entity_accuracy(rows).as_dict(),
        "role_accuracy": role_accuracy(rows).as_dict(),
        "same_role_wrong_entity_rate": same_role_wrong_entity_rate(rows).as_dict(),
        "chance_level": chance_level(rows).as_dict(),
        "status_counts": status_counts(rows),
        "by_role": metric_table(rows, lambda r: role_of(r, r.get("gold_entity_id")), entity_accuracy),
        "by_candidate_count": metric_table(rows, lambda r: len(r.get("candidates") or []), entity_accuracy),
        "n_conversations": len({r.get("conversation_id") for r in rows}),
    }


def controlled_summary(rows: Iterable[dict], first_version: str, second_version: str) -> dict:
    """통제 실험 한 모델의 요약. A는 (v1, v2), B는 (early, late)를 넘긴다."""
    rows = list(rows)
    pairs, dropped = build_pairs(rows, first_version, second_version)
    summary = {
        "pair_accuracy": pair_accuracy(pairs).as_dict(),
        "paired_harm": paired_harm(pairs).as_dict(),
        "paired_recovery": paired_recovery(pairs).as_dict(),
        "transitions": pair_transition_counts(pairs),
        "n_pairs": len(pairs),
        "n_families": len({p.family_id for p in pairs}),
        "dropped_pairs": dropped,
        "status_counts": status_counts(rows),
    }
    if any(r.get("designated_distractor_id") for r in rows):
        summary["distractor_rate_by_version"] = metric_table(rows, "version", distractor_rate)
    return summary


# --------------------------------------------------------------------------- 벤치마크 요약(독립 창작 데이터셋)

def confusion_matrix(rows: Iterable[dict], gold_key: str = "gold_role", pred_key: str = "predicted_role") -> dict:
    """gold 역할 × 예측 역할. parse_status가 ok가 아니면 예측 칸에 상태를 적는다."""
    matrix: dict = {}
    for r in rows:
        gold = str(r.get(gold_key))
        pred = str(r.get(pred_key)) if r.get("parse_status") == "ok" else str(r.get("parse_status"))
        matrix.setdefault(gold, {})
        matrix[gold][pred] = matrix[gold].get(pred, 0) + 1
    return {g: dict(sorted(v.items())) for g, v in sorted(matrix.items())}


def entity_confusion(rows: Iterable[dict]) -> dict:
    return confusion_matrix(rows, gold_key="gold_entity_id", pred_key="predicted_entity_id")


def distractor_error_rate(rows: Iterable[dict]) -> Metric:
    """distractor_present인 항목 중 경쟁 개체(지정값 또는 가장 최근 언급 개체)를 고른 비율."""
    subset = [r for r in rows if r.get("distractor_present")]
    hits = 0
    for r in subset:
        target = r.get("designated_distractor_id") or r.get("most_recent_mentioned_id")
        if r.get("parse_status") == "ok" and target and r.get("predicted_entity_id") == target and target != r.get("gold_entity_id"):
            hits += 1
    return _ratio(hits, len(subset))


def pair_consistency(rows: Iterable[dict]) -> dict:
    """같은 pair_id의 두 항목이 모두 정답인 비율과 전이 개수. 한쪽이 없는 pair는 제외한다."""
    groups: dict = {}
    for r in rows:
        for pid in (r.get("pair_ids") or ([r["pair_id"]] if r.get("pair_id") else [])):
            groups.setdefault(pid, []).append(r)
    complete = {k: v for k, v in groups.items() if len(v) == 2}
    both = sum(all(is_correct(r) for r in v) for v in complete.values())
    counts = Counter(tuple(sorted(int(is_correct(r)) for r in v)) for v in complete.values())
    return {
        "pair_accuracy": _ratio(both, len(complete)).as_dict(),
        "n_pairs": len(complete),
        "dropped_pairs": sorted(k for k, v in groups.items() if len(v) != 2),
        "transitions": {"both_correct": counts.get((1, 1), 0), "one_correct": counts.get((0, 1), 0), "both_wrong": counts.get((0, 0), 0)},
    }


def benchmark_summary(rows: Iterable[dict]) -> dict:
    """모델×조건별 요약. 행은 benchmark.join_gold 결과다."""
    rows = list(rows)
    out: dict = {"by_model_condition": {}, "context_benefit": {}}
    for (model, condition), subset in sorted(group_by(rows, lambda r: (r.get("model_label"), r.get("condition"))).items(), key=lambda kv: str(kv[0])):
        out["by_model_condition"][f"{model}|{condition}"] = {
            "overall_accuracy": entity_accuracy(subset).as_dict(),
            "role_accuracy": role_accuracy(subset).as_dict(),
            "chance_level": chance_level(subset).as_dict(),
            "status_counts": status_counts(subset),
            "by_referent_type": metric_table(subset, "gold_role", entity_accuracy),
            "by_referent_changed": metric_table(subset, "referent_changed", entity_accuracy),
            "by_speaker_changed": metric_table(subset, "speaker_changed", entity_accuracy),
            "by_role_changed": metric_table(subset, "referent_role_changed", entity_accuracy),
            "by_distractor_present": metric_table(subset, "distractor_present", entity_accuracy),
            "by_turn_distance": metric_table(subset, "turn_distance", entity_accuracy),
            "by_dataset": metric_table(subset, "dataset", entity_accuracy),
            "distractor_error_rate": distractor_error_rate(subset).as_dict(),
            "role_confusion": confusion_matrix(subset),
            "entity_confusion": entity_confusion(subset),
            "pair_consistency": pair_consistency(subset),
            "n_rows": len(subset),
            "n_clusters": len({r.get("conversation_id") for r in subset}),
        }
    for model, subset in group_by(rows, "model_label").items():
        conditions = {r.get("condition") for r in subset}
        if "full_mcq" in conditions and "target_only_mcq" in conditions:
            out["context_benefit"][str(model)] = paired_condition_difference(subset, "full_mcq", "target_only_mcq").as_dict()
    return out
