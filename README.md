# KoImplicit

한국어 다중턴 대화에서 화자·청자·담화 대상 전환에 따른 LLM의 생략 주어 추적 능력을 평가하는 연구 저장소다.

**데이터 원칙(2026-10-10 확정)**: 국립국어원 말뭉치를 사용하지 않는다. 모든 평가 대화는 독립 설계한 시나리오로 새로 작성하고, 생성 출처·검수 이력을 기록한다. 절차는 [docs/데이터셋_구축방법.md](docs/데이터셋_구축방법.md)를 따른다.

현재 상태: **Pilot v0 후보 20개**(`datasets/pilot_v0/`)가 자동 검증을 통과했고 모두 `annotation_status=candidate`(사람 검수 전)다. 외부 모델 평가는 아직 수행하지 않았고 mock provider로 파이프라인만 검증했다.

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

# 3. 자동 검증과 변형 pair 대조 (오류·문제가 있으면 종료 코드 1)
python -m koimplicit validate --dataset datasets/pilot_v0 --scenarios datasets/scenarios/pilot_v0.jsonl --out datasets/pilot_v0/validation_report.json --strict
python -m koimplicit pairs --dataset datasets/pilot_v0 --out datasets/pilot_v0/pairs.json

# 4. 사람이 읽는 Pilot Review 문서
python -m koimplicit review-doc --dataset datasets/pilot_v0 --scenarios datasets/scenarios/pilot_v0.jsonl --out datasets/pilot_v0/review.md

# 5. 사람 검수 (검수 파일은 Git 제외). sample_id는 시트에 나오지 않고 id_map.json에만 있다
python -m koimplicit annotate sheets --dataset datasets/pilot_v0 --annotators 검수자1,검수자2 --condition local --out annotations/controlled/pilot_v0   # Local 먼저
python -m koimplicit annotate sheets --dataset datasets/pilot_v0 --annotators 검수자1,검수자2 --condition full  --out annotations/controlled/pilot_v0
python -m koimplicit annotate agreement --sheets annotations/controlled/pilot_v0/sheet_full_검수자1.csv annotations/controlled/pilot_v0/sheet_full_검수자2.csv annotations/controlled/pilot_v0/sheet_local_검수자1.csv annotations/controlled/pilot_v0/sheet_local_검수자2.csv --out annotations/controlled/pilot_v0/agreement.json
python -m koimplicit annotate pair-sheet --dataset datasets/pilot_v0 --out annotations/controlled/pilot_v0/pair_sheet.csv
python -m koimplicit annotate adjudicate --dataset datasets/pilot_v0 --sheets annotations/controlled/pilot_v0/sheet_full_검수자1.csv annotations/controlled/pilot_v0/sheet_full_검수자2.csv annotations/controlled/pilot_v0/sheet_local_검수자1.csv annotations/controlled/pilot_v0/sheet_local_검수자2.csv --decisions annotations/controlled/pilot_v0/adjudication.csv --out annotations/controlled/pilot_v0/labels_adjudicated.jsonl

# 6. 조정 라벨을 새 버전으로 동결한 뒤 공식 payload 생성 (accepted만 포함, 누수 검사 자동 실행)
mkdir datasets\pilot_v1; copy datasets\pilot_v0\dialogues.jsonl datasets\pilot_v1\; copy annotations\controlled\pilot_v0\labels_adjudicated.jsonl datasets\pilot_v1\labels.jsonl
python -m koimplicit validate --dataset datasets/pilot_v1 --strict
python -m koimplicit payload --dataset datasets/pilot_v1 --out data/processed/pilot_v1

#    검수 전 점검용 payload (결과는 공식 평가가 아니다)
python -m koimplicit payload --dataset datasets/pilot_v0 --out data/processed/pilot_v0 --include-unreviewed

