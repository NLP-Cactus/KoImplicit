"""provider adapter 레지스트리. 실제 API provider는 모델 선정 뒤 한 파일씩 추가한다.

현재는 네트워크를 쓰지 않는 dry adapter만 있다. 요청 생성·기록·캐시를 비용 없이 점검하는 용도다.
"""

from __future__ import annotations

from importlib import import_module

PROVIDERS = {
    "dry": "koimplicit.providers.dry",
}


def get_adapter(name: str, **options):
    if name not in PROVIDERS:
        raise KeyError(f"unknown provider {name!r}; available: {sorted(PROVIDERS)}")
    module = import_module(PROVIDERS[name])
    return module.Adapter(**options)
