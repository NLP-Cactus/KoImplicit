# Pilot v1 결과표 (2026-10-14, 구독 CLI 실행 · 개발 점검용)

표본 17개(accepted), cluster = scenario 10개. 구독 CLI(claude -p, codex exec)로 돌린 결과라 에이전트 컨텍스트가 붙어 있으며 논문 수치가 아니다.

## 1. 전체 정확도

| 모델 | 조건 | 정확도 | 95% CI (scenario bootstrap) | 무작위 기대 | 파싱 상태 |
|---|---|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | full_mcq | 0.76 (13/17) | [0.53, 0.94] | 0.32 | ok 17, invalid 0, abstain 0, missing 0 |
| claude_code_cli (claude-haiku-5-5) | target_only_mcq | 0.47 (8/17) | [0.29, 0.64] | 0.32 | ok 17, invalid 0, abstain 0, missing 0 |
| codex_cli (gpt-6.1-sol) | full_mcq | 1.00 (17/17) | [1.00, 1.00] | 0.32 | ok 17, invalid 0, abstain 0, missing 0 |
| codex_cli (gpt-6.1-sol) | target_only_mcq | 0.76 (13/17) | [0.54, 1.00] | 0.32 | ok 17, invalid 0, abstain 0, missing 0 |

## 2. 문맥 이득 (full − target_only, 같은 표본 paired)

| 모델 | 차이 | 95% CI | 토큰 |
|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | 0.29 (5/17) | [+0.07, +0.44] | in 251,317 / out 476 |
| codex_cli (gpt-6.1-sol) | 0.24 (4/17) | [+0.00, +0.46] | in 590,917 / out 668 |

## 3. 휴리스틱 기준선

| 기준선 | 정확도 | 매핑 실패 |
|---|---|---|
| most_recent_entity | 0.59 (10/17) | 5/17 |
| current_speaker | 0.12 (2/17) | 0/17 |
| current_addressee | 0.18 (3/17) | 0/17 |

## 4. 역할별 (목표 발화 화자 기준)

| 모델 | 조건 | speaker | addressee | third_party |
|---|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | full_mcq | 1.00 (2/2) | 0.75 (3/4) | 0.73 (8/11) |
| claude_code_cli (claude-haiku-5-5) | target_only_mcq | 1.00 (2/2) | 0.50 (2/4) | 0.36 (4/11) |
| codex_cli (gpt-6.1-sol) | full_mcq | 1.00 (2/2) | 1.00 (4/4) | 1.00 (11/11) |
| codex_cli (gpt-6.1-sol) | target_only_mcq | 1.00 (2/2) | 1.00 (4/4) | 0.64 (7/11) |

## 5. 참조 대상 전환 (referent_changed)

| 모델 | 조건 | False | None | True |
|---|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | full_mcq | 0.67 (8/12) | 1.00 (2/2) | 1.00 (3/3) |
| claude_code_cli (claude-haiku-5-5) | target_only_mcq | 0.33 (4/12) | 1.00 (2/2) | 0.67 (2/3) |
| codex_cli (gpt-6.1-sol) | full_mcq | 1.00 (12/12) | 1.00 (2/2) | 1.00 (3/3) |
| codex_cli (gpt-6.1-sol) | target_only_mcq | 0.67 (8/12) | 1.00 (2/2) | 1.00 (3/3) |

## 6. 화자 전환 (speaker_changed)

| 모델 | 조건 | False | None | True |
|---|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | full_mcq | 1.00 (1/1) | 1.00 (2/2) | 0.71 (10/14) |
| claude_code_cli (claude-haiku-5-5) | target_only_mcq | 1.00 (1/1) | 1.00 (2/2) | 0.36 (5/14) |
| codex_cli (gpt-6.1-sol) | full_mcq | 1.00 (1/1) | 1.00 (2/2) | 1.00 (14/14) |
| codex_cli (gpt-6.1-sol) | target_only_mcq | 1.00 (1/1) | 1.00 (2/2) | 0.71 (10/14) |

## 7. 최근성 경쟁 개체 (distractor_present)

