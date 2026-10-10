# datasets/

독립 창작 데이터. 말뭉치 원문이 없으므로 Git에서 추적한다.

| 경로 | 내용 | 상태 |
|---|---|---|
| `scenarios/pilot_v0.jsonl` | 시나리오 명세 10개(S01~S07 controlled, N01~N03 naturalistic)와 변형 선언 | 작성 완료 |
| `pilot_v0/dialogues.jsonl` | 대화 레코드 20개. 정답 정보 없음 | 후보(candidate) |
| `pilot_v0/labels.jsonl` | 정답·anchor·distractor·조작 선언·작성 근거 | 작성자 의도값, 검수 전 |
| `pilot_v0/review.md` | 사람 검수용 문서(`koimplicit review-doc`) | 생성물 |
| `pilot_v0/pairs.json` | 변형 pair 대조(`koimplicit pairs`) | 생성물 |
| `pilot_v0/validation_report.json` | 자동 검증(`koimplicit validate`) | 생성물 |

## 출처와 작성 방식

- 작성자: Claude Fable 5.1, Claude Code 세션에서 직접 작성(외부 API 호출 없음). `generation_metadata`에 기록.
- 참고: 공개 문헌의 언어 현상(주어 생략, 전문 어미, 호격, 높임, 인접쌍)과 실험 설계 원칙만. 말뭉치 문장 미사용.
- 인명은 흔한 가명이며 실존 인물과 무관하다.

## 사용 규칙

- `labels.jsonl`과 `review.md`의 "작성자 라벨"은 모델 입력·검수 화면에 넣지 않는다.
- 검수 완료(`annotation_status=accepted`) 전에는 공식 평가셋이 아니다.
- 수정은 새 버전 폴더(`pilot_v1`, `controlled_v1`)로 한다. 동결된 버전은 바꾸지 않는다.
- 공개 라이선스는 팀이 정한다. 정하기 전에는 저장소 공개 범위 설정을 따른다.
