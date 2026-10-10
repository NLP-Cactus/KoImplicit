# KoImplicit

한국어 대화의 생략 주어 해소에서 참여자 기준과 문맥 의존성을 평가하는 자연어처리 팀 프로젝트다.

현재는 **설계 v2.0에 맞춘 프로젝트 기본 구조**다. 원자료·주석·문항·평가 프롬프트·모델 결과는 아직 없다. 기본 CLI는 폴더와 설정 상태만 확인하며 모델 호출이나 데이터 다운로드를 하지 않는다.

- 실행 기준: [최종설계안.md](최종설계안.md)
- 조사 근거: [독립검증_2026-10.md](독립검증_2026-10.md)
- 기존 연구 문서는 `docs/`에 보존했다.

## 시작

Python 3.10 이상을 사용한다. 실행 코드는 Python 표준 라이브러리만 사용한다.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m koimplicit status
```

설치 후에는 `koimplicit status`도 사용할 수 있다. 프로젝트 루트 밖에서 실행하면 `--root`로 작업 폴더를 지정한다.

```powershell
.venv\Scripts\python -m koimplicit status --json
.venv\Scripts\python -m unittest discover -s tests
```

ZA 2025 구어 JSON을 `data/raw/` 아래에 풀어 두면 구조 audit을 실행할 수 있다. 출력은 개수만 담고 문장 원문은 출력하지 않는다. `--cases`는 화자가 바뀐 대명사 연결의 source ID 목록을 쓰며 `data/` 아래 경로만 허용한다.

```powershell
.venv\Scripts\python -m koimplicit audit --cases data\interim\cross_speaker_pronoun_links.json
```

`parse`는 같은 파일을 `data/interim/`의 `utterances.jsonl`, `targets.jsonl`, `gold_hints.jsonl`로 평탄화한다. 세부 규약은 [말뭉치 활용 구현 가이드](docs/말뭉치_활용_구현가이드.md) 2절을 따른다.

```powershell
.venv\Scripts\python -m koimplicit parse
```

## 폴더 구조

```text
KoImplicit/
├── 최종설계안.md                 # 현재 실행 설계 v2.0
├── 독립검증_2026-10.md           # 문헌·공식 데이터 검증 근거
├── configs/study.json           # MVP 수량·입력 조건·모델 선택 상태
├── schemas/annotation.schema.json # 자연 자료 annotation 명세 초안
├── src/koimplicit/              # Python 패키지와 상태 확인 CLI
├── data/
│   ├── raw/                     # 승인받은 ZA 2025 구어 원본
│   ├── interim/                 # 구조 audit·정규화 중간 자료
│   ├── processed/               # 후속 평가 입력
│   └── manifests/               # source 연결·대화 split·버전 기록
├── annotations/
│   ├── development/             # 자연 개발 자료 독립 판정·조정
│   ├── heldout/                 # 독립 자연 평가 자료 판정
│   └── controlled/              # 후속 A/B 쌍의 검증·family 기록
├── prompts/                     # 후속 승인된 평가 prompt 버전
├── results/
│   ├── runs/                    # 모델 출력·실행 설정
│   ├── analysis/                # entity/pair accuracy·cluster 분석
│   └── figures/                 # 후속 결과 그림
└── tests/                       # 기본 CLI 확인
```

`data/`, `annotations/`, `results/`의 실제 자료는 Git에서 제외한다. `.gitkeep`과 폴더 안내문만 추적한다. Git 제외는 공개 허가를 대신하지 않으며, 원문·파생 자료의 공개 범위는 실제 약정에 따라 확인한다.

## 설계와 구조의 연결

| 단계 | 저장 위치 | 구현 착수 조건 |
|---|---|---|
| ZA 2025 구어 확보 | data/raw | 이용 승인·약정 |
| speaker/context/target 구조 audit | data/interim | 실파일 구조 확인 |
| 대화 단위 development/held-out split | data/manifests | 대상 적합성과 대화 ID 확인 |
| Full/Local 독립 인간 판정 | annotations | 같은 입력 기준의 entity·충분성 판정 |
| 자연 평가 N | data/processed, results/runs | gold·prompt·분석 기준 동결 |
| 통제 실험 A/B | annotations/controlled | 후속 제작 및 독립 인간 검증 |
| 결과 분석 | results/analysis | 대화/family 단위 cluster 보존 |

MVP 예산은 자연 개발 40개·held-out 80개, A/B 각 12쌍, 모델 2개다. 모델 ID는 아직 지정하지 않았다. 현재 수량은 설정된 **계획**이며 확보된 데이터 수가 아니다.

다음 구현은 구어 실파일 audit부터 시작한다. Corpus parser·문항 생성·모델 provider·통계 pipeline은 해당 단계의 입력을 확인한 뒤 추가한다.
