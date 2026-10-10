# KoImplicit

한국어 다중턴 대화에서 화자·청자·담화 대상 전환에 따른 LLM의 생략 주어 추적 능력을 평가하는 연구 저장소다.

**데이터 원칙(2026-10-10 확정)**: 국립국어원 말뭉치를 사용하지 않는다. 모든 평가 대화는 독립 설계한 시나리오로 새로 작성하고, 생성 출처·검수 이력을 기록한다. 자세한 절차는 [docs/데이터셋_구축방법.md](docs/데이터셋_구축방법.md)를 따른다.

현재 상태: **Pilot v0 후보 20개**(`datasets/pilot_v0/`)가 작성되어 있고 자동 검증을 통과했다. 모두 `annotation_status=candidate`이며 사람 검수 전이다. 외부 모델 평가는 아직 수행하지 않았고, mock provider로 파이프라인만 검증했다.

## 설치와 검증

Python 3.10 이상, 의존성은 `pydantic`뿐이다. 실제 API provider는 표준 라이브러리 `urllib`로 호출한다.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m koimplicit status
.venv\Scripts\python -m unittest discover -s tests
```

## 파이프라인 실행 순서

```powershell
# 1. 시나리오 명세 확인
python -m koimplicit scenarios --file datasets/scenarios/pilot_v0.jsonl --list

# 2. (선택) 시나리오로 대화 초안 생성. API 키 없이 mock으로 형식 검증 가능
python -m koimplicit generate --scenarios datasets/scenarios/pilot_v0.jsonl --model mock --out data/generated/mock_test
python -m koimplicit generate --scenarios datasets/scenarios/pilot_v0.jsonl --model claude_haiku_5_5 --out data/generated/haiku_v1   # ANTHROPIC_API_KEY 필요

# 3. 자동 검증 (스키마·턴/화자·gold 식별성·중복·불균형·pair 연결·gold 누수·출처/검수 상태)
python -m koimplicit validate --dataset datasets/pilot_v0 --scenarios datasets/scenarios/pilot_v0.jsonl --out datasets/pilot_v0/validation_report.json --strict

# 4. 변형 pair 대조: 주장한 조작 vs 실제로 달라진 변수
python -m koimplicit pairs --dataset datasets/pilot_v0 --out datasets/pilot_v0/pairs.json

# 5. 사람이 읽는 Pilot Review 문서
python -m koimplicit review-doc --dataset datasets/pilot_v0 --scenarios datasets/scenarios/pilot_v0.jsonl --out datasets/pilot_v0/review.md

# 6. 사람 검수 (2명 독립 → 일치도 → pair 타당성 → 조정). 검수 파일은 Git 제외
python -m koimplicit annotate sheets --dataset datasets/pilot_v0 --annotators 검수자1,검수자2 --out annotations/controlled/pilot_v0
python -m koimplicit annotate agreement --sheets annotations/controlled/pilot_v0/sheet_검수자1.csv annotations/controlled/pilot_v0/sheet_검수자2.csv --out annotations/controlled/pilot_v0/agreement.json
python -m koimplicit annotate pair-sheet --dataset datasets/pilot_v0 --out annotations/controlled/pilot_v0/pair_sheet.csv
python -m koimplicit annotate adjudicate --dataset datasets/pilot_v0 --sheets annotations/controlled/pilot_v0/sheet_검수자1.csv annotations/controlled/pilot_v0/sheet_검수자2.csv --decisions annotations/controlled/pilot_v0/adjudication.csv --out annotations/controlled/pilot_v0/labels_adjudicated.jsonl

# 7. 평가 입력(items, 정답 없음)과 정답(gold) 분리. 기본은 accepted만 포함
python -m koimplicit payload --dataset datasets/pilot_v0 --out data/processed/pilot_v0 --include-unreviewed   # pilot 점검용

