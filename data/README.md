# 데이터 작업 공간

- raw: 승인받은 원본. 파일을 수정하지 않는다.
- interim: 구조 audit 및 중간 변환.
- processed: gold·입력 조건 확인 후 만든 평가 입력.
- manifests: source 연결, 대화 단위 split, seed, 버전 및 제외 기록.

MVP 주자료는 ZA 2025 구어다. 구조 audit을 통과하기 전에는 원본 turn 보존이나 entity 연결을 가정하지 않는다. 이 폴더의 실제 자료와 source ID는 Git에서 제외된다.
