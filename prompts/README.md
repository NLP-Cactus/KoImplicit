# 평가 prompt 작업 공간

실제 prompt는 아직 작성하지 않았다. `mcq_v1.json`, `qa_v1.json`은 slot 선언만 있는 뼈대이며 `template`이 비어 있다. 비어 있는 동안 `koimplicit run`은 `PromptNotApproved`로 실행을 거부한다. `koimplicit check-prompts`로 slot 선언과 template의 일치를 검사한다. 후속 단계에서 Full/Local MCQ와 Full QA의 입력 정보를 맞추고 개발 자료로 검토한 뒤 버전을 고정한다.

원문, 문항, 정답 예시는 이 폴더의 공개 prompt 파일에 넣지 않는다. 모델 실행은 각 항목을 독립 요청으로 처리하고 pair의 다른 버전이나 정답을 history에 남기지 않는다.
