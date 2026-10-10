# 주석 작업 공간 (Git 제외)

`controlled/<dataset>/`에 `koimplicit annotate`의 파일을 둔다.

| 파일 | 만드는 단계 | 내용 |
|---|---|---|
| `id_map.json` | `annotate sheets` | review_id → sample_id 대응표. 검수자에게 주지 않는다 |
| `sheet_local_<검수자>.csv` | `annotate sheets --condition local` | 목표 발화와 후보만. Full 정답을 보기 전에 먼저 판정한다 |
| `sheet_full_<검수자>.csv` | `annotate sheets --condition full` | 전체 문맥. 열: naturalness_1to5, referent_id, addressee_id(3인 대화만), context_sufficient(yes/no), ambiguity(unambiguous/ambiguous/uncertain), notes. 역할·anchor는 묻지 않는다 |
| `agreement.json` | `annotate agreement` | 조건별·필드별 percent agreement, Cohen's κ(정의 불가면 None), 결측 수, 자연스러움 차이, 불일치 목록 |
| `pair_sheet.csv` | `annotate pair-sheet` | 독립 판정 뒤 두 버전을 나란히 보고 pair_valid, only_claimed_changed, gold_change_as_intended 판정 |
| `adjudication.csv` | 조정자가 작성 | sample_id, adjudicator, decision(accept/reject), final_referent_id, final_ambiguity, final_addressee_id, reason |
| `labels_adjudicated.jsonl` | `annotate adjudicate` | 최종 라벨. 최초 판정은 `validation_metadata.annotator_votes`에, 작성자 값 변경은 `author_values_overridden`에, Local 기반 분류는 `context_need`에 기록 |

채택된 라벨은 새 버전 폴더(`datasets/pilot_v1/labels.jsonl`)로 복사해 `dialogues.jsonl`과 함께 동결한다. 검수자는 판정 전에 `labels.jsonl`, `review.md`, `pairs.json`을 보지 않는다. 청자 판정 규칙은 `docs/데이터셋_구축방법.md` 2절을 따른다. anchor는 작성자 선언 변수라 검수하지 않는다.

독립 창작 데이터셋의 검수 원본(시트·id_map·adjudication)은 동결할 때 `datasets/<version>/annotations/`로 복사해 추적한다(Pilot v1: 임동건·정택준). 이 폴더는 작업 중인 사본이다.
