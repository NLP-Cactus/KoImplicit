"""provider adapter 레지스트리.

- dry: 네트워크 없음, 응답 없음(요청 기록만).
- mock: 네트워크 없음, 결정적 응답. API 키 없이 전체 파이프라인을 검증할 때 쓴다.
- anthropic / openai: 표준 라이브러리 urllib로 호출. 키는 환경 변수에서만 읽는다.
"""

from __future__ import annotations

from importlib import import_module

PROVIDERS = {
    "dry": "koimplicit.providers.dry",
    "mock": "koimplicit.providers.mock",
    "anthropic": "koimplicit.providers.anthropic",
    "openai": "koimplicit.providers.openai_chat",
}


def get_adapter(name: str, **options):
    if name not in PROVIDERS:
        raise KeyError(f"unknown provider {name!r}; available: {sorted(PROVIDERS)}")
    module = import_module(PROVIDERS[name])
    return module.Adapter(**options)
