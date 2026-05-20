# 2026-05-20 CJK Units and Expansion Requests

## Question

Can deterministic issue extraction produce cleaner units for Japanese/Chinese/Korean punctuation and keep positive-review expansion requests from disappearing into generic praise?

## Hypothesis

Many CJK reviews do not include spaces after sentence punctuation. Splitting on `。！？` should make evidence units narrower. Separately, upvoted reviews that say they love the game but want more routes, chapters, endings, or content are planning requests rather than pure praise.

## Data

- Games: Legend of Mortal, Magical Girl Witch Trials, Marfusha:Sentinel Girls
- App IDs: `1859910`, `3101040`, `1456820`
- Review counts: 5,000; 5,000; 3,148
- Analysis run IDs: latest local issue runs were used for the companion focus-evidence check
- Sampling or filters: all stored reviews for each app; CJK punctuation review text and upvoted units

## Baseline

`_split_review_units` only split punctuation when followed by whitespace, so CJK multi-sentence reviews could stay too broad. `_issue_intent` required a negative cue or downvote for requests, so positive reviews asking for more routes or chapters could be classified as praise.

## Change

- Split review units after CJK sentence punctuation even without whitespace.
- Add a narrow expansion-request cue for upvoted reviews that ask for more routes, chapters, content, endings, story, or characters.
- Keep pure positive reviews as praise.

## Results

Quantitative signals:

- broad label rate: not evaluated
- verified match evidence: not changed
- partial/reject distribution: not changed
- language coverage: CJK unit granularity increased on all three pilot games
- duplicate or overlapping issue rate: not evaluated

Pilot read-only measurement:

| App ID | Reviews | Reviews with changed CJK split | Old CJK units | New CJK units | Upvoted expansion request units newly caught |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1859910` | 5,000 | 803 | 7,192 | 8,905 | 65 |
| `3101040` | 5,000 | 974 | 6,795 | 9,054 | 24 |
| `1456820` | 3,148 | 711 | 4,802 | 6,193 | 53 |

Qualitative signals:

- improved examples: `序盤は楽しい。後半は説明不足！それでもキャラは良い。` splits into three units
- improved examples: `I love the story and would love more routes and chapters.` becomes a request
- unchanged examples: `I love the characters and music.` remains praise

## User Feedback

The user asked for continuous logic and case research that improves planner and marketer usefulness.

## Decision

Adopt. The change is deterministic, narrow, and covered by smoke assertions.

## Follow-Up

Measure whether future CJK issue cards produce shorter subissues and fewer mixed evidence snippets.
