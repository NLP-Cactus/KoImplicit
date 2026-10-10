# 프롬프트 (버전 고정)

| 파일 | 용도 | slot |
|---|---|---|
| `mcq_v1.json` | Multiple-choice 주평가. `full_mcq`, `target_only_mcq` 공통 | dialogue, target_utterance, target_marker, target_speaker_label, candidates, output_schema |
| `qa_v1.json` | Direct Answer 확장 조건 `full_qa` | 위에서 candidates 제외 |
| `generate_v1.json` | 시나리오 → 대화 초안 생성 | scenario, variant, constraints, output_schema |

`koimplicit check-prompts`가 slot 선언과 template의 일치를 검사한다. 평가 프롬프트에는 정답·역할·anchor 정보가 들어가지 않는다(`koimplicit validate`의 누수 검사 대상). 문구를 바꾸면 새 버전 파일을 만들고 실행 기록의 prompt sha256으로 구분한다. 생성 프롬프트는 의도한 지시 대상을 포함하지만 그 결과의 gold는 검수 전까지 후보값이다.