| 모델 | 조건 | False | True |
|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | full_mcq | 0.80 (12/15) | 0.50 (1/2) |
| claude_code_cli (claude-haiku-5-5) | target_only_mcq | 0.47 (7/15) | 0.50 (1/2) |
| codex_cli (gpt-6.1-sol) | full_mcq | 1.00 (15/15) | 1.00 (2/2) |
| codex_cli (gpt-6.1-sol) | target_only_mcq | 0.80 (12/15) | 0.50 (1/2) |

## 8. 문맥 필요성 (사람 Local 판정 기반)

| 모델 | 조건 | None | conflict | discourse_dependent | locally_recoverable |
|---|---|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | full_mcq | 1.00 (1/1) | 0.67 (2/3) | 0.73 (8/11) | 1.00 (2/2) |
| claude_code_cli (claude-haiku-5-5) | target_only_mcq | 1.00 (1/1) | 0.33 (1/3) | 0.36 (4/11) | 1.00 (2/2) |
| codex_cli (gpt-6.1-sol) | full_mcq | 1.00 (1/1) | 1.00 (3/3) | 1.00 (11/11) | 1.00 (2/2) |
| codex_cli (gpt-6.1-sol) | target_only_mcq | 1.00 (1/1) | 0.67 (2/3) | 0.73 (8/11) | 1.00 (2/2) |

## 9. 거리 (정답 마지막 언급 → 목표, 턴)

| 모델 | 조건 | 0 | 1 | 3 | 5 | None |
|---|---|---|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | full_mcq | 1.00 (2/2) | 0.67 (4/6) | 0.67 (2/3) | 1.00 (1/1) | 0.80 (4/5) |
| claude_code_cli (claude-haiku-5-5) | target_only_mcq | 1.00 (2/2) | 0.00 (0/6) | 0.67 (2/3) | 1.00 (1/1) | 0.60 (3/5) |
| codex_cli (gpt-6.1-sol) | full_mcq | 1.00 (2/2) | 1.00 (6/6) | 1.00 (3/3) | 1.00 (1/1) | 1.00 (5/5) |
| codex_cli (gpt-6.1-sol) | target_only_mcq | 1.00 (2/2) | 0.50 (3/6) | 0.67 (2/3) | 1.00 (1/1) | 1.00 (5/5) |

## 10. distractor 선택률 / pair 일관성

| 모델 | 조건 | distractor 선택률 | pair 둘 다 정답 | 기준만 정답 | 변형만 정답 | n pairs |
|---|---|---|---|---|---|---|
| claude_code_cli (claude-haiku-5-5) | full_mcq | 0.50 (1/2) | 4 | 3 | 0 | 7 |
| claude_code_cli (claude-haiku-5-5) | target_only_mcq | 0.00 (0/2) | 1 | 2 | 2 | 7 |
| codex_cli (gpt-6.1-sol) | full_mcq | 0.00 (0/2) | 7 | 0 | 0 | 7 |
| codex_cli (gpt-6.1-sol) | target_only_mcq | 0.50 (1/2) | 3 | 3 | 0 | 7 |

## 11. 표본별 결과 (full_mcq)

| 표본 | gold | claude_code_cli | codex_cli |
|---|---|---|---|
| N02-01 | P3 (addressee) | X P2 | O P3 |
| N03-01 | T2 (third_party) | X T1 | O T2 |
| S01-base | T1 (third_party) | O T1 | O T1 |
| S01-distractor | T1 (third_party) | O T1 | O T1 |
| S01-shift | T2 (third_party) | O T2 | O T2 |
| S02-addressee | P2 (addressee) | O P2 | O P2 |
| S02-third | T1 (third_party) | O T1 | O T1 |
| S03-vocative | P3 (addressee) | O P3 | O P3 |
| S04-base | T2 (third_party) | O T2 | O T2 |
| S04-distractor | T2 (third_party) | X T1 | O T2 |
| S05-addressee | P2 (addressee) | O P2 | O P2 |
| S05-speaker | P1 (speaker) | O P1 | O P1 |
| S06-d1 | T1 (third_party) | O T1 | O T1 |
| S06-d5 | T1 (third_party) | O T1 | O T1 |
| S07-hearsay | T1 (third_party) | O T1 | O T1 |
| S07-plain | T1 (third_party) | X P2 | O T1 |
| S07-speaker | P2 (speaker) | O P2 | O P2 |

표기: O/X 뒤는 모델이 고른 인물(원래 ID). 중립 ID는 gold의 id_map으로 되돌렸다.
