# Pilot Review

대화를 먼저 읽고 생략 주어를 판단한 뒤, '작성자 라벨'을 펼쳐 비교한다. 작성자 라벨은 검수 전 후보값이다.

## 자동 검증 요약

- 표본 20개, 오류 0, 경고 2, 사람 검수 표시 20

| 축 | 분포 |
|---|---|
| by_dataset | {"controlled": 17, "naturalistic": 3} |
| by_role | {"None": 1, "addressee": 4, "speaker": 4, "third_party": 11} |
| by_referent_changed | {"False": 13, "None": 3, "True": 4} |
| by_speaker_changed | {"False": 1, "None": 2, "True": 17} |
| by_distractor_present | {"False": 15, "True": 5} |
| by_turn_distance | {"0": 2, "1": 5, "3": 3, "5": 1, "None": 9} |
| by_n_participants | {"2": 17, "3": 3} |

## S01

### S01-base (controlled, variant=base, pairs=S01:base~distractor)

- 인물: P1=지은, P2=현우, T1=민수(비참여), T2=서연(비참여)
- 목표: 4번 발화, 서술어 `바쁘대`, 화자 현우

```text
지은: 서연이 결혼식 때 보고 민수 못 봤네. 요즘 어떻게 지낸대?
현우: 지난주에 봤는데, 회사 옮겼대.
지은: 그럼 이제 출퇴근은 좀 편해졌겠네?
현우: 응, 그렇다고 하더라. 요즘 많이 [[바쁘대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 민수 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=3; most_recent=T1
- cues: hearsay_ending(-대); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 대화 주제가 민수의 근황이고 3번 발화의 생략 주어도 민수다. 서연은 1번 발화 앞부분에서만 언급되어 최근성 경쟁 개체가 아니다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### S01-distractor (controlled, variant=distractor, pairs=S01:base~distractor,S01:distractor~shift)

- 인물: P1=지은, P2=현우, T1=민수(비참여), T2=서연(비참여)
- 목표: 4번 발화, 서술어 `바쁘대`, 화자 현우

```text
지은: 민수 요즘 어떻게 지낸대? 한참 못 봤네.
현우: 지난주에 봤는데, 회사 옮겼대. 서연이가 소개해 준 데래.
지은: 그럼 이제 출퇴근은 좀 편해졌겠네?
현우: 응, 그렇다고 하더라. 요즘 많이 [[바쁘대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 민수 / role=third_party
- anchor: turn 3 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T2 present=True; turn_distance=3; most_recent=T2
- cues: hearsay_ending(-대); manipulated: distractor; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 서연이 2번 발화에서 민수보다 뒤에 언급되지만 '출퇴근이 편해졌겠네'의 주어는 회사를 옮긴 민수이므로 정답은 유지된다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

### S01-shift (controlled, variant=shift, pairs=S01:distractor~shift)

- 인물: P1=지은, P2=현우, T1=민수(비참여), T2=서연(비참여)
- 목표: 4번 발화, 서술어 `바쁘대`, 화자 현우

```text
지은: 민수 요즘 어떻게 지낸대? 한참 못 봤네.
현우: 지난주에 봤는데, 회사 옮겼대. 서연이가 소개해 준 데래.
지은: 서연이는 아직 거기 다녀?
현우: 응, 그렇다고 하더라. 요즘 많이 [[바쁘대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 서연 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T2
- cues: hearsay_ending(-대); manipulated: referent_shift; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 발화가 서연의 근황을 묻고 4번 발화가 그 답이므로 '바쁘대'의 주어는 서연이다. 민수로 읽힐 가능성은 검수에서 확인한다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

## S02

### S02-addressee (controlled, variant=base, pairs=S02:base~speaker)

- 인물: P1=수아, P2=준호, T1=민수(비참여)
- 목표: 3번 발화, 서술어 `고생 많았다`, 화자 수아

```text
수아: 이번 발표 자료, 네가 거의 다 만들었다며?
준호: 응, 어제 밤새워서 겨우 끝냈어.
수아: 진짜 [[고생 많았다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 준호 / role=addressee
- anchor: turn 2 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 2번 발화에서 준호가 밤샘했다고 했고 3번 발화는 그에 대한 수아의 반응이므로 '고생 많았다'의 주어는 청자 준호다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### S02-speaker (controlled, variant=speaker, pairs=S02:base~speaker,S02:speaker~third)

- 인물: P1=수아, P2=준호, T1=민수(비참여)
- 목표: 2번 발화, 서술어 `고생 많았다`, 화자 수아

```text
준호: 발표 자료는 다 끝냈어?
수아: 응, 어제 밤새 혼자 다 했어. 진짜 [[고생 많았다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 수아 / role=speaker
- anchor: turn 1 → P1; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: evaluative_exclamation, same_turn_prior_clause; manipulated: speaker_role; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 같은 발화 앞 절에서 화자가 혼자 다 했다고 했으므로 '고생 많았다'는 화자 자신에 대한 감탄이다. 1번 발화 '끝냈어?'의 생략 주어는 청자인 수아(=P1).

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### S02-third (controlled, variant=third, pairs=S02:speaker~third)

- 인물: P1=수아, P2=준호, T1=민수(비참여)
- 목표: 2번 발화, 서술어 `고생 많았다`, 화자 수아

```text
준호: 발표 자료는 다 끝났어?
수아: 응, 민수가 어제 밤새 혼자 다 했대. 진짜 [[고생 많았다]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 민수 / role=third_party
- anchor: turn None → None; speaker_changed=None, referent_changed=None, role_changed=None
- distractor: None present=False; turn_distance=0; most_recent=T1
- cues: evaluative_exclamation, same_turn_prior_clause, hearsay_in_prior_clause; manipulated: referent_shift; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 앞 절에서 민수가 밤샘했다고 전했으므로 '고생 많았다'는 민수에 대한 평가다. 1번 발화 '끝났어?'의 주어는 자료(비인간)라 anchor를 두지 않는다.

</details>

검증 표시: warning:ANCHOR_MISSING(controlled sample without anchor: shift variables are None); review:HUMAN_REVIEW(gold_unverified)

## S03

### S03-vocative (controlled, variant=base, pairs=S03:base~novocative)

- 인물: P1=하늘, P2=태양, P3=보라
- 목표: 5번 발화, 서술어 `정해 줘`, 화자 하늘

```text
하늘: 보라야, 이번 주말에 시간 돼?
보라: 토요일은 안 되고 일요일은 괜찮아.
하늘: 태양이 너는?
태양: 나도 일요일이 좋아.
하늘: 그럼 일요일에 보자. 보라야, 장소 좀 [[정해 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 보라 / role=addressee
- anchor: turn 4 → P2; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: None present=False; turn_distance=0; most_recent=P3
- cues: vocative, imperative(-해 줘); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 호격 '보라야'로 청자가 보라임이 확정되고 명령형의 주어는 청자다. 직전 화자 태양이 최근성 경쟁 개체다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,multi_party_addressee)

### S03-novocative (controlled, variant=novocative, pairs=S03:base~novocative)

- 인물: P1=하늘, P2=태양, P3=보라
- 목표: 5번 발화, 서술어 `정해 줘`, 화자 하늘

```text
하늘: 보라야, 이번 주말에 시간 돼?
보라: 토요일은 안 되고 일요일은 괜찮아.
하늘: 태양이 너는?
태양: 나도 일요일이 좋아.
하늘: 그럼 일요일에 보자. 장소 좀 [[정해 줘]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: None (없음) / role=None
- anchor: turn 4 → P2; speaker_changed=True, referent_changed=None, role_changed=None
- distractor: None present=True; turn_distance=None; most_recent=P2
- cues: imperative(-해 줘); manipulated: linguistic_cue; expected_gold_change=None
- 상태: ambiguity=ambiguous, annotation=candidate, creation=llm_authored
- 근거: 호격이 없으면 청자가 직전 화자 태양(인접쌍)일 수도, 보라일 수도 있다. 임의로 정답을 주지 않고 모호 사례로 둔다. 평가셋에서 제외된다.

</details>

검증 표시: review:HUMAN_REVIEW(multi_party_addressee,distractor_check_gold_still_unique)

## S04

### S04-base (controlled, variant=base, pairs=S04:base~distractor)

- 인물: P1=엄마, P2=유진, T1=아빠(비참여), T2=이모(비참여)
- 목표: 4번 발화, 서술어 `올라오신대`, 화자 유진

```text
엄마: 아빠는 오늘 회식이라 늦으신대. 우리 먼저 먹자.
유진: 알았어. 아, 아까 이모한테 전화 왔었어.
엄마: 이모가? 무슨 일로?
유진: 다음 주에 [[올라오신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 이모 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T2
- cues: honorific(-시-), hearsay_ending(-대); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 3번 발화가 이모의 전화 용건을 물었고 4번 발화가 그 답이다. 높임은 아빠에게도 해당하므로 구분 단서가 아니다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### S04-distractor (controlled, variant=distractor, pairs=S04:base~distractor)

- 인물: P1=엄마, P2=유진, T1=아빠(비참여), T2=이모(비참여)
- 목표: 4번 발화, 서술어 `올라오신대`, 화자 유진

```text
엄마: 이모한테 아까 전화 왔었다며? 무슨 일이래?
유진: 잠깐만, 아빠한테 답장만 먼저 하고. 오늘 회식이라 늦으신대.
엄마: 알았어. 그래서, 뭐래?
유진: 다음 주에 [[올라오신대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 이모 / role=third_party
- anchor: turn 3 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: T1 present=True; turn_distance=3; most_recent=T1
- cues: honorific(-시-), hearsay_ending(-대); manipulated: distractor; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 아빠가 2번 발화에서 더 최근에 언급되고 '늦으신대'의 주어이기도 하지만, 3번 발화 '뭐래?'가 이모의 용건으로 되돌아가므로 정답은 이모다. 경쟁이 강해 검수가 중요하다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)

## S05

### S05-addressee (controlled, variant=base, pairs=S05:base~speaker)

- 인물: P1=민재, P2=소희
- 목표: 3번 발화, 서술어 `와야 돼`, 화자 민재

```text
민재: 오늘 또 늦었네. 무슨 일 있었어?
소희: 버스를 놓쳤어. 미안.
민재: 내일은 좀 일찍 [[와야 돼]]. 아침에 리허설 있어.
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 소희 / role=addressee
- anchor: turn 2 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: obligation(-아야 돼); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 늦은 사람은 소희이고 3번 발화는 그에 대한 민재의 요구이므로 주어는 청자 소희다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### S05-speaker (controlled, variant=speaker, pairs=S05:base~speaker)

- 인물: P1=민재, P2=소희
- 목표: 2번 발화, 서술어 `와야 돼`, 화자 민재

```text
소희: 내일 리허설 몇 시부터야?
민재: 아홉 시. 근데 음향 세팅을 맡아서, 내일은 좀 일찍 [[와야 돼]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 민재 / role=speaker
- anchor: turn None → None; speaker_changed=None, referent_changed=None, role_changed=None
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: obligation(-아야 돼), same_turn_prior_clause; manipulated: speaker_role; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 앞 절 '음향 세팅을 맡아서'의 주어가 화자이고 그 이유로 일찍 와야 하는 사람도 화자다. 1번 발화의 주어는 리허설(비인간)이라 anchor 없음.

</details>

검증 표시: warning:ANCHOR_MISSING(controlled sample without anchor: shift variables are None); review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

## S06

### S06-d1 (controlled, variant=base, pairs=S06:base~d5)

- 인물: P1=다은, P2=시우, T1=지훈 선배(비참여)
- 목표: 2번 발화, 서술어 `읽었나 봐`, 화자 시우

```text
다은: 지훈 선배한테 자료 보내 달라고 했어?
시우: 응, 어제 메시지 보냈는데 아직 안 [[읽었나 봐]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지훈 선배 / role=third_party
- anchor: turn 1 → P2; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: conjecture(-나 봐); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 메시지를 받은 쪽이 선배이므로 읽지 않은 사람도 선배다. 1번 발화 '했어?'의 주어는 청자 시우.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### S06-d5 (controlled, variant=d5, pairs=S06:base~d5)

- 인물: P1=다은, P2=시우, T1=지훈 선배(비참여)
- 목표: 6번 발화, 서술어 `읽었나 봐`, 화자 시우

```text
다은: 지훈 선배한테 자료 보내 달라고 했어?
시우: 응, 어제 메시지 보냈어.
다은: 그 자료 없으면 이번 주 발표 못 하는데.
시우: 나도 알아. 일단 지난 학기 자료로 초안은 만들고 있어.
다은: 그래, 그거라도 먼저 해 두자.
시우: 근데 아직 안 [[읽었나 봐]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 지훈 선배 / role=third_party
- anchor: turn 4 → P2; speaker_changed=False, referent_changed=True, role_changed=True
- distractor: None present=False; turn_distance=5; most_recent=T1
- cues: conjecture(-나 봐); manipulated: context_distance; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 선배 언급이 1번 발화에만 있고 그 사이 턴은 발표 준비 이야기라 새 인물이 없다. 5번 발화 '해 두자'는 복수 주어라 anchor에서 건너뛰고 4번 발화(시우)를 anchor로 둔다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

## S07

### S07-hearsay (controlled, variant=base, pairs=S07:base~plain)

- 인물: P1=세진, P2=도현, T1=윤아(비참여)
- 목표: 2번 발화, 서술어 `결정 못 했대`, 화자 도현

```text
세진: 윤아는 유학 가기로 확정했어?
도현: 아니, 아직 [[결정 못 했대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 윤아 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: hearsay_ending(-대); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 질문의 주어 윤아가 답의 주어로 이어지고 전문 어미가 이를 뒷받침한다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

### S07-speaker (controlled, variant=speaker, pairs=S07:speaker~plain)

- 인물: P1=세진, P2=도현, T1=윤아(비참여)
- 목표: 2번 발화, 서술어 `결정 못 했어`, 화자 도현

```text
세진: 너는 유학 가기로 확정했어?
도현: 아니, 아직 [[결정 못 했어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P2 도현 / role=speaker
- anchor: turn 1 → P2; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: plain_ending(-어); manipulated: speaker_role; expected_gold_change=True
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 질문이 청자(도현)에 대한 것이고 답은 도현 자신에 대한 것이다. 1번 발화 기준 도현은 청자, 2번 발화 기준 화자라 역할이 바뀐다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention)

### S07-plain (controlled, variant=plain, pairs=S07:base~plain,S07:speaker~plain)

- 인물: P1=세진, P2=도현, T1=윤아(비참여)
- 목표: 2번 발화, 서술어 `결정 못 했어`, 화자 도현

```text
세진: 윤아는 유학 가기로 확정했어?
도현: 아니, 아직 [[결정 못 했어]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T1 윤아 / role=third_party
- anchor: turn 1 → T1; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=False; turn_distance=1; most_recent=T1
- cues: plain_ending(-어); manipulated: linguistic_cue; expected_gold_change=False
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 질문이 윤아에 대한 것이므로 답의 주어도 윤아다. 전문 어미 없이도 문맥이 결정하는지를 본다. 도현 자신으로 읽힐 여지가 있는지 검수 필요.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified)

## N01

### N01-01 (naturalistic, variant=base, pairs=-)

- 인물: P1=나래, P2=재훈, T1=사장님(비참여)
- 목표: 6번 발화, 서술어 `말 안 했어`, 화자 나래

```text
재훈: 너 요즘 카페 알바 계속해?
나래: 응, 근데 다음 달까지만 하려고.
재훈: 왜? 사장님이랑 잘 지낸다며.
나래: 잘 지내지. 그건 문제가 아니고, 학기 시작하면 시간이 안 나.
재훈: 아, 그렇구나. 사장님은 뭐라셔?
나래: 아직 [[말 안 했어]]. 이번 주에 얘기하려고.
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P1 나래 / role=speaker
- anchor: turn 5 → T1; speaker_changed=True, referent_changed=True, role_changed=True
- distractor: None present=True; turn_distance=None; most_recent=T1
- cues: honorific_absence; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: '사장님은 뭐라셔?'에 대한 답으로 '(내가) 아직 말 안 했어'. 사장님이 주어라면 '말씀 안 하셨어'처럼 높임이 쓰였을 것이라 높임 부재가 단서가 된다. 사장님이 더 최근에 언급되어 경쟁 개체다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,distractor_check_gold_still_unique)

## N02

### N02-01 (naturalistic, variant=base, pairs=-)

- 인물: P1=유나, P2=건우, P3=서준
- 목표: 4번 발화, 서술어 `보내 줄 수 있어`, 화자 건우

```text
유나: 축제 부스 신청서 누가 낼 거야?
건우: 내가 낼게. 근데 양식이 어디 있는지 모르겠어.
서준: 학생회 홈페이지에 있어. 어제 봤어.
건우: 링크 좀 [[보내 줄 수 있어]]?
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: P3 서준 / role=addressee
- anchor: turn 3 → P3; speaker_changed=True, referent_changed=False, role_changed=True
- distractor: None present=False; turn_distance=None; most_recent=None
- cues: request(-줄 수 있어), adjacency; manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 링크를 아는 사람은 직전 발화자 서준이므로 요청의 상대(주어)는 서준이다. 호격이 없어 3인 대화 청자 판정은 검수가 필요하다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,deictic_no_text_mention,multi_party_addressee)

## N03

### N03-01 (naturalistic, variant=base, pairs=-)

- 인물: P1=하준, P2=예린, T1=형(비참여), T2=형수(비참여)
- 목표: 6번 발화, 서술어 `가 있기로 했대`, 화자 하준

```text
예린: 이번 주말에 이사 도와주러 간다며? 누구네?
하준: 우리 형. 형수님이 둘째 낳고 나서 집이 좁다고 해서 옮기는 거야.
예린: 둘째도 있었어? 몰랐네.
하준: 응, 지난달에 태어났어. 아무튼 형이 짐이 많아서 하루 종일 걸릴 것 같아.
예린: 형수님은 괜찮으셔? 아기 낳은 지 얼마 안 됐잖아.
하준: 아직 몸이 다 안 회복돼서 그날은 친정에 [[가 있기로 했대]].
```

<details><summary>작성자 라벨 (검수 전)</summary>

- gold: T2 형수 / role=third_party
- anchor: turn 5 → T2; speaker_changed=True, referent_changed=False, role_changed=False
- distractor: None present=True; turn_distance=None; most_recent=T1
- cues: lexical(친정), hearsay_ending(-대); manipulated: -; expected_gold_change=None
- 상태: ambiguity=unreviewed, annotation=candidate, creation=llm_authored
- 근거: 5번 발화가 형수의 상태를 물었고 6번 발화가 답이다. '친정'이 강한 어휘 단서라 문맥 추적 없이도 풀릴 수 있음을 기록한다.

</details>

검증 표시: review:HUMAN_REVIEW(gold_unverified,distractor_check_gold_still_unique)
