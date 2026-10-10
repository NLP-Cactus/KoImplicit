"""cluster bootstrap. 자연 자료는 conversation, 통제 자료는 family 단위로 재표집한다.

statistic은 행 목록을 받아 float 또는 None을 돌려주는 함수다. Metric을 돌려주는
함수를 넘기면 value를 꺼내 쓴다. 조건 차이나 모델 차이도 같은 재표집에서 계산하려면
두 조건의 행을 한 목록에 넣고 statistic 안에서 나누어 계산한다
(condition_difference 참고).
"""

from __future__ import annotations

import random
from typing import Callable, Iterable

from .metrics import Metric, is_correct


def _value(result) -> float | None:
    if isinstance(result, Metric):
        return result.value
    return result


def percentile(sorted_values: list[float], q: float) -> float:
    """선형 보간 percentile. q는 0~1."""
    if not sorted_values:
        raise ValueError("empty sample")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = q * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def cluster_bootstrap(
    rows: Iterable[dict],
    cluster_key: str,
    statistic: Callable[[list[dict]], float | Metric | None],
    n_boot: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> dict:
    """cluster를 복원 추출하고 그 안의 행을 전부 가져와 statistic을 다시 계산한다.

    반환: point, ci_low, ci_high, n_rows, n_clusters, n_boot, n_undefined.
    n_undefined는 재표집에서 statistic이 None이 된 횟수다(분모 0 등).
    """
    rows = list(rows)
    clusters: dict = {}
    for r in rows:
        if cluster_key not in r:
            raise KeyError(f"row without cluster key {cluster_key!r}: {r.get('item_id')}")
        clusters.setdefault(r[cluster_key], []).append(r)
    cluster_ids = sorted(clusters, key=str)
    point = _value(statistic(rows))
    if not cluster_ids:
        return {"point": point, "ci_low": None, "ci_high": None, "n_rows": 0, "n_clusters": 0, "n_boot": 0, "n_undefined": 0}
    rng = random.Random(seed)
    samples: list[float] = []
    undefined = 0
    for _ in range(n_boot):
        drawn = [cluster_ids[rng.randrange(len(cluster_ids))] for _ in cluster_ids]
        # 같은 cluster가 여러 번 뽑히면 행이 중복된다. paired 통계가 중복 추출을 잃지 않도록 추출 회차를 붙인다.
        resampled = [{**row, "_draw": k} for k, cid in enumerate(drawn) for row in clusters[cid]]
        value = _value(statistic(resampled))
        if value is None:
            undefined += 1
        else:
            samples.append(value)
    samples.sort()
    if samples:
        ci_low = percentile(samples, alpha / 2)
        ci_high = percentile(samples, 1 - alpha / 2)
    else:
        ci_low = ci_high = None
    return {
        "point": point,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n_rows": len(rows),
        "n_clusters": len(cluster_ids),
        "n_boot": n_boot,
        "n_undefined": undefined,
    }


def condition_difference(metric: Callable[[list[dict]], Metric], condition_a: str, condition_b: str, key: str = "condition"):
    """같은 재표집 안에서 metric(a) - metric(b)를 계산하는 statistic을 만든다."""

    def statistic(rows: list[dict]) -> float | None:
        a = metric([r for r in rows if r.get(key) == condition_a]).value
        b = metric([r for r in rows if r.get(key) == condition_b]).value
        if a is None or b is None:
            return None
        return a - b

    return statistic


def model_difference(metric: Callable[[list[dict]], Metric], model_a: str, model_b: str):
    return condition_difference(metric, model_a, model_b, key="model_label")


def paired_item_difference(condition_a: str, condition_b: str):
    """같은 item의 두 조건 정답 차이 평균. 두 조건 모두 있는 item만 쓴다."""

    def statistic(rows: list[dict]) -> float | None:
        by_item: dict = {}
        for r in rows:
            if r.get("condition") in (condition_a, condition_b):
                by_item.setdefault((r["item_id"], r.get("_draw")), {})[r["condition"]] = r
        diffs = [
            int(is_correct(v[condition_a])) - int(is_correct(v[condition_b]))
            for v in by_item.values() if condition_a in v and condition_b in v
        ]
        return sum(diffs) / len(diffs) if diffs else None

    return statistic
