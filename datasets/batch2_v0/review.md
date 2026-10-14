# Pilot Review

대화를 먼저 읽고 생략 주어를 판단한 뒤, '작성자 라벨'을 펼쳐 비교한다. 작성자 라벨은 검수 전 후보값이다.

## 자동 검증 요약

- 표본 100개, 오류 0, 경고 5, 사람 검수 표시 100

| 축 | 분포 |
|---|---|
| by_dataset | {"controlled": 80, "naturalistic": 20} |
| by_role | {"None": 5, "addressee": 23, "speaker": 15, "third_party": 57} |
| by_referent_changed | {"False": 69, "None": 10, "True": 21} |
| by_speaker_changed | {"False": 11, "None": 5, "True": 84} |
| by_distractor_present | {"False": 54, "None": 5, "True": 41} |
| by_turn_distance | {"0": 5, "1": 21, "2": 4, "3": 27, "None": 43} |
| by_n_participants | {"2": 80, "3": 20} |

## A1

### A1-base (controlled, variant=base, pairs=A1:base~distractor,A1:base~shift)

- 인물: P1=수빈, P2=태훈, T1=지호(비참여), T2=유나(비참여)
- 목표: 4번 발화, 서술어 `재택이래`, 화자 태훈

```text
수빈: 유나 팀 옮긴 건 알지? 근데 지호 소식은 들었어?
태훈: 응, 이번에 계약 연장됐대.
수빈: 그럼 사무실은 계속 나와?
태훈: 아니, 다음 달부터 [[재택이래]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지호 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 질문의 주어가 지호이고 4번이 그 답. 유나는 1번 앞부분에서만 언급.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A1-distractor (controlled, variant=distractor, pairs=A1:base~distractor)

- 인물: P1=수빈, P2=태훈, T1=지호(비참여), T2=유나(비참여)
- 목표: 4번 발화, 서술어 `재택이래`, 화자 태훈

```text
수빈: 지호 소식 들었어?
태훈: 응, 이번에 계약 연장됐대. 유나가 알려 줬어.
수빈: 그럼 사무실은 계속 나와?
태훈: 아니, 다음 달부터 [[재택이래]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지호 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 유나가 2번에서 더 최근에 언급되지만 정보 제공자일 뿐, 사무실 출근 여부를 묻는 3번의 주어는 지호.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### A1-shift (controlled, variant=shift, pairs=A1:base~shift,A1:shift~shift_distractor)

- 인물: P1=수빈, P2=태훈, T1=지호(비참여), T2=유나(비참여)
- 목표: 4번 발화, 서술어 `재택이래`, 화자 태훈

```text
수빈: 지호는 계약 연장됐다며?
태훈: 응. 유나도 팀 옮기고 잘 지낸대.
수빈: 유나는 아직 사무실 나와?
태훈: 아니, 다음 달부터 [[재택이래]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 유나 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T2
- cues: hearsay_ending; manipulated: referent_shift; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 질문이 유나에 대한 것이므로 4번의 주어는 유나.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A1-shift_distractor (controlled, variant=shift_distractor, pairs=A1:shift~shift_distractor)

- 인물: P1=수빈, P2=태훈, T1=지호(비참여), T2=유나(비참여)
- 목표: 4번 발화, 서술어 `재택이래`, 화자 태훈

```text
수빈: 유나 팀 옮기고 어때?
태훈: 잘 지낸대.
수빈: 유나 아직 사무실 나와? 지호랑 같은 층이잖아.
태훈: 아니, 다음 달부터 [[재택이래]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 유나 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T1 present=True; turn_distance=1; most_recent=T1
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번의 '아직 사무실은 나와?'는 1번부터 이어진 유나 이야기. 지호는 '같은 층' 비교 대상으로만 언급.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## A2

### A2-base (controlled, variant=base, pairs=A2:base~distractor,A2:base~shift)

- 인물: P1=채원, P2=건희, T1=나윤(비참여), T2=하람(비참여)
- 목표: 4번 발화, 서술어 `출국한대`, 화자 채원

```text
건희: 하람이는 요즘 뭐 해? 참, 나윤이 유학 가는 건 결정됐어?
채원: 응, 비자도 나왔어.
건희: 그럼 언제 가?
채원: 9월에 [[출국한대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 나윤 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 '언제 가?'의 주어는 유학이 결정된 나윤.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A2-distractor (controlled, variant=distractor, pairs=A2:base~distractor)

- 인물: P1=채원, P2=건희, T1=나윤(비참여), T2=하람(비참여)
- 목표: 4번 발화, 서술어 `출국한대`, 화자 채원

```text
건희: 나윤이 유학 가는 건 결정됐어?
채원: 응, 비자도 나왔어. 하람이가 서류 도와줬어.
건희: 그럼 언제 가?
채원: 9월에 [[출국한대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 나윤 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 하람은 서류를 도와준 사람으로 더 최근에 언급되지만 출국하는 사람은 나윤.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### A2-shift (controlled, variant=shift, pairs=A2:base~shift,A2:shift~shift_distractor)

- 인물: P1=채원, P2=건희, T1=나윤(비참여), T2=하람(비참여)
- 목표: 4번 발화, 서술어 `출국한대`, 화자 채원

```text
건희: 나윤이 유학 가는 건 결정됐어?
채원: 응, 비자도 나왔어. 하람이도 같은 학교 붙었잖아.
건희: 하람이는 언제 가?
채원: 9월에 [[출국한대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 하람 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T2
- cues: hearsay_ending; manipulated: referent_shift; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번이 하람에 대한 질문.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A2-shift_distractor (controlled, variant=shift_distractor, pairs=A2:shift~shift_distractor)

- 인물: P1=채원, P2=건희, T1=나윤(비참여), T2=하람(비참여)
- 목표: 4번 발화, 서술어 `출국한대`, 화자 채원

```text
건희: 하람이 유학 가는 건 결정됐어?
채원: 응, 비자도 나왔어.
건희: 하람이 언제 가? 나윤이랑 같은 학교라며.
채원: 9월에 [[출국한대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 하람 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T1 present=True; turn_distance=1; most_recent=T1
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 1번부터 하람 이야기. 나윤은 '같은 학교' 비교 대상.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## A3

### A3-base (controlled, variant=base, pairs=A3:base~distractor,A3:base~shift)

- 인물: P1=예준, P2=소율, T1=강민(비참여), T2=다희(비참여)
- 목표: 4번 발화, 서술어 `안 나온대`, 화자 소율

```text
예준: 다희는 요즘 연락 되지? 근데 강민이는 왜 모임에 안 보여?
소율: 회사 일이 많아졌대.
예준: 그럼 이번 모임도 바빠?
소율: 그래서 이번엔 [[안 나온대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 강민 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 '바빠?'의 주어는 회사 일이 많아진 강민.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A3-distractor (controlled, variant=distractor, pairs=A3:base~distractor)

- 인물: P1=예준, P2=소율, T1=강민(비참여), T2=다희(비참여)
- 목표: 4번 발화, 서술어 `안 나온대`, 화자 소율

```text
예준: 강민이는 왜 모임에 안 보여?
소율: 회사 일이 많아졌대. 다희한테 들었어.
예준: 그럼 이번 모임도 바빠?
소율: 그래서 이번엔 [[안 나온대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 강민 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 다희는 정보 출처로만 언급.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### A3-shift (controlled, variant=shift, pairs=A3:base~shift,A3:shift~shift_distractor)

- 인물: P1=예준, P2=소율, T1=강민(비참여), T2=다희(비참여)
- 목표: 4번 발화, 서술어 `안 나온대`, 화자 소율

```text
예준: 강민이는 회사 일 때문에 바쁘다며?
소율: 응. 다희도 요즘 집안일이 있다고 하더라.
예준: 다희는 이번 모임 와?
소율: 그래서 이번엔 [[안 나온대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 다희 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T2
- cues: hearsay_ending; manipulated: referent_shift; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번이 다희의 참석을 묻고 '그래서'는 집안일을 가리킨다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A3-shift_distractor (controlled, variant=shift_distractor, pairs=A3:shift~shift_distractor)

- 인물: P1=예준, P2=소율, T1=강민(비참여), T2=다희(비참여)
- 목표: 4번 발화, 서술어 `안 나온대`, 화자 소율

```text
예준: 다희 요즘 집안일로 바쁘다며?
소율: 응, 좀 힘든가 봐.
예준: 다희는 이번 모임 와? 강민이랑 같이 오기로 했잖아.
소율: 그래서 이번엔 [[안 나온대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 다희 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T1 present=True; turn_distance=1; most_recent=T1
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 1번부터 다희 이야기. 강민은 동행 상대로만 언급.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## A4

### A4-base (controlled, variant=base, pairs=A4:base~distractor,A4:base~shift)

- 인물: P1=지우, P2=현서, T1=삼촌(비참여), T2=고모(비참여)
- 목표: 4번 발화, 서술어 `오신대`, 화자 지우

```text
현서: 고모는 추석에 못 오신다고 했지? 삼촌은 연락 있었어?
지우: 응, 어제 전화 왔어.
현서: 그럼 이번 주말에 오셔?
지우: 아니, 다음 주에 [[오신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 삼촌 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 높임은 두 어른 모두에 해당하므로 단서가 아니다. 3번 질문의 주어는 삼촌.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A4-distractor (controlled, variant=distractor, pairs=A4:base~distractor)

- 인물: P1=지우, P2=현서, T1=삼촌(비참여), T2=고모(비참여)
- 목표: 4번 발화, 서술어 `오신대`, 화자 지우

```text
현서: 삼촌은 연락 있었어?
지우: 응, 어제 전화 왔어. 고모도 같이 계시더라.
현서: 그럼 이번 주말에 오셔?
지우: 아니, 다음 주에 [[오신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 삼촌 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 고모는 '같이 계시더라'로 더 최근에 언급될 뿐.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### A4-shift (controlled, variant=shift, pairs=A4:base~shift,A4:shift~shift_distractor)

- 인물: P1=지우, P2=현서, T1=삼촌(비참여), T2=고모(비참여)
- 목표: 4번 발화, 서술어 `오신대`, 화자 지우

```text
현서: 삼촌은 어제 전화 왔다며?
지우: 응. 고모도 추석에 올까 고민하신대.
현서: 고모는 이번 주말에 오셔?
지우: 아니, 다음 주에 [[오신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 고모 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T2
- cues: hearsay_ending; manipulated: referent_shift; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번이 고모의 방문을 묻는다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A4-shift_distractor (controlled, variant=shift_distractor, pairs=A4:shift~shift_distractor)

- 인물: P1=지우, P2=현서, T1=삼촌(비참여), T2=고모(비참여)
- 목표: 4번 발화, 서술어 `오신대`, 화자 지우

```text
현서: 고모 추석에 올까 고민하신다며?
지우: 응, 어제 통화했어.
현서: 고모는 이번 주말에 오셔? 삼촌이랑 같이 오신다고 했잖아.
지우: 아니, 다음 주에 [[오신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 고모 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T1 present=True; turn_distance=1; most_recent=T1
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 1번부터 고모 이야기. 삼촌은 동행 상대.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## A5

### A5-base (controlled, variant=base, pairs=A5:base~distractor,A5:base~shift)

- 인물: P1=시현, P2=라온, T1=교수님(비참여), T2=조교님(비참여)
- 목표: 4번 발화, 서술어 `메일 주신대`, 화자 시현

```text
라온: 조교님한테는 아까 물어봤고. 교수님은 뭐라셔?
시현: 아직 검토 중이시래.
라온: 그럼 오늘 답 주셔?
시현: 응, 오늘 중으로 [[메일 주신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 교수님 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 높임은 둘 다에 해당. 3번 '답 주셔?'의 주어는 검토 중인 교수님.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A5-distractor (controlled, variant=distractor, pairs=A5:base~distractor)

- 인물: P1=시현, P2=라온, T1=교수님(비참여), T2=조교님(비참여)
- 목표: 4번 발화, 서술어 `메일 주신대`, 화자 시현

```text
라온: 교수님은 뭐라셔?
시현: 아직 검토 중이시래. 조교님이 전해 주셨어.
라온: 그럼 오늘 답 주셔?
시현: 응, 오늘 중으로 [[메일 주신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 교수님 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 조교님은 전달자로만 언급.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### A5-shift (controlled, variant=shift, pairs=A5:base~shift,A5:shift~shift_distractor)

- 인물: P1=시현, P2=라온, T1=교수님(비참여), T2=조교님(비참여)
- 목표: 4번 발화, 서술어 `메일 주신대`, 화자 시현

```text
라온: 교수님은 아직 검토 중이시라며?
시현: 응. 조교님이 일정표 정리하고 계신대.
라온: 조교님은 오늘 보내 주셔?
시현: 응, 오늘 중으로 [[메일 주신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 조교님 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T2
- cues: hearsay_ending; manipulated: referent_shift; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번이 조교님의 일정표 발송을 묻는다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### A5-shift_distractor (controlled, variant=shift_distractor, pairs=A5:shift~shift_distractor)

- 인물: P1=시현, P2=라온, T1=교수님(비참여), T2=조교님(비참여)
- 목표: 4번 발화, 서술어 `메일 주신대`, 화자 시현

```text
라온: 조교님이 일정표 정리하고 계신다며?
시현: 응, 거의 다 됐대.
라온: 교수님도 기다리신다던데, 오늘 보내 주셔?
시현: 응, 오늘 중으로 [[메일 주신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 조교님 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T1 present=True; turn_distance=3; most_recent=T1
- cues: hearsay_ending; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번의 마지막 절 '보내 주셔?'의 주어는 조교님. 교수님은 앞 절에서 기다리는 사람.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## B1

### B1-speaker (controlled, variant=speaker, pairs=B1:speaker~addressee)

- 인물: P1=윤서, P2=재민, T1=승우(비참여), T2=민기(비참여)
- 목표: 2번 발화, 서술어 `완전 무리했네`, 화자 윤서

```text
재민: 발표 준비 다 됐어?
윤서: 응, 근데 이틀 동안 거의 못 잤어. [[완전 무리했네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 윤서 / role=speaker
- anchor: turn None → None; speaker_changed=None, referent_changed=None, role_changed=None
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation, same_turn_prior_clause; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 앞 절에서 화자가 못 잤다고 했으므로 자기 평가.

</details>

검증 표시: warning:ANCHOR_MISSING(controlled sample without anchor: shift variables are None); review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B1-addressee (controlled, variant=addressee, pairs=B1:speaker~addressee,B1:addressee~third)

- 인물: P1=윤서, P2=재민, T1=승우(비참여), T2=민기(비참여)
- 목표: 2번 발화, 서술어 `완전 무리했네`, 화자 재민

```text
윤서: 이틀 동안 거의 못 잤어.
재민: 발표 때문에? [[완전 무리했네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 윤서 / role=addressee
- anchor: turn 1 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation; manipulated: speaker_role; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 청자가 1번에서 못 잤다고 했고 2번은 그에 대한 반응.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B1-third (controlled, variant=third, pairs=B1:addressee~third,B1:third~third_distractor)

- 인물: P1=윤서, P2=재민, T1=승우(비참여), T2=민기(비참여)
- 목표: 2번 발화, 서술어 `완전 무리했네`, 화자 재민

```text
윤서: 승우 발표 준비한다고 이틀 동안 거의 못 잤대.
재민: [[완전 무리했네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 승우 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: evaluative_exclamation; manipulated: referent_shift; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 1번이 승우의 상태를 전함.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### B1-third_distractor (controlled, variant=third_distractor, pairs=B1:third~third_distractor)

- 인물: P1=윤서, P2=재민, T1=승우(비참여), T2=민기(비참여)
- 목표: 2번 발화, 서술어 `완전 무리했네`, 화자 재민

```text
윤서: 승우 발표 준비한다고 이틀 동안 거의 못 잤대. 민기랑 같은 조거든.
재민: [[완전 무리했네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 승우 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=1; most_recent=T2
- cues: evaluative_exclamation; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 민기는 '같은 조' 비교 대상. 무리한 사람은 승우.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## B2

### B2-speaker (controlled, variant=speaker, pairs=B2:speaker~addressee)

- 인물: P1=하린, P2=준영, T1=민찬(비참여), T2=수호(비참여)
- 목표: 2번 발화, 서술어 `진짜 많이 늘었다`, 화자 하린

```text
준영: 요즘 기타 연습 잘 돼?
하린: 응, 매일 한 시간씩 했더니 [[진짜 많이 늘었다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 하린 / role=speaker
- anchor: turn None → None; speaker_changed=None, referent_changed=None, role_changed=None
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation, same_turn_prior_clause; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 앞 절의 연습 주체가 화자.

</details>

검증 표시: warning:ANCHOR_MISSING(controlled sample without anchor: shift variables are None); review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B2-addressee (controlled, variant=addressee, pairs=B2:speaker~addressee,B2:addressee~third)

- 인물: P1=하린, P2=준영, T1=민찬(비참여), T2=수호(비참여)
- 목표: 2번 발화, 서술어 `진짜 많이 늘었다`, 화자 준영

```text
하린: 나 어제 연주 영상 올렸어.
준영: 봤어. [[진짜 많이 늘었다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 하린 / role=addressee
- anchor: turn 1 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation; manipulated: speaker_role; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 청자의 영상에 대한 평가.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B2-third (controlled, variant=third, pairs=B2:addressee~third,B2:third~third_distractor)

- 인물: P1=하린, P2=준영, T1=민찬(비참여), T2=수호(비참여)
- 목표: 2번 발화, 서술어 `진짜 많이 늘었다`, 화자 준영

```text
하린: 민찬이 어제 연주 영상 올렸더라.
준영: 봤어. [[진짜 많이 늘었다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 민찬 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: evaluative_exclamation; manipulated: referent_shift; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 민찬의 영상에 대한 평가.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### B2-third_distractor (controlled, variant=third_distractor, pairs=B2:third~third_distractor)

- 인물: P1=하린, P2=준영, T1=민찬(비참여), T2=수호(비참여)
- 목표: 2번 발화, 서술어 `진짜 많이 늘었다`, 화자 준영

```text
하린: 민찬이 어제 연주 영상 올렸더라. 수호랑 같이 찍은 거.
준영: 봤어. [[진짜 많이 늘었다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 민찬 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=1; most_recent=T2
- cues: evaluative_exclamation; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 수호는 함께 찍은 사람으로만 언급. 실력이 는 사람은 영상을 올린 민찬.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## B3

### B3-speaker (controlled, variant=speaker, pairs=B3:speaker~addressee)

- 인물: P1=아린, P2=태민, T1=규현(비참여), T2=선호(비참여)
- 목표: 2번 발화, 서술어 `오늘 운이 좋았네`, 화자 아린

```text
태민: 면접 어땠어?
아린: 질문이 다 아는 거였어. [[오늘 운이 좋았네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 아린 / role=speaker
- anchor: turn None → None; speaker_changed=None, referent_changed=None, role_changed=None
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation, same_turn_prior_clause; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 면접을 본 사람이 화자. 1번 주어는 면접(비인간)이라 anchor 없음.

</details>

검증 표시: warning:ANCHOR_MISSING(controlled sample without anchor: shift variables are None); review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B3-addressee (controlled, variant=addressee, pairs=B3:speaker~addressee,B3:addressee~third)

- 인물: P1=아린, P2=태민, T1=규현(비참여), T2=선호(비참여)
- 목표: 2번 발화, 서술어 `오늘 운이 좋았네`, 화자 태민

```text
아린: 면접 봤는데 질문이 다 아는 거였어.
태민: [[오늘 운이 좋았네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 아린 / role=addressee
- anchor: turn None → None; speaker_changed=None, referent_changed=None, role_changed=None
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation; manipulated: speaker_role; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 면접을 본 사람은 청자. 1번 마지막 절 주어는 질문이라 anchor 없음.

</details>

검증 표시: warning:ANCHOR_MISSING(controlled sample without anchor: shift variables are None); review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B3-third (controlled, variant=third, pairs=B3:addressee~third,B3:third~third_distractor)

- 인물: P1=아린, P2=태민, T1=규현(비참여), T2=선호(비참여)
- 목표: 2번 발화, 서술어 `오늘 운이 좋았네`, 화자 태민

```text
아린: 규현이는 면접 질문이 다 아는 거였대.
태민: [[오늘 운이 좋았네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 규현 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: evaluative_exclamation; manipulated: referent_shift; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 규현이 대주어.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### B3-third_distractor (controlled, variant=third_distractor, pairs=B3:third~third_distractor)

- 인물: P1=아린, P2=태민, T1=규현(비참여), T2=선호(비참여)
- 목표: 2번 발화, 서술어 `오늘 운이 좋았네`, 화자 태민

```text
아린: 규현이는 면접 질문이 다 아는 거였대. 선호랑 같은 조였는데.
태민: [[오늘 운이 좋았네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 규현 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=1; most_recent=T2
- cues: evaluative_exclamation; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 선호는 같은 조로만 언급.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## B4

### B4-speaker (controlled, variant=speaker, pairs=B4:speaker~addressee)

- 인물: P1=서아, P2=우진, T1=혜원(비참여), T2=가람(비참여)
- 목표: 2번 발화, 서술어 `결국 해냈다`, 화자 서아

```text
우진: 자격증 결과 나왔어?
서아: 응, 세 번 만에 붙었어. [[결국 해냈다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 서아 / role=speaker
- anchor: turn None → None; speaker_changed=None, referent_changed=None, role_changed=None
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation, same_turn_prior_clause; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 붙은 사람이 화자.

</details>

검증 표시: warning:ANCHOR_MISSING(controlled sample without anchor: shift variables are None); review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B4-addressee (controlled, variant=addressee, pairs=B4:speaker~addressee,B4:addressee~third)

- 인물: P1=서아, P2=우진, T1=혜원(비참여), T2=가람(비참여)
- 목표: 2번 발화, 서술어 `결국 해냈다`, 화자 우진

```text
서아: 세 번 만에 붙었어.
우진: [[결국 해냈다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 서아 / role=addressee
- anchor: turn 1 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation; manipulated: speaker_role; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 붙은 사람이 청자.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B4-third (controlled, variant=third, pairs=B4:addressee~third,B4:third~third_distractor)

- 인물: P1=서아, P2=우진, T1=혜원(비참여), T2=가람(비참여)
- 목표: 2번 발화, 서술어 `결국 해냈다`, 화자 우진

```text
서아: 혜원이 세 번 만에 붙었대.
우진: [[결국 해냈다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 혜원 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: evaluative_exclamation; manipulated: referent_shift; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 붙은 사람이 혜원.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### B4-third_distractor (controlled, variant=third_distractor, pairs=B4:third~third_distractor)

- 인물: P1=서아, P2=우진, T1=혜원(비참여), T2=가람(비참여)
- 목표: 2번 발화, 서술어 `결국 해냈다`, 화자 우진

```text
서아: 혜원이 세 번 만에 붙었대. 가람이보다 먼저 땄네.
우진: [[결국 해냈다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 혜원 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=1; most_recent=T2
- cues: evaluative_exclamation; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 가람은 비교 대상. 자격증을 딴 사람은 혜원.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## B5

### B5-speaker (controlled, variant=speaker, pairs=B5:speaker~addressee)

- 인물: P1=나은, P2=시온, T1=병훈(비참여), T2=주원(비참여)
- 목표: 2번 발화, 서술어 `너무 성급했어`, 화자 나은

```text
시온: 그 집 계약했어?
나은: 응, 근데 다른 데를 더 볼 걸 그랬어. [[너무 성급했어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 나은 / role=speaker
- anchor: turn 1 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation, same_turn_prior_clause; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 계약한 사람이 화자. 1번 '계약했어?'의 주어는 청자였던 화자 본인.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B5-addressee (controlled, variant=addressee, pairs=B5:speaker~addressee,B5:addressee~third)

- 인물: P1=나은, P2=시온, T1=병훈(비참여), T2=주원(비참여)
- 목표: 2번 발화, 서술어 `너무 성급했어`, 화자 시온

```text
나은: 그 집 바로 계약해 버렸어.
시온: 다른 데도 안 보고? [[너무 성급했어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 나은 / role=addressee
- anchor: turn 1 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation; manipulated: speaker_role; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 계약한 사람이 청자.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### B5-third (controlled, variant=third, pairs=B5:addressee~third,B5:third~third_distractor)

- 인물: P1=나은, P2=시온, T1=병훈(비참여), T2=주원(비참여)
- 목표: 2번 발화, 서술어 `너무 성급했어`, 화자 시온

```text
나은: 병훈이 그 집 바로 계약해 버렸대.
시온: 다른 데도 안 보고? [[너무 성급했어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 병훈 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: evaluative_exclamation; manipulated: referent_shift; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 계약한 사람이 병훈.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### B5-third_distractor (controlled, variant=third_distractor, pairs=B5:third~third_distractor)

- 인물: P1=나은, P2=시온, T1=병훈(비참여), T2=주원(비참여)
- 목표: 2번 발화, 서술어 `너무 성급했어`, 화자 시온

```text
나은: 병훈이 그 집 바로 계약해 버렸대. 주원이 말도 안 듣고.
시온: 다른 데도 안 보고? [[너무 성급했어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 병훈 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=1; most_recent=T2
- cues: evaluative_exclamation; manipulated: distractor; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 주원은 말린 사람으로 비주어 자리. 성급한 사람은 병훈.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## C1

### C1-keep_other (controlled, variant=keep_other, pairs=C1:keep_other~keep_same,C1:keep_other~shift_other)

- 인물: P1=하은, P2=도윤, T1=준서(비참여), T2=세아(비참여)
- 목표: 4번 발화, 서술어 `퇴원한대`, 화자 도윤

```text
하은: 준서 수술은 잘 됐대?
도윤: 응, 잘 끝났대.
하은: 그럼 언제까지 입원해 있어야 돼?
도윤: 다음 주에 [[퇴원한대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 준서 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 '입원해 있어야 돼?'의 주어가 준서, 4번이 답.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C1-keep_same (controlled, variant=keep_same, pairs=C1:keep_other~keep_same,C1:keep_same~shift_same)

- 인물: P1=하은, P2=도윤, T1=준서(비참여), T2=세아(비참여)
- 목표: 4번 발화, 서술어 `퇴원한대`, 화자 도윤

```text
하은: 준서 수술은 잘 됐대?
도윤: 응, 잘 끝났대. 회복도 빠른 편이래.
하은: 다행이다.
도윤: 다음 주에 [[퇴원한대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 준서 / role=third_party
- anchor: turn 2 → T1; speaker_changed=False, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_speaker; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번은 맞장구. 2번 마지막 절 '회복도 빠른 편이래'의 대주어 준서.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C1-shift_other (controlled, variant=shift_other, pairs=C1:keep_other~shift_other,C1:shift_other~shift_same)

- 인물: P1=하은, P2=도윤, T1=준서(비참여), T2=세아(비참여)
- 목표: 4번 발화, 서술어 `퇴원한대`, 화자 도윤

```text
하은: 준서 수술은 잘 됐대?
도윤: 응, 잘 끝났대.
하은: 세아가 밤새 병원에 있었다며. 고생했겠다.
도윤: 다음 주에 [[퇴원한대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 준서 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 주어는 세아지만 퇴원하는 사람은 수술받은 준서.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### C1-shift_same (controlled, variant=shift_same, pairs=C1:keep_same~shift_same,C1:shift_other~shift_same)

- 인물: P1=하은, P2=도윤, T1=준서(비참여), T2=세아(비참여)
- 목표: 4번 발화, 서술어 `퇴원한대`, 화자 도윤

```text
하은: 준서 수술은 잘 됐대?
도윤: 응, 잘 끝났대. 세아가 밤새 병원에 있었대. 고생했겠더라.
하은: 그러게.
도윤: 다음 주에 [[퇴원한대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 준서 / role=third_party
- anchor: turn 2 → T2; speaker_changed=False, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 주어는 세아, 퇴원은 준서.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## C2

### C2-keep_other (controlled, variant=keep_other, pairs=C2:keep_other~keep_same,C2:keep_other~shift_other)

- 인물: P1=유빈, P2=성민, T1=지민(비참여), T2=혜진(비참여)
- 목표: 4번 발화, 서술어 `올라갔대`, 화자 성민

```text
유빈: 지민이 지원한 회사 결과 나왔어?
성민: 응, 어제 연락 왔대.
유빈: 그래서 붙었대?
성민: 최종 면접까지 [[올라갔대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지민 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 '붙었대?'의 주어가 지민.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C2-keep_same (controlled, variant=keep_same, pairs=C2:keep_other~keep_same,C2:keep_same~shift_same)

- 인물: P1=유빈, P2=성민, T1=지민(비참여), T2=혜진(비참여)
- 목표: 4번 발화, 서술어 `올라갔대`, 화자 성민

```text
유빈: 지민이 지원한 회사 결과 나왔어?
성민: 응, 어제 연락 왔대. 서류는 통과했대.
유빈: 오, 그래서?
성민: 최종 면접까지 [[올라갔대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지민 / role=third_party
- anchor: turn 2 → T1; speaker_changed=False, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_speaker; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 '서류는 통과했대'의 주어 지민.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C2-shift_other (controlled, variant=shift_other, pairs=C2:keep_other~shift_other,C2:shift_other~shift_same)

- 인물: P1=유빈, P2=성민, T1=지민(비참여), T2=혜진(비참여)
- 목표: 4번 발화, 서술어 `올라갔대`, 화자 성민

```text
유빈: 지민이 지원한 회사 결과 나왔어?
성민: 응, 어제 연락 왔대.
유빈: 혜진이가 자소서 많이 봐줬다며. 진짜 잘해 주네.
성민: 최종 면접까지 [[올라갔대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지민 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 주어는 혜진이지만 면접에 올라가는 사람은 지원자 지민.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### C2-shift_same (controlled, variant=shift_same, pairs=C2:keep_same~shift_same,C2:shift_other~shift_same)

- 인물: P1=유빈, P2=성민, T1=지민(비참여), T2=혜진(비참여)
- 목표: 4번 발화, 서술어 `올라갔대`, 화자 성민

```text
유빈: 지민이 지원한 회사 결과 나왔어?
성민: 응, 어제 연락 왔대. 혜진이가 자소서 많이 봐줬대.
유빈: 오, 그래서?
성민: 최종 면접까지 [[올라갔대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지민 / role=third_party
- anchor: turn 2 → T2; speaker_changed=False, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 주어 혜진, 면접은 지민.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## C3

### C3-keep_other (controlled, variant=keep_other, pairs=C3:keep_other~keep_same,C3:keep_other~shift_other)

- 인물: P1=소민, P2=현준, T1=김 대리(비참여), T2=가은(비참여)
- 목표: 4번 발화, 서술어 `답 준대`, 화자 현준

```text
소민: 김 대리한테 견적 요청한 건 어떻게 됐어?
현준: 어제 메일 보냈어.
소민: 그래서 언제 준대?
현준: 오늘 안에 [[답 준대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 김 대리 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 '언제 준대?'의 주어가 김 대리.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C3-keep_same (controlled, variant=keep_same, pairs=C3:keep_other~keep_same,C3:keep_same~shift_same)

- 인물: P1=소민, P2=현준, T1=김 대리(비참여), T2=가은(비참여)
- 목표: 4번 발화, 서술어 `답 준대`, 화자 현준

```text
소민: 김 대리한테 견적 요청한 건 어떻게 됐어?
현준: 어제 메일 보냈어. 지금 확인 중이라더라.
소민: 그래서?
현준: 오늘 안에 [[답 준대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 김 대리 / role=third_party
- anchor: turn 2 → T1; speaker_changed=False, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_speaker; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 '확인 중이라더라'의 주어 김 대리.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C3-shift_other (controlled, variant=shift_other, pairs=C3:keep_other~shift_other,C3:shift_other~shift_same)

- 인물: P1=소민, P2=현준, T1=김 대리(비참여), T2=가은(비참여)
- 목표: 4번 발화, 서술어 `답 준대`, 화자 현준

```text
소민: 김 대리한테 견적 요청한 건 어떻게 됐어?
현준: 어제 메일 보냈어.
소민: 가은이가 양식 만들어 줬다며. 꼼꼼하더라.
현준: 오늘 안에 [[답 준대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 김 대리 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 주어는 가은이지만 견적에 답하는 쪽은 거래처 김 대리.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### C3-shift_same (controlled, variant=shift_same, pairs=C3:keep_same~shift_same,C3:shift_other~shift_same)

- 인물: P1=소민, P2=현준, T1=김 대리(비참여), T2=가은(비참여)
- 목표: 4번 발화, 서술어 `답 준대`, 화자 현준

```text
소민: 김 대리한테 견적 요청한 건 어떻게 됐어?
현준: 어제 메일 보냈어. 가은이가 양식 만들어 줬어.
소민: 그래서?
현준: 오늘 안에 [[답 준대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 김 대리 / role=third_party
- anchor: turn 2 → T2; speaker_changed=False, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 주어 가은, 답은 김 대리.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## C4

### C4-keep_other (controlled, variant=keep_other, pairs=C4:keep_other~keep_same,C4:keep_other~shift_other)

- 인물: P1=지유, P2=한결, T1=누나(비참여), T2=민호(비참여)
- 목표: 4번 발화, 서술어 `짐 뺀대`, 화자 지유

```text
한결: 누나 이사 날짜 잡혔어?
지유: 응, 집은 구했대.
한결: 그럼 언제 나가?
지유: 토요일에 [[짐 뺀대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 누나 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 '언제 나가?'의 주어가 누나.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C4-keep_same (controlled, variant=keep_same, pairs=C4:keep_other~keep_same,C4:keep_same~shift_same)

- 인물: P1=지유, P2=한결, T1=누나(비참여), T2=민호(비참여)
- 목표: 4번 발화, 서술어 `짐 뺀대`, 화자 지유

```text
한결: 누나 이사 날짜 잡혔어?
지유: 응, 집은 구했대. 계약도 끝났고.
한결: 잘됐네.
지유: 토요일에 [[짐 뺀대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 누나 / role=third_party
- anchor: turn 2 → T1; speaker_changed=False, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_speaker; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 '계약도 끝났고'의 대주어 누나.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C4-shift_other (controlled, variant=shift_other, pairs=C4:keep_other~shift_other,C4:shift_other~shift_same)

- 인물: P1=지유, P2=한결, T1=누나(비참여), T2=민호(비참여)
- 목표: 4번 발화, 서술어 `짐 뺀대`, 화자 지유

```text
한결: 누나 이사 날짜 잡혔어?
지유: 응, 집은 구했대.
한결: 민호가 차 빌려준다며. 착하네.
지유: 토요일에 [[짐 뺀대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 누나 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 주어는 민호지만 짐을 빼는 사람은 이사하는 누나.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### C4-shift_same (controlled, variant=shift_same, pairs=C4:keep_same~shift_same,C4:shift_other~shift_same)

- 인물: P1=지유, P2=한결, T1=누나(비참여), T2=민호(비참여)
- 목표: 4번 발화, 서술어 `짐 뺀대`, 화자 지유

```text
한결: 누나 이사 날짜 잡혔어?
지유: 응, 집은 구했대. 민호가 차 빌려준대.
한결: 잘됐네.
지유: 토요일에 [[짐 뺀대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 누나 / role=third_party
- anchor: turn 2 → T2; speaker_changed=False, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 주어 민호, 이사는 누나.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## C5

### C5-keep_other (controlled, variant=keep_other, pairs=C5:keep_other~keep_same,C5:keep_other~shift_other)

- 인물: P1=은우, P2=서현, T1=지후(비참여), T2=지후 어머니(비참여)
- 목표: 4번 발화, 서술어 `다시 온대`, 화자 서현

```text
은우: 과외 학생 요즘 안 와?
서현: 지후? 이번 달은 쉬기로 했어.
은우: 그럼 언제 다시 해?
서현: 시험 끝나면 [[다시 온대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지후 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=2; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint, honorific_absence; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 '다시 해?'의 주어가 지후.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C5-keep_same (controlled, variant=keep_same, pairs=C5:keep_other~keep_same,C5:keep_same~shift_same)

- 인물: P1=은우, P2=서현, T1=지후(비참여), T2=지후 어머니(비참여)
- 목표: 4번 발화, 서술어 `다시 온대`, 화자 서현

```text
은우: 과외 학생 요즘 안 와?
서현: 지후? 이번 달은 쉬기로 했어. 학교 시험 기간이래.
은우: 아, 그렇구나.
서현: 시험 끝나면 [[다시 온대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지후 / role=third_party
- anchor: turn 2 → T1; speaker_changed=False, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=2; most_recent=T1
- cues: hearsay_ending, semantic_role_constraint, honorific_absence; manipulated: anchor_speaker; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 '시험 기간이래'의 대주어 지후.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### C5-shift_other (controlled, variant=shift_other, pairs=C5:keep_other~shift_other,C5:shift_other~shift_same)

- 인물: P1=은우, P2=서현, T1=지후(비참여), T2=지후 어머니(비참여)
- 목표: 4번 발화, 서술어 `다시 온대`, 화자 서현

```text
은우: 과외 학생 요즘 안 와?
서현: 지후? 이번 달은 쉬기로 했어.
은우: 지후 어머니가 미안해하셨다며. 신경 많이 쓰시네.
서현: 시험 끝나면 [[다시 온대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지후 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=2; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint, honorific_absence; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 주어는 어머니지만 다시 오는 사람은 학생. 높임 부재가 단서가 될 수 있어 기록.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### C5-shift_same (controlled, variant=shift_same, pairs=C5:keep_same~shift_same,C5:shift_other~shift_same)

- 인물: P1=은우, P2=서현, T1=지후(비참여), T2=지후 어머니(비참여)
- 목표: 4번 발화, 서술어 `다시 온대`, 화자 서현

```text
은우: 과외 학생 요즘 안 와?
서현: 지후? 이번 달은 쉬기로 했어. 어머니가 미안해하시더라.
은우: 아, 그렇구나.
서현: 시험 끝나면 [[다시 온대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지후 / role=third_party
- anchor: turn 2 → T2; speaker_changed=False, referent_changed=True, role_changed=False
- distractor: None present=True; turn_distance=2; most_recent=T2
- cues: hearsay_ending, semantic_role_constraint, honorific_absence; manipulated: anchor_entity; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 마지막 절 주어 어머니, 오는 사람은 지후.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## D1

### D1-vocative (controlled, variant=vocative, pairs=D1:vocative~adjacency,D1:vocative~ambiguous)

- 인물: P1=채린, P2=민석, P3=진우
- 목표: 4번 발화, 서술어 `공유해 줘`, 화자 채린

```text
채린: 다음 주 발표 자료 누가 갖고 있어?
민석: 나는 아직 못 봤는데.
진우: 내가 정리해 뒀어.
채린: 진우야, 자료 좀 [[공유해 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 진우 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=0; most_recent=P3
- cues: vocative, request; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 호격 진우야.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee)

### D1-adjacency (controlled, variant=adjacency, pairs=D1:vocative~adjacency)

- 인물: P1=채린, P2=민석, P3=진우
- 목표: 4번 발화, 서술어 `공유해 줘`, 화자 채린

```text
채린: 다음 주 발표 자료 누가 갖고 있어?
민석: 나는 아직 못 봤는데.
진우: 내가 정리해 뒀어.
채린: 자료 좀 [[공유해 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 진우 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: request, adjacency; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 자료를 가진 사람은 직전 화자 진우.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,multi_party_addressee)

### D1-ambiguous (controlled, variant=ambiguous, pairs=D1:vocative~ambiguous)

- 인물: P1=채린, P2=민석, P3=진우
- 목표: 4번 발화, 서술어 `공유해 줘`, 화자 채린

```text
채린: 다음 주 발표 자료 누가 갖고 있어?
민석: 나 있어.
진우: 나도 있어.
채린: 자료 좀 [[공유해 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: None (없음) / role=None
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=None, role_changed=None
- distractor: None present=None; turn_distance=None; most_recent=None
- cues: request; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=ambiguous, annotation=candidate, creation=llm_authored
- 근거: 둘 다 자료가 있어 요청 대상이 확정되지 않음.

</details>

검증 표시: review:HUMAN_REVIEW(multi_party_addressee)

### D1-third_in_3p (controlled, variant=third_in_3p, pairs=-)

- 인물: P1=채린, P2=민석, P3=진우
- 목표: 4번 발화, 서술어 `아픈 것 같지 않아`, 화자 채린

```text
진우: 나 오늘 좀 일찍 가야 돼.
채린: 왜?
진우: 병원 예약.
채린: 민석아, 요즘 계속 [[아픈 것 같지 않아]]?
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 진우 / role=third_party
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=True; turn_distance=None; most_recent=P2
- cues: vocative; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 청자는 민석(호격), 아픈 사람은 병원에 간다는 진우.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee,distractor_check_gold_still_unique)

## D2

### D2-vocative (controlled, variant=vocative, pairs=D2:vocative~adjacency,D2:vocative~ambiguous)

- 인물: P1=유리, P2=동하, P3=세훈
- 목표: 4번 발화, 서술어 `가져와 줘`, 화자 유리

```text
유리: 토요일에 차 누가 가져와?
동하: 난 그날 차 정비 맡겨.
세훈: 내 차는 비어 있어.
유리: 세훈아, 그럼 [[가져와 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 세훈 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=0; most_recent=P3
- cues: vocative, request; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 호격 세훈아.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee)

### D2-adjacency (controlled, variant=adjacency, pairs=D2:vocative~adjacency)

- 인물: P1=유리, P2=동하, P3=세훈
- 목표: 4번 발화, 서술어 `가져와 줘`, 화자 유리

```text
유리: 토요일에 차 누가 가져와?
동하: 난 그날 차 정비 맡겨.
세훈: 내 차는 비어 있어.
유리: 그럼 [[가져와 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 세훈 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: request, adjacency; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 차가 비어 있는 사람은 직전 화자 세훈.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,multi_party_addressee)

### D2-ambiguous (controlled, variant=ambiguous, pairs=D2:vocative~ambiguous)

- 인물: P1=유리, P2=동하, P3=세훈
- 목표: 4번 발화, 서술어 `가져와 줘`, 화자 유리

```text
유리: 토요일에 차 누가 가져와?
동하: 내 차 가져갈 수 있어.
세훈: 나도 가능해.
유리: 그럼 [[가져와 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: None (없음) / role=None
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=None, role_changed=None
- distractor: None present=None; turn_distance=None; most_recent=None
- cues: request; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=ambiguous, annotation=candidate, creation=llm_authored
- 근거: 둘 다 가능하다고 해 확정 불가.

</details>

검증 표시: review:HUMAN_REVIEW(multi_party_addressee)

### D2-third_in_3p (controlled, variant=third_in_3p, pairs=-)

- 인물: P1=유리, P2=동하, P3=세훈
- 목표: 4번 발화, 서술어 `늦었잖아`, 화자 유리

```text
동하: 나 토요일에 좀 늦을 것 같아.
유리: 얼마나?
동하: 한 시간쯤.
유리: 세훈아, 지난번에도 한 시간 [[늦었잖아]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 동하 / role=third_party
- anchor: turn 3 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=True; turn_distance=None; most_recent=P3
- cues: vocative; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 청자 세훈(호격), 늦은 사람은 동하.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee,distractor_check_gold_still_unique)

## D3

### D3-vocative (controlled, variant=vocative, pairs=D3:vocative~adjacency,D3:vocative~ambiguous)

- 인물: P1=이안, P2=수호, P3=예나
- 목표: 4번 발화, 서술어 `내 줘`, 화자 이안

```text
이안: 회비 아직 안 낸 사람 있어?
수호: 나 어제 냈어.
예나: 나는 아직.
이안: 예나야, 내일까지는 [[내 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 예나 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=0; most_recent=P3
- cues: vocative, request; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 호격 예나야.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee)

### D3-adjacency (controlled, variant=adjacency, pairs=D3:vocative~adjacency)

- 인물: P1=이안, P2=수호, P3=예나
- 목표: 4번 발화, 서술어 `내 줘`, 화자 이안

```text
이안: 회비 아직 안 낸 사람 있어?
수호: 나 어제 냈어.
예나: 나는 아직.
이안: 내일까지는 [[내 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 예나 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: request, adjacency; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 안 낸 사람은 직전 화자 예나.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,multi_party_addressee)

### D3-ambiguous (controlled, variant=ambiguous, pairs=D3:vocative~ambiguous)

- 인물: P1=이안, P2=수호, P3=예나
- 목표: 4번 발화, 서술어 `내 줘`, 화자 이안

```text
이안: 회비 아직 안 낸 사람 있어?
수호: 나 아직 못 냈어.
예나: 나도.
이안: 내일까지는 [[내 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: None (없음) / role=None
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=None, role_changed=None
- distractor: None present=None; turn_distance=None; most_recent=None
- cues: request; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=ambiguous, annotation=candidate, creation=llm_authored
- 근거: 둘 다 안 냈다.

</details>

검증 표시: review:HUMAN_REVIEW(multi_party_addressee)

### D3-third_in_3p (controlled, variant=third_in_3p, pairs=-)

- 인물: P1=이안, P2=수호, P3=예나
- 목표: 4번 발화, 서술어 `내도 되지`, 화자 이안

```text
예나: 나 이번 달 회비 못 낼 것 같아.
이안: 왜?
예나: 알바비가 늦게 들어와.
이안: 수호야, 다음 달에 한꺼번에 [[내도 되지]]?
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 예나 / role=third_party
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=True; turn_distance=None; most_recent=P2
- cues: vocative; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 청자 수호(호격), 다음 달에 내는 사람은 예나. 3번 '늦게 들어와'의 주어는 알바비라 anchor는 1번의 예나로 보지만 v0에서는 3번 대주어 예나로 기록.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee,distractor_check_gold_still_unique)

## D4

### D4-vocative (controlled, variant=vocative, pairs=D4:vocative~adjacency,D4:vocative~ambiguous)

- 인물: P1=아빠, P2=지원, P3=태오
- 목표: 4번 발화, 서술어 `문단속 잘하고`, 화자 아빠

```text
아빠: 내일 아침에 누가 먼저 나가?
지원: 나는 아홉 시 수업이야.
태오: 난 일곱 시에 나가야 돼.
아빠: 태오야, 그럼 나갈 때 [[문단속 잘하고]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 태오 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=0; most_recent=P3
- cues: vocative, imperative; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 호격 태오야.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee)

### D4-adjacency (controlled, variant=adjacency, pairs=D4:vocative~adjacency)

- 인물: P1=아빠, P2=지원, P3=태오
- 목표: 4번 발화, 서술어 `문단속 잘하고`, 화자 아빠

```text
아빠: 내일 아침에 누가 먼저 나가?
지원: 나는 아홉 시 수업이야.
태오: 난 일곱 시에 나가야 돼.
아빠: 그럼 나갈 때 [[문단속 잘하고]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 태오 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: imperative, adjacency; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 먼저 나가는 사람은 직전 화자 태오.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,multi_party_addressee)

### D4-ambiguous (controlled, variant=ambiguous, pairs=D4:vocative~ambiguous)

- 인물: P1=아빠, P2=지원, P3=태오
- 목표: 4번 발화, 서술어 `문단속 잘하고`, 화자 아빠

```text
아빠: 내일 아침에 누가 먼저 나가?
지원: 나 일곱 시.
태오: 나도 일곱 시쯤.
아빠: 그럼 나갈 때 [[문단속 잘하고]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: None (없음) / role=None
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=None, role_changed=None
- distractor: None present=None; turn_distance=None; most_recent=None
- cues: imperative; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=ambiguous, annotation=candidate, creation=llm_authored
- 근거: 둘 다 일곱 시.

</details>

검증 표시: review:HUMAN_REVIEW(multi_party_addressee)

### D4-third_in_3p (controlled, variant=third_in_3p, pairs=-)

- 인물: P1=아빠, P2=지원, P3=태오
- 목표: 4번 발화, 서술어 `일찍 나가더라`, 화자 아빠

```text
태오: 나 내일 일곱 시에 나가야 돼.
아빠: 그렇게 일찍?
태오: 응, 아침 자습.
아빠: 지원아, 요즘 매일 저렇게 [[일찍 나가더라]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 태오 / role=third_party
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=True; turn_distance=None; most_recent=P2
- cues: vocative, demonstrative; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 청자 지원(호격), 일찍 나가는 사람은 태오. '저렇게'가 단서.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee,distractor_check_gold_still_unique)

## D5

### D5-vocative (controlled, variant=vocative, pairs=D5:vocative~adjacency,D5:vocative~ambiguous)

- 인물: P1=선우, P2=미래, P3=정훈
- 목표: 4번 발화, 서술어 `끝내 줘`, 화자 선우

```text
선우: 이 보고서 오늘까지 가능한 사람?
미래: 저는 오후에 외근이에요.
정훈: 저는 오전엔 시간 돼요.
선우: 정훈아, 그럼 오늘까지 [[끝내 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 정훈 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=0; most_recent=P3
- cues: vocative, request; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 호격 정훈아.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee)

### D5-adjacency (controlled, variant=adjacency, pairs=D5:vocative~adjacency)

- 인물: P1=선우, P2=미래, P3=정훈
- 목표: 4번 발화, 서술어 `끝내 줘`, 화자 선우

```text
선우: 이 보고서 오늘까지 가능한 사람?
미래: 저는 오후에 외근이에요.
정훈: 저는 오전엔 시간 돼요.
선우: 그럼 오늘까지 [[끝내 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 정훈 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: request, adjacency; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 시간이 되는 사람은 직전 화자 정훈.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,multi_party_addressee)

### D5-ambiguous (controlled, variant=ambiguous, pairs=D5:vocative~ambiguous)

- 인물: P1=선우, P2=미래, P3=정훈
- 목표: 4번 발화, 서술어 `끝내 줘`, 화자 선우

```text
선우: 이 보고서 오늘까지 가능한 사람?
미래: 저 오전에 시간 돼요.
정훈: 저도 돼요.
선우: 그럼 오늘까지 [[끝내 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: None (없음) / role=None
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=None, role_changed=None
- distractor: None present=None; turn_distance=None; most_recent=None
- cues: request; manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=ambiguous, annotation=candidate, creation=llm_authored
- 근거: 둘 다 가능.

</details>

검증 표시: review:HUMAN_REVIEW(multi_party_addressee)

### D5-third_in_3p (controlled, variant=third_in_3p, pairs=-)

- 인물: P1=선우, P2=미래, P3=정훈
- 목표: 4번 발화, 서술어 `힘든 일 있는 것 같지 않아`, 화자 선우

```text
정훈: 저 오늘 반차 쓸게요.
선우: 무슨 일 있어?
정훈: 집에 일이 좀 있어서요.
선우: 미래야, 요즘 [[힘든 일 있는 것 같지 않아]]?
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 정훈 / role=third_party
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=True; turn_distance=None; most_recent=P2
- cues: vocative; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 청자 미래(호격), 힘든 일이 있는 사람은 반차를 내는 정훈.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee,distractor_check_gold_still_unique)

## N04

### N04-base (naturalistic, variant=base, pairs=-)

- 인물: P1=수연, P2=민규, T1=팀장님(비참여)
- 목표: 5번 발화, 서술어 `쉴 예정이야`, 화자 수연

```text
수연: 아, 드디어 퇴근이네. 내일 연차 쓰려고 했는데 오늘 일이 안 끝날까 봐 조마조마했어.
민규: 아까 팀장님이 자료 하나 더 정리하라고 했잖아. 그것까지 다 끝냈어?
수연: 응, 방금 보내고 나왔어. 연차 신청도 해 뒀는데 승인됐는지 못 봤네.
민규: 팀장님이 아까 승인했어.
수연: 다행이다. 내일은 집에서 푹 [[쉴 예정이야]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 수연 / role=speaker
- anchor: turn 4 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: volitional_plan(-ㄹ 예정); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 4번 주어 팀장님, 5번 '쉴 예정이야'는 연차를 신청한 수연 자신.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N05

### N05-base (naturalistic, variant=base, pairs=-)

- 인물: P1=지혜, P2=보람, T1=집주인(비참여)
- 목표: 4번 발화, 서술어 `알아볼게`, 화자 보람

```text
지혜: 저녁 먹고 짐부터 조금씩 정리할까? 이사 준비 서둘러야겠어.
보람: 그러자. 짐 정리랑 새집 찾는 거 나눠서 하면 되겠다.
지혜: 짐 정리는 내가 맡을 테니까 집 알아보는 건 맡아 줄래? 집주인은 한 달만 더 살겠다는 것도 거절했어.
보람: 응, 내일 퇴근하고 부동산 몇 군데 들러서 집을 [[알아볼게]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 보람 / role=speaker
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: volitional_ending(-ㄹ게); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 3번 마지막 절 주어 집주인. '-ㄹ게'는 화자 의지 표현이라 단서가 강함.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N06

### N06-base (naturalistic, variant=base, pairs=-)

- 인물: P1=현우, P2=서윤, T1=엄마(비참여)
- 목표: 5번 발화, 서술어 `안 했어`, 화자 현우

```text
현우: 어제 엄마가 시험 성적 물어봤어.
서윤: 그래서 점수 말씀드렸어?
현우: 생각보다 많이 떨어져서 말하기가 좀 그렇더라.
서윤: 엄마는 성적 언제 나오는지 계속 궁금해하던데.
현우: 아직 성적 나왔다는 말도 [[안 했어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 현우 / role=speaker
- anchor: turn 4 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: -; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 4번 주어 엄마, 5번 '말도 안 했어'는 성적을 숨기는 현우.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N07

### N07-base (naturalistic, variant=base, pairs=-)

- 인물: P1=태희, P2=준수, T1=코치님(비참여)
- 목표: 4번 발화, 서술어 `못 가`, 화자 준수

```text
태희: 코치님이 토요일 훈련을 오전으로 옮겼대.
준수: 토요일 오전엔 동생이랑 병원 가기로 했는데. 오후로 다시 바꿀 수는 없대?
태희: 응, 코치님은 오후에 다른 수업이 있대.
준수: 그럼 이번 훈련은 [[못 가]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 준수 / role=speaker
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: -; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 3번 마지막 절 주어 코치님, 4번 '못 가'는 병원 일정이 있는 준수.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N08

### N08-base (naturalistic, variant=base, pairs=-)

- 인물: P1=은지, P2=성호, T1=형(비참여)
- 목표: 5번 발화, 서술어 `도우려고`, 화자 성호

```text
은지: 형이 카페 열었다며? 준비하느라 한동안 바빴겠다.
성호: 응, 지난주에 열었어. 아직 직원을 못 구했대.
은지: 그럼 넌 어떻게 도와주려고?
성호: 형은 평일보다 주말에 더 바쁘대.
성호: 주말에 가서 주문 받는 일 좀 [[도우려고]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 성호 / role=speaker
- anchor: turn 4 → T1; speaker_changed=False, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: volitional_ending(-려고); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 4번 주어 형, 5번은 같은 화자 성호의 계획. 화자 유지 표본.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N09

### N09-base (naturalistic, variant=base, pairs=-)

- 인물: P1=하영, P2=동건, T1=조장(비참여)
- 목표: 4번 발화, 서술어 `다 끝냈어`, 화자 하영

```text
동건: 조장이 발표 순서 정해서 단톡방에 올렸어.
하영: 아직 못 봤는데, 내가 첫 번째야?
동건: 응, 조장은 맨 마지막에 발표하기로 했어.
하영: 첫 번째라 좀 떨리긴 하는데, 발표 준비는 [[다 끝냈어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 하영 / role=speaker
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: -; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 3번 주어 조장, 4번 '다 끝냈어'는 첫 번째 발표자 하영.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N10

### N10-base (naturalistic, variant=base, pairs=-)

- 인물: P1=민아, P2=재현, T1=아이(비참여)
- 목표: 4번 발화, 서술어 `데려갈 수 있어`, 화자 재현

```text
민아: 아이가 새벽부터 열이 나네. 해열제 먹였는데도 잘 안 내려가.
재현: 병원 문 열면 데려가야겠다. 오늘 오전에 시간 괜찮아?
민아: 오전 회의는 빠지기 어려운데, 당신은 어때? 애가 계속 축 처져 있어.
재현: 오전에 반차 내고 병원에 [[데려갈 수 있어]].
민아: 그럼 부탁할게. 진료 끝나면 연락해 줘.
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 재현 / role=speaker
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: ability(-ㄹ 수 있어); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 3번 마지막 절 주어 아이(애), 4번은 반차를 내는 재현.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N11

### N11-base (naturalistic, variant=base, pairs=-)

- 인물: P1=유진, P2=상민, T1=면접관(비참여)
- 목표: 4번 발화, 서술어 `준비해 뒀어`, 화자 유진

```text
상민: 내일 면접이지? 거기 면접관이 꽤 까다롭다는 소문이 있던데.
유진: 그러니까. 어제도 밤늦게까지 답변 연습했어.
상민: 대답을 조금만 얼버무려도 면접관이 끝까지 캐묻는대.
유진: 그래도 예상 질문 답변은 꼼꼼히 [[준비해 뒀어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 유진 / role=speaker
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: -; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 3번 주어 면접관, 4번 '준비해 뒀어'는 면접을 보는 유진.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N12

### N12-base (naturalistic, variant=base, pairs=-)

- 인물: P1=소연, P2=규민, T1=동생(비참여)
- 목표: 5번 발화, 서술어 `주문할 거야`, 화자 소연

```text
소연: 동생 생일 선물로 무선 이어폰을 샀어. 케이크도 내가 준비하기로 했고.
규민: 선물은 골랐네. 케이크는 무슨 맛으로 하려고?
소연: 딸기랑 초콜릿 중에 고민 중이야. 지난번에 우리 집에서 같이 먹었을 때 어땠지?
규민: 동생은 초콜릿만 먹더라. 딸기는 손도 안 댔어.
소연: 그럼 오늘 저녁에 초콜릿 케이크로 [[주문할 거야]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 소연 / role=speaker
- anchor: turn 4 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: volitional_ending(-ㄹ 거야); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 4번 마지막 절 주어 동생, 5번은 케이크를 준비하기로 한 소연.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N13

### N13-base (naturalistic, variant=base, pairs=-)

- 인물: P1=연우, P2=지성, T1=기사님(비참여)
- 목표: 4번 발화, 서술어 `집에 있어`, 화자 지성

```text
연우: 싱크대 물 새는 건 수리 맡겼어?
지성: 응, 기사님이 다음 주 수요일에 온대.
연우: 그날 집에 있을 수 있어? 기사님은 오후 두 시쯤 온다던데.
지성: 응, 그날은 일정이 없어서 오후 내내 [[집에 있어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 지성 / role=speaker
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: -; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 3번 마지막 절 주어 기사님, 4번 '집에 있어'는 집에 있을 지성.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N14

### N14-base (naturalistic, variant=base, pairs=-)

- 인물: P1=다현, P2=승민
- 목표: 4번 발화, 서술어 `준비해야겠네`, 화자 다현

```text
승민: 아, 늦잠 잤네. 알람을 못 들었어.
다현: 벌써 여덟 시야. 난 준비 다 해서 먼저 나가려고.
승민: 버스가 십 분 뒤에 오는데 아직 잠옷도 안 갈아입었어.
다현: 그럼 지금 바로 [[준비해야겠네]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 승민 / role=addressee
- anchor: turn 3 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: obligation(-아야겠네); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 늦잠 잔 승민에게 다현이 하는 말. 3번 주어 승민(화자)→4번 청자로 역할 전환.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

## N15

### N15-base (naturalistic, variant=base, pairs=-)

- 인물: P1=수아, P2=민호
- 목표: 5번 발화, 서술어 `잘 설명했어`, 화자 수아

```text
수아: 발표 끝났네. 준비한 만큼 다 얘기했어?
민호: 응, 근데 마지막 부분에서 시간이 부족해서 좀 급하게 말했어.
수아: 그래도 사례를 먼저 보여준 건 괜찮더라.
민호: 내가 그 부분은 몇 번 고쳤거든. 설명이 너무 길어질까 봐 걱정했어.
수아: 핵심을 짚어서 [[잘 설명했어]]. 마지막에 조금만 천천히 말하면 더 좋겠더라.
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 민호 / role=addressee
- anchor: turn 4 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 4번 마지막 절 주어 민호, 5번은 민호의 발표에 대한 평가.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

## N16

### N16-base (naturalistic, variant=base, pairs=-)

- 인물: P1=지안, P2=현석
- 목표: 3번 발화, 서술어 `내야 돼`, 화자 현석

```text
현석: 과제 제출은 했어?
지안: 아직 안 냈어. 마지막 문제를 못 풀어서 붙잡고 있어.
현석: 오늘까지는 [[내야 돼]]. 일단 푼 것만이라도 올려.
지안: 알겠어. 한 번만 더 보고 바로 올릴게.
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 지안 / role=addressee
- anchor: turn 2 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: obligation(-아야 돼); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 과제를 안 낸 지안에게 하는 재촉.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

## N17

### N17-base (naturalistic, variant=base, pairs=-)

- 인물: P1=예은, P2=도훈
- 목표: 3번 발화, 서술어 `가 보는 게 좋겠어`, 화자 예은

```text
예은: 아까부터 기침하네. 목도 아파?
도훈: 응, 목도 따갑고 어젯밤에는 기침 때문에 잠도 거의 못 잤어.
예은: 오늘은 병원에 [[가 보는 게 좋겠어]].
도훈: 그래야겠다. 점심 먹고 다녀올게.
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 도훈 / role=addressee
- anchor: turn 2 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: suggestion(-는 게 좋겠어); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 기침하는 도훈에게 하는 권유.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

## N18

### N18-base (naturalistic, variant=base, pairs=-)

- 인물: P1=나래, P2=준혁
- 목표: 4번 발화, 서술어 `잘했어`, 화자 준혁

```text
나래: 볶음밥 하다가 바닥을 다 태웠어. 탄 냄새 아직도 나지?
준혁: 조금 나긴 하네. 불을 너무 세게 켰나 봐.
나래: 내가 볶음밥은 오늘 처음 만들어 봤거든. 계란까지 넣고 나니까 정신이 없더라.
준혁: 처음 해 본 것치고는 [[잘했어]].
나래: 그렇게 말해 주니까 좀 낫네. 다음엔 불부터 줄여야겠다.
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 나래 / role=addressee
- anchor: turn 3 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 볶음밥을 태운 나래에 대한 평가.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

## N19

### N19-base (naturalistic, variant=base, pairs=-)

- 인물: P1=시우, P2=하나
- 목표: 4번 발화, 서술어 `붙을 거야`, 화자 시우

```text
하나: 오늘 면허 시험 떨어졌어. 주차하다가 선을 밟았어.
시우: 아, 연습할 땐 잘됐는데 아깝다.
하나: 막상 시험 보니까 너무 긴장되더라. 다음 시험 전에 주차 연습 좀 더 하려고.
시우: 이번에 한 번 해 봤으니까 다음엔 [[붙을 거야]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 하나 / role=addressee
- anchor: turn 3 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: conjecture(-ㄹ 거야); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 면허 시험에 떨어진 하나에 대한 격려.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

## N20

### N20-base (naturalistic, variant=base, pairs=-)

- 인물: P1=혜수, P2=종민, T1=지인(비참여)
- 목표: 5번 발화, 서술어 `결정하는 게 좋겠어`, 화자 혜수

```text
종민: 요즘 이직할까 고민 중이야. 지금 하는 일이 너무 반복되는 것 같아서.
혜수: 그럼 생각해 둔 회사는 있어?
종민: 다른 회사 다니는 지인이 자기 회사를 추천하더라고. 일하는 방식도 여기랑 꽤 다르대.
종민: 그 지인은 지난달에 옮겼는데 벌써 잘 적응했대. 그래서 나도 좀 마음이 기울어.
혜수: 그래도 막상 옮기면 기대했던 거랑 다를 수도 있어. 근무 조건까지 좀 더 알아보고 [[결정하는 게 좋겠어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 종민 / role=addressee
- anchor: turn 4 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: T1 present=True; turn_distance=None; most_recent=T1
- cues: suggestion(-는 게 좋겠어); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 이직을 고민하는 종민에게 하는 조언. 직전 턴에 지인이 언급되어 경쟁 개체. 생성 서술어 '기대했던 거랑 다를 수도 있어'는 주어가 사람이 아니라 같은 발화의 '결정하는 게 좋겠어'로 바꿈.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N21

### N21-base (naturalistic, variant=base, pairs=-)

- 인물: P1=아영, P2=진호
- 목표: 4번 발화, 서술어 `확인해 봐`, 화자 진호

```text
아영: 도로에서는 좀 익숙해졌는데 주차는 아직 너무 어려워.
진호: 주차할 때 어떤 게 제일 헷갈려?
아영: 핸들을 언제 풀어야 할지 모르겠어. 그러다 보니 자꾸 선을 밟아.
진호: 선을 밟았다고 급하게 핸들을 돌리지 말고, 일단 멈춰서 차가 어느 쪽으로 기울었는지 [[확인해 봐]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 아영 / role=addressee
- anchor: turn 3 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: imperative(-해 봐); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 주차를 어려워하는 아영에게 하는 조언.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

## N22

### N22-base (naturalistic, variant=base, pairs=-)

- 인물: P1=미정, P2=태규, T1=조카(비참여), T2=언니(비참여)
- 목표: 5번 발화, 서술어 `금방 적응할 것 같아`, 화자 미정

```text
미정: 우리 조카가 내년에 초등학교에 들어가. 벌써 그렇게 컸나 싶더라.
태규: 그러게, 얼마 전까지 유치원 다닌다고 했던 것 같은데.
미정: 언니는 입학 준비하느라 요즘 바쁘대. 이것저것 알아볼 게 많나 봐.
태규: 조카는 어때? 처음 보는 애들하고도 잘 어울리는 편이야?
미정: 응, 놀이터에서도 먼저 말 걸고 같이 놀더라. 새 학교에서도 [[금방 적응할 것 같아]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 조카 / role=third_party
- anchor: turn 4 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: conjecture(-ㄹ 것 같아); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 4번 주어 조카, 5번도 조카. 언니는 3번에 언급되어 최근성 경쟁은 아님.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

## N23

### N23-base (naturalistic, variant=base, pairs=-)

- 인물: P1=경수, P2=윤정, T1=아들(비참여), T2=남편(비참여)
- 목표: 5번 발화, 서술어 `돌겠네요`, 화자 경수

```text
경수: 요즘 아들이 강아지 산책시키는 모습이 자주 보이더라고요.
윤정: 네, 자기가 맡겠다고 해서 저녁 산책은 아들이 담당해요.
경수: 전에는 남편분도 종종 데리고 다니셨잖아요.
윤정: 남편은 요즘 야근 때문에 바빠서 산책은 아들한테 완전히 맡겼어요.
경수: 그럼 저녁마다 강아지 데리고 동네 한 바퀴씩 [[돌겠네요]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 아들 / role=third_party
- anchor: turn 4 → T2; speaker_changed=True, referent_changed=True, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: conjecture(-겠네요), honorific_speech_level; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_generated_api
- 근거: 4번 마지막 절 주어 남편, 5번 '돌겠네요'는 산책을 맡은 아들. 존댓말 대화.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)
