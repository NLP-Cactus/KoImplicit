# 주석 작업 공간 (Git 제외)

`controlled/<dataset>/`에 `koimplicit annotate`의 파일을 둔다.

| 파일 | 만드는 단계 | 내용 |
|---|---|---|
| `sheet_<검수자>.csv` | `annotate sheets` | 검수자별 독립 판정 시트. 정답·anchor·작성 근거는 없다. 열: naturalness_1to5, referent_id, referent_role, context_sufficient(yes/no), ambiguity(unambiguous/ambiguous/uncertain), previous_referent_id, previous_referent_turn, notes |
| `agreement.json` | `annotate agreement` | 필드별 percent agreement, Cohen's κ, 자연스러움 차이, 불일치 목록 |
| `pair_sheet.csv` | `annotate pair-sheet` | 독립 판정 뒤 두 버전을 나란히 보고 pair_valid, only_claimed_changed, gold_change_as_intended 판정 |
| `adjudication.csv` | 조정자가 작성 | sample_id, adjudicator, decision(accept/reject), final_referent_id, final_ambiguity, reason |
| `labels_adjudicated.jsonl` | `annotate adjudicate` | 최종 라벨. 최초 판정은 `validation_metadata.annotator_votes`에 보존 |

채택된 라벨은 새 버전 폴더(`datasets/pilot_v1/labels.jsonl` 등)로 복사해 동결한다. 검수자는 판정 전에 `labels.jsonl`과 `review.md`의 작성자 라벨을 보지 않는다.