# 7. 벤치마크 (mock / anthropic / openai). 조건: full_mcq, target_only_mcq, full_qa. 검수 전 표본은 --allow-unreviewed가 있어야 실행된다
python -m koimplicit benchmark --items data/processed/pilot_v0/items.jsonl --gold data/processed/pilot_v0/gold.jsonl --model mock --conditions full_mcq,target_only_mcq --run-dir results/runs/20261010_mock_pilot_v0 --allow-unreviewed
python -m koimplicit benchmark --items data/processed/pilot_v0/items.jsonl --gold data/processed/pilot_v0/gold.jsonl --model mock --conditions full_qa --prompt prompts/qa_v1.json --run-dir results/runs/20261010_mock_pilot_v0_qa --allow-unreviewed

# 8. 휴리스틱 기준선과 지표 재계산(+ scenario 단위 cluster bootstrap)
python -m koimplicit baselines --items data/processed/pilot_v0/items.jsonl --gold data/processed/pilot_v0/gold.jsonl --out results/analysis/pilot_v0_baselines
python -m koimplicit metrics --normalized results/runs/20261010_mock_pilot_v0/normalized.jsonl --gold data/processed/pilot_v0/gold.jsonl --n-boot 2000 --out results/analysis/pilot_v0_mock_metrics.json
```

실제 모델을 쓰려면 `configs/models.json`의 모델 라벨을 고르고 환경 변수를 설정한다. 코드는 `.env`를 읽지 않으므로 셸에서 직접 설정한다(`$env:ANTHROPIC_API_KEY="..."`). `openai_candidate`의 `model_id`는 팀이 정한 뒤 채운다. 같은 `--run-dir`는 같은 모델·프롬프트·입력일 때만 재사용되며 캐시로 재개된다.

## 폴더 구조

```text
KoImplicit/
├── datasets/                      # 독립 창작 데이터(Git 추적)
│   ├── scenarios/pilot_v0.jsonl   # 시나리오 명세(조건·의도·변형 선언)
│   └── pilot_v0/                  # dialogues.jsonl(모델 노출 가능) + labels.jsonl(정답·메타, 비노출)
│       ├── review.md / pairs.json / validation_report.json
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

- 역할(speaker / addressee / third_party)은 항상 **목표 발화의 화자 기준**으로 계산한다. 3인 대화의 청자는 호격·2인칭 표현 또는 인접쌍+내용으로 확정하고, 못 하면 비운다.
- `speaker_changed`와 `referent_changed`는 별개 변수다. anchor(이전 참조 대상)는 작성자가 시나리오에서 선언하며(경험자·대주어 포함 규칙), 없으면 `None`이지 `False`가 아니다. 검수자는 인물·청자·확정 여부·충분성·자연스러움만 판정한다.
- 정답이 불명확하면 `gold_referent_id`를 비운다(S03-novocative가 그 예다).
- `dialogues.jsonl`과 `items.jsonl`에는 정답·anchor·distractor·작성 근거가 없다. 후보는 중립 ID(E1..)로 노출되고 `payload`가 실제 파일로 누수를 검사한다.
- `annotation_status=accepted`가 아닌 표본은 공식 평가셋에 들어가지 않는다. `--allow-unreviewed` 실행은 결과에 `contains_unreviewed`로 표시된다.
- 같은 시나리오의 변형은 독립 표본이 아니다. bootstrap과 pair 지표는 `scenario_id`를 cluster로 쓴다. `pairs`의 단일 변수 판정은 자동 구조 검사이며 사람의 pair 판정이 끝나야 minimal pair로 보고한다.

## 설계 문서

- 현행: [docs/데이터셋_구축방법.md](docs/데이터셋_구축방법.md), [AGENTS.md](AGENTS.md)
- 이력: [최종설계안.md](최종설계안.md) v2.0(연구 질문·지표 정의는 유지, 말뭉치 확보 절차는 폐기), [독립검증_2026-10.md](독립검증_2026-10.md), `docs/`의 이전 가이드
