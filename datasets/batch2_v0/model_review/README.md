# batch2_v0 모델 검수 (조정·동결 전, 참고용)

사람 검수자를 구할 수 없어 서로 다른 계열의 모델 2개가 사람과 같은 시트를 독립적으로 채웠다. **사람 검수가 아니며 gold를 확정하지 않는다.** 조정·동결(`batch2_v1`)은 아직 하지 않았다.

| 검수자 | 실행 | 조건 |
|---|---|---|
| `sonnet` = claude-sonnet-5-5 | `claude -p`(Claude Code 구독 CLI, effort medium, 시스템 프롬프트 대체) | Local → Full |
| `gpt` = gpt-6.1-sol | `codex exec --json`(ChatGPT 구독 CLI, reasoning low, 읽기 전용 샌드박스) | Local → Full |

명령: `koimplicit annotate model-fill --sheets <sheet> --out <sheet> --condition local|full --model claude_code_cli_sonnet|codex_cli` (2026-10-14).

## 파일

- `controlled_*`: 통제 80개(A·B·C·D 템플릿). `naturalistic_*`: Codex 생성 20개.
- `*_id_map.json`: review_id → sample_id. `*_sheet_<cond>_<judge>.csv`: 채워진 시트. `*.responses.jsonl`: 원문 응답과 근거.
- `*_agreement.json`: 두 모델의 일치도. `review_summary.json`: 작성자 gold와의 대조와 조정 미리보기(표본별 상태).

## 결과 요약

| 세트 | Full 인물 일치(둘 다 확정) | Full 확정 여부 κ | Local 확정 여부 κ | 작성자 gold와 두 모델 모두 일치 |
|---|---|---|---|---|
| controlled 80 | 0.96 (κ 0.93, n=68) | 0.63 | 0.72 | 65 / 80 |
| naturalistic 20 | 1.00 (κ 1.0, n=20) | 단일 범주 | 0.24 | 20 / 20 |

통제 80개의 조정 미리보기(규칙: 두 모델이 작성자 gold와 모두 일치할 때만 채택): 채택 가능 65, 의도대로 확정 불가(gold 없음) 5, 두 모델 모두 확정 불가 1(A4-distractor), 불일치 9.

불일치·문제 표본: A4-distractor, B2-third, B2-third_distractor, B3-third_distractor, B5-third, D1·D2·D3·D5-third_in_3p, D4-adjacency. 특히 D 템플릿 `third_in_3p`("민석아, 요즘 계속 아픈 것 같지 않아?" 류)는 청자 본인에 대한 질문으로도 읽혀 변형 자체를 재설계해야 한다. B의 평가 표현("진짜 많이 늘었다", "너무 성급했어")은 제3자 변형에서 화자·청자로 읽히는 경우가 있다.

## 한계

- 모델 검수는 사람 검수의 대체물이다. 채택 시 `validation_metadata.human_verified=false`와 검수 모델을 기록해야 한다.
- 검수 모델(sonnet, gpt-6.1-sol)이 평가 대상이 되면 순환이 생긴다. 평가는 Haiku 등 검수에 쓰지 않은 모델을 주로 쓰고, 겹치는 모델은 참고로만 보고한다.
- Local 판정에서 gpt는 의지 어미(-ㄹ게, -려고)를 근거로 화자 확정을 더 자주 했다(naturalistic κ 0.24). 어느 쪽 기준을 쓸지 조정 단계에서 정해야 한다.