# 8. 벤치마크 실행 (mock / anthropic / openai). 조건: full_mcq, target_only_mcq, full_qa
python -m koimplicit benchmark --items data/processed/pilot_v0/items.jsonl --gold data/processed/pilot_v0/gold.jsonl --model mock --conditions full_mcq,target_only_mcq --run-dir results/runs/20261010_mock_pilot_v0
python -m koimplicit benchmark --items data/processed/pilot_v0/items.jsonl --gold data/processed/pilot_v0/gold.jsonl --model mock --conditions full_qa --prompt prompts/qa_v1.json --run-dir results/runs/20261010_mock_pilot_v0_qa

# 9. 휴리스틱 기준선 (most_recent_entity, current_speaker, current_addressee)
python -m koimplicit baselines --items data/processed/pilot_v0/items.jsonl --gold data/processed/pilot_v0/gold.jsonl --out results/analysis/pilot_v0_baselines

# 10. 지표 재계산 + scenario 단위 cluster bootstrap
python -m koimplicit metrics --normalized results/runs/20261010_mock_pilot_v0/normalized.jsonl --gold data/processed/pilot_v0/gold.jsonl --n-boot 2000 --out results/analysis/pilot_v0_mock_metrics.json
```

실제 모델을 쓰려면 `configs/models.json`에 모델 라벨을 두고 환경 변수(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)를 설정한다. 키는 `.env`에만 두고 커밋하지 않는다. `openai_candidate`의 `model_id`는 비어 있으므로 팀이 정한 뒤 채운다.

## 폴더 구조

```text
KoImplicit/
├── datasets/                      # 독립 창작 데이터(Git 추적)
│   ├── scenarios/pilot_v0.jsonl   # 시나리오 명세(조건·의도·변형 선언)
│   └── pilot_v0/                  # dialogues.jsonl(모델 노출 가능) + labels.jsonl(정답·메타, 비노출)
│       ├── review.md              # 사람 검수용 문서
│       ├── pairs.json             # 변형 pair 대조 결과
│       └── validation_report.json
├── src/koimplicit/
│   ├── schema.py                  # Pydantic 스키마, 파생 변수(역할·shift·거리·distractor)
│   ├── scenarios.py / generate.py / variations.py
│   ├── validate.py / annotation.py / payload.py
│   ├── runner.py / normalize.py / metrics.py / bootstrap.py / baselines.py / benchmark.py
│   └── providers/                 # dry, mock, anthropic, openai_chat
├── prompts/                       # mcq_v1, qa_v1, generate_v1
├── configs/                       # study.json(범위·변수·경로), models.json(모델별 설정·단가)
├── docs/                          # 데이터셋_구축방법.md(현행), 설계 이력
├── data/processed/                # payload 출력(Git 제외)
├── annotations/controlled/        # 검수 시트·조정(Git 제외)
└── results/                       # runs(실행 기록), analysis(Git 제외)
```

## 핵심 규칙

- 역할(speaker / addressee / third_party)은 항상 **목표 발화의 화자 기준**으로 계산한다.
- `speaker_changed`와 `referent_changed`는 별개 변수다. anchor(이전 참조 대상)를 확인할 수 없으면 `None`이지 `False`가 아니다.
- 다자 대화에서 청자를 확정할 수 없으면 `addressee_id`를 비우고, 정답이 불명확하면 `gold_referent_id`를 비운다(S03-novocative가 그 예다).
- `dialogues.jsonl`에는 정답·anchor·distractor·작성 근거가 없다. `payload`가 만드는 `items.jsonl`도 마찬가지이며 `validate`가 누수를 검사한다.
- `annotation_status=accepted`가 아닌 표본은 공식 평가셋에 들어가지 않는다.
- 같은 시나리오의 변형은 독립 표본이 아니다. bootstrap과 pair 지표는 `scenario_id`를 cluster로 쓴다.

## 설계 문서

- 현행: [docs/데이터셋_구축방법.md](docs/데이터셋_구축방법.md), [AGENTS.md](AGENTS.md)
- 이력: [최종설계안.md](최종설계안.md) v2.0(말뭉치 기반 설계. 연구 질문·지표 정의는 유지, 데이터 확보 절차는 폐기), [독립검증_2026-10.md](독립검증_2026-10.md), `docs/`의 이전 가이드
