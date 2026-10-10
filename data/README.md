# 데이터 작업 공간 (Git 제외)

- `processed/<dataset>/`: `koimplicit payload`가 만든 평가 입력 `items.jsonl`(정답 없음), `gold.jsonl`, `payload_manifest.json`.
- `generated/<run>/`: `koimplicit generate`가 만든 대화 초안과 `generation_log.jsonl`. 검수 후 채택분만 `datasets/`로 옮긴다.

말뭉치 원본은 더 이상 이 프로젝트에서 쓰지 않는다. 추적되는 데이터는 `datasets/`에 있다.
