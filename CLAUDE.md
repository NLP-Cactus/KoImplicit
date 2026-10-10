# KoImplicit — Claude 작업 지침

작업 전에 [AGENTS.md](AGENTS.md)를 읽고 공통 규칙을 따른다. 두 파일의 규칙을 중복 관리하지 않으며 공통 규칙 변경은 AGENTS.md에 반영한다.

우선 적용할 사항:

- 커밋 메시지·PR·새 코드/문서에 자동 AI 서명, 로봇 이모지, 생성 도구 홍보 문구를 넣지 않는다.
- Claude를 비롯한 AI 명의의 자동 `Co-authored-by` trailer를 붙이지 않는다.
- 사람의 정당한 저작자·공동 작성자·라이선스·출처 표시는 유지한다.
- 연구 방법과 실험 기록의 AI 활용 사실(데이터 생성 모델, 평가 모델)은 보존한다.
- 현재 실행 기준은 [docs/데이터셋_구축방법.md](docs/데이터셋_구축방법.md) v2.1이다. 연구 질문·지표 정의는 [최종설계안.md](최종설계안.md) v2.0을 따른다.
- 국립국어원 말뭉치는 사용하지 않는다. 말뭉치를 읽는 코드·문장·ID를 추가하지 않는다.
- Pilot v0 후보 20개는 사용자 요청으로 제작했다. 추가 문항·대규모 생성은 사용자의 후속 요청 뒤에 한다.
- 실제 데이터·주석·모델 출력(`data/`, `annotations/`, `results/`)을 Git에 강제 추가하지 않는다. `datasets/`는 추적한다.

기본 검증:

```text
python -m koimplicit status
python -m unittest discover -s tests
python -m koimplicit validate --dataset datasets/pilot_v0 --scenarios datasets/scenarios/pilot_v0.jsonl --strict --quiet
```

검사하지 않은 사항을 통과했다고 쓰지 않는다. mock 실행과 실제 모델 평가를 구별해서 보고한다. 사용자의 기존 변경과 연구 기록을 보존한다.
