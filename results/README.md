# 결과 작업 공간 (Git 제외)

- `runs/<run_id>/`: `koimplicit benchmark`의 기록. `config.json`(model_id·prompt/items 해시·조건·날짜), `requests.jsonl`, `responses.jsonl`(원문 응답·토큰·지연·재시도), `normalized.jsonl`, `per_sample.csv`, `metrics.json`, `cache/`.
- `analysis/`: `koimplicit metrics`(bootstrap 포함)와 `koimplicit baselines` 출력.
- `figures/`: 결과 확인 뒤 만드는 그림.

run_id는 `{YYYYMMDD}_{model_label}_{dataset}` 형식을 권장한다. mock 실행 결과를 실제 모델 결과처럼 보고하지 않는다.
