# ReviewForge 리뷰 분석 연구 로그

이 문서는 ReviewForge의 Steam 리뷰 분석 로직을 개선하기 위한 연구 기록이다.
목표는 단순한 클러스터 목록이 아니라, 기획자가 실제 의사결정에 사용할 수 있는 다국어 리뷰 기반 이슈 보드를 만드는 것이다.

## 현재 구현 상태 메모

이 문서의 실험 섹션은 당시의 연구 기록이므로 "production 코드는 변경하지 않았다"나 "다음 구현 조건"처럼 과거/미래 시점 표현이 남아 있을 수 있다. 현재 코드에는 이미 `issue_units`, `issues`, `issue_evidence`, `analysis_axes`, `axis_suggestions`, `verifier_verdict`, `summary_ko`가 일부 구현되어 있다.

현재 구현은 완성형 하이브리드 파이프라인이 아니라, 규칙 기반 이슈 생성과 선택적 LM Studio 검증을 포함한 중간 단계다. 코드를 바꿀 때는 아래 연구 결론을 의도 문서로 해석하되, 현재 API와 DB 계약은 `docs/api-contract.md`와 `docs/project-intent.md`를 우선 확인한다.

## 2026-05-20 연구 목적

현재 문제는 다음과 같다.

- 이슈명이 `밸런스/RNG 불만`, `UI/가독성/온보딩 불만`, `호평이 관측된다`처럼 너무 넓다.
- 같은 문제라도 한국어, 영어, 일본어, 중국어 리뷰가 서로 다른 이슈로 갈라진다.
- 각 이슈에 포함된 실제 리뷰 전체를 보기 어렵다.
- 원문만 보여주면 사용자가 모든 언어를 알아야 해서 실무성이 낮다.
- LLM 요약이 근거 리뷰와 얼마나 맞는지 검증하기 어렵다.

따라서 이번 연구의 핵심 질문은 다음이다.

1. 다국어 리뷰를 같은 의미의 이슈로 합칠 수 있는가?
2. 기존의 넓은 카테고리보다 구체적인 기획 이슈를 만들 수 있는가?
3. 실제 리뷰 원문과 번역을 함께 보여줄 수 있는가?
4. LLM이 만든 요약을 근거 리뷰와 연결해 검증할 수 있는가?
5. 어떤 방식이 실패했고, 왜 실패했는가?

## 참고한 방법론

이번 조사에서 확인한 방향은 단순 토픽 모델링이 아니라 하이브리드 파이프라인이다.

- Aspect-Based Sentiment Analysis, ABSA
  - 리뷰에서 단순 긍정/부정을 뽑는 것이 아니라 `aspect`, `opinion`, `sentiment`, `category`를 함께 뽑는다.
  - 참고: https://link.springer.com/article/10.1007/s10462-024-10906-z

- Multilingual embedding
  - 여러 언어 문장을 같은 의미 공간에 놓아 유사도를 계산한다.
  - `intfloat/multilingual-e5-large`는 94개 언어를 지원하고, sentence-transformers로 사용할 수 있다.
  - 참고: https://huggingface.co/intfloat/multilingual-e5-large
  - 참고: https://arxiv.org/abs/2402.05672

- BERTopic 계열 접근
  - embedding, clustering, c-TF-IDF, LLM representation을 조합한다.
  - 중요한 점은 클러스터를 최종 답으로 믿지 않고, 사람이 읽을 수 있는 topic representation으로 후처리한다는 것이다.
  - 참고: https://bertopic.readthedocs.io/en/latest/

- TopicGPT 계열 접근
  - LDA식 단어 뭉치 대신 LLM으로 자연어 토픽명과 설명을 만든다.
  - 단, LLM 출력은 반드시 실제 근거 문장과 연결해야 한다.
  - 참고: https://arxiv.org/abs/2311.01449

- HDBSCAN의 soft clustering/outlier 개념
  - 애매한 문장을 억지로 이슈에 넣지 않고 outlier 또는 검토 필요로 남길 수 있다.
  - 참고: https://hdbscan.readthedocs.io/en/latest/soft_clustering_explanation.html
  - 참고: https://hdbscan.readthedocs.io/en/latest/outlier_detection.html

## 사용한 실제 데이터

이번 실험은 이미 수집된 실제 Steam 리뷰 데이터를 읽기 전용으로 사용했다.

대상 게임:

- Legend of Mortal, app id `1859910`, 최신 분석 run `33`
- Magical Girl Witch Trials, app id `3101040`, 최신 분석 run `34`
- Marfusha:Sentinel Girls, app id `1456820`, 최신 분석 run `35`

리뷰 수:

- Legend of Mortal: 5,000 reviews
- Magical Girl Witch Trials: 5,000 reviews
- Marfusha:Sentinel Girls: 3,148 reviews

실험은 production 로직에 바로 반영하지 않았다.
DB는 읽기 전용으로 조회했고, 별도 임시 Python 실험으로만 검증했다.

## 기준선: 현재 이슈 보드 결과

현재 이슈 보드의 상위 10개 이슈명은 세 게임 모두 전부 넓은 라벨이었다.

| 게임 | 현재 상위 10개 중 넓은 라벨 |
| --- | ---: |
| Legend of Mortal | 10/10 |
| Magical Girl Witch Trials | 10/10 |
| Marfusha:Sentinel Girls | 10/10 |

예시:

- `밸런스/RNG 강점`
- `밸런스/RNG 불만`
- `난이도/진척 강점`
- `UI/가독성/온보딩 불만`
- `반복성/콘텐츠 불만`
- `누락/비교 불만`

판단:

- 현재 방식은 데이터 요약으로는 보일 수 있지만 기획 판단에는 약하다.
- `밸런스`, `UI`, `반복성` 같은 라벨은 최종 이슈명이 아니라 보조 태그로 내려야 한다.
- 이슈명은 `추리 게임인데 마법 규칙이 사건 논리를 무너뜨린다`처럼 판단 가능한 문장이어야 한다.

## 실험 1: 다국어 키워드 기반 canonical bucket

목적:

- 같은 문제가 언어별로 갈라지는지 확인한다.
- 키워드만으로도 다국어 이슈 후보를 어느 정도 합칠 수 있는지 본다.

방법:

- 게임별로 의미 있는 후보 이슈를 사람이 정의했다.
- 각 후보에 한국어, 영어, 일본어, 중국어 키워드를 넣었다.
- 기존 `issue_units`와 원문 리뷰 일부를 대상으로 매칭했다.

주요 결과:

| 게임 | 후보 이슈 | 매칭 unit | unique review | 언어 |
| --- | --- | ---: | ---: | --- |
| Legend of Mortal | route_guidance | 563 | 302 | ko, zh-CN, zh-TW, en, ja |
| Legend of Mortal | update_completion | 505 | 319 | zh-CN, ko, zh-TW, en |
| Magical Girl Witch Trials | mystery_logic | 586 | 295 | ko, zh-CN, ja, en, zh-TW |
| Magical Girl Witch Trials | chapter_replay | 109 | 42 | ko, en, ja, zh-CN |
| Marfusha | short_content | 824 | 409 | en, ja, ko, zh-CN, others |
| Marfusha | weapon_card_rng | 617 | 324 | ja, en, ko, zh-CN, zh-TW |

확인된 점:

- 같은 문제는 실제로 여러 언어에 흩어져 있다.
- 현재 시스템은 이 문제들을 `general`, `balance`, `ui_onboarding`, `progression`, `content_missing` 등으로 쪼갠다.
- 따라서 다국어 통합 layer는 필요하다.

실패와 한계:

- 키워드 방식은 recall은 높지만 precision이 낮다.
- 예를 들어 `ending` 키워드는 분량, 우울한 결말, 루트 분기, 스토리 불만을 한꺼번에 잡을 수 있다.
- Marfusha의 `short_content` 후보는 `분량 부족`, `엔딩 불만`, `반복 피로`가 섞였다.

판단:

- 키워드는 후보 수집용으로는 유용하다.
- 하지만 최종 이슈 확정에는 단독으로 쓰면 안 된다.

## 실험 2: multilingual-e5 + HDBSCAN으로 의견 문장 군집화

목적:

- 키워드 없이 의미 임베딩만으로 다국어 의견 문장이 자연스럽게 합쳐지는지 확인한다.
- 넓은 라벨보다 구체적인 이슈 후보가 나오는지 본다.

방법:

- `issue_units` 중 불만, 버그, 요청, 부정 문장을 샘플링했다.
- `intfloat/multilingual-e5-large`를 RTX 5060 Ti에서 로드했다.
- 각 문장을 `passage:` prefix로 임베딩했다.
- sklearn `HDBSCAN`으로 군집화했다.
- 각 클러스터의 언어 분포, 기존 aspect 분포, evidence 문장을 확인했다.

환경 확인:

- GPU: NVIDIA GeForce RTX 5060 Ti
- embedding model: `intfloat/multilingual-e5-large`
- CUDA 사용 가능

결과:

| 게임 | 샘플 unit | 클러스터 | noise ratio | 다국어 클러스터 | 기존 aspect가 섞인 클러스터 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Legend of Mortal | 773 | 2 | 0.23 | 2 | 1 |
| Magical Girl Witch Trials | 495 | 3 | 0.43 | 1 | 1 |
| Marfusha | 536 | 4 | 0.62 | 2 | 4 |

좋았던 점:

- 현재 상위 이슈 10개가 전부 넓은 라벨이라는 기준선 문제는 명확히 드러났다.
- HDBSCAN의 noise 처리는 유용했다. 애매한 문장을 억지로 분류하지 않았다.
- 일부 클러스터는 현재 aspect 여러 개를 가로질러 묶었다.

실패한 점:

- 순수 임베딩 군집화만으로는 언어 통합이 충분하지 않았다.
- Legend of Mortal은 중국어/번체 위주 클러스터와 한국어/영어 위주 클러스터로 갈라졌다.
- Magical Girl Witch Trials도 중국어, 한국어, 일본어가 충분히 섞이지 않았다.
- Marfusha는 클러스터가 언어별로 갈라지는 경향이 강했다.

LLM 카드 생성 결과:

- Magical Girl Witch Trials:
  - `추리 과정의 정체성과 정보 전달 방식 문제`
  - 기존보다 유의미했다.
- Marfusha:
  - `게임 플레이 시간 대비 콘텐츠 양 및 체감 만족도 불일치`
  - 약간 뭉개졌다. 분량, 전투 속도, 반복 문제가 섞였다.
- Legend of Mortal:
  - `스토리 몰입도 및 콘텐츠 만족도 저하`
  - 기존보다 낫지만 너무 일반적이었다.

판단:

- 순수 `multilingual-e5 + HDBSCAN`은 보조 실험으로는 유용하지만, 최종 솔루션으로는 부족하다.
- 특히 다국어 통합을 자연스럽게 기대하기에는 약하다.
- 언어별 분리 문제를 극복하려면 seed, 번역, LLM 검증 중 하나 이상이 필요하다.

## 실험 3: seed 기반 canonical issue matching

목적:

- 게임별로 기획 이슈 정의를 먼저 만들고, 리뷰 문장이 해당 이슈에 맞는지 semantic matching한다.
- 순수 군집화보다 더 구체적인 이슈를 만들 수 있는지 확인한다.

방법:

- 게임별로 4개 canonical issue seed를 정의했다.
- seed 문장은 한국어와 영어 키워드를 섞어 작성했다.
- `multilingual-e5-large`로 seed는 `query:`, 리뷰 문장은 `passage:`로 임베딩했다.
- top score와 margin 기준으로 확신이 낮은 문장은 `ambiguous`로 제외했다.

결과:

| 게임 | 샘플 unit | assigned | ambiguous ratio |
| --- | ---: | ---: | ---: |
| Legend of Mortal | 773 | 154 | 0.80 |
| Magical Girl Witch Trials | 495 | 60 | 0.88 |
| Marfusha | 536 | 82 | 0.85 |

좋았던 사례:

- Legend of Mortal, `update_completion`
  - units: 119
  - unique reviews: 110
  - languages: ko, zh-CN, zh-TW
  - 내용: 미완성, 업데이트 지연, 약속된 후속 콘텐츠 부족

- Magical Girl Witch Trials, `mystery_logic_magic`
  - units: 20
  - unique reviews: 14
  - languages: ko, ja
  - 내용: 마법으로 트릭을 얼버무려 추리 논리가 납득되지 않음

- Marfusha, `bleak_ending_tone`
  - units: 66
  - unique reviews: 55
  - languages: ko, ja, en, pt-BR, zh-TW, es
  - 내용: 엔딩이 지나치게 우울하고 구원이 부족하다는 반응

실패한 사례:

- Legend of Mortal, `route_story_choice`
  - units: 12
  - 전부 한국어로 잡혔다.
  - 다국어 통합 효과가 약했다.

- Magical Girl Witch Trials, `chapter_replay_flow`
  - 렉, 로딩, BAD END, 선택지 불만이 섞였다.
  - seed 정의가 너무 넓거나 evidence 검증이 부족했다.

- Marfusha, `short_content_loop`
  - units: 4만 high confidence로 잡혔다.
  - 실제로는 분량 부족 리뷰가 많지만 embedding margin 조건이 너무 보수적이었다.

LLM 카드 생성 실패:

- seed 하나당 카드 하나를 기대했지만, LLM이 근거 문장별로 여러 카드를 만들었다.
- `evidence_risk`에 seed 설명 문자열을 그대로 넣는 등 형식 오류가 있었다.
- Legend of Mortal은 긍정 문장을 근거로 잡아 불만 이슈 카드가 흐려졌다.

판단:

- seed 기반 matching은 precision을 올리는 데 효과가 있다.
- 하지만 recall이 너무 낮다.
- 이 방식만 쓰면 중요한 불만을 많이 놓친다.
- LLM 카드 생성은 반드시 엄격한 JSON schema, 카드 수 제한, evidence role 제한이 필요하다.

## 현재까지의 결론

실증 결과, 제안 방향은 일부 맞았지만 그대로는 부족하다.

버려야 할 접근:

- 순수 TF-IDF/KMeans 클러스터링
- 순수 multilingual embedding/HDBSCAN 클러스터링
- 키워드만으로 이슈 확정
- LLM에게 evidence 없이 바로 요약 요청
- LLM에게 자유 형식으로 카드 생성 요청

살릴 접근:

- opinion unit 단위 분석
- multilingual keyword recall
- multilingual-e5 semantic matching
- ambiguous/noise 분리
- LLM 기반 이슈명/요약 생성
- 실제 리뷰 ID 연결
- 한국어 번역 캐시

## 개선된 가설: hybrid issue pipeline

다음 방식이 가장 현실적이다.

1. Opinion unit extraction
   - 리뷰 전체가 아니라 문장/의견 단위로 쪼갠다.
   - 현재 `issue_units` 구조는 이 기반으로 사용할 수 있다.

2. Candidate recall
   - 게임/장르별 seed issue registry를 둔다.
   - 다국어 키워드와 regex로 후보를 넓게 수집한다.
   - 이 단계는 recall 우선이다.

3. Semantic filtering
   - 후보 문장과 issue seed를 `multilingual-e5-large`로 비교한다.
   - score, margin, 현재 aspect, intent, vote 정보를 함께 본다.
   - 확신 낮은 문장은 `ambiguous`로 보낸다.

4. LLM verifier
   - LLM에게 카드 생성을 바로 맡기지 않는다.
   - 먼저 각 evidence가 canonical issue에 맞는지 `match`, `partial`, `reject`로 판정하게 한다.
   - 이때 JSON schema를 강제해야 한다.

5. Issue reducer
   - 같은 canonical issue 안에서 subissue를 나눈다.
   - 예: Marfusha `short_content`는 `분량 부족`, `반복 피로`, `우울한 엔딩`으로 분리되어야 한다.

6. Evidence audit
   - 한 이슈당 같은 리뷰는 한 번만 대표 evidence로 쓴다.
   - 언어가 한쪽에 몰리면 경고를 붙인다.
   - 추천 리뷰 속 불만인지, 비추천 리뷰 핵심 불만인지 구분한다.

7. LLM issue card generation
   - 검증된 evidence만 넣는다.
   - 카드 수를 명시한다.
   - 출력은 schema로 제한한다.
   - 금지어: `호평이 관측된다`, `불만이 반복된다`, `관련 의견이 있다`.

8. Translation cache
   - UI에서는 한국어 번역/요약을 기본으로 보여준다.
   - 원문은 접어서 볼 수 있게 한다.
   - 번역은 모든 리뷰에 미리 돌리지 않고, 사용자가 여는 evidence부터 lazy translation한다.

## 다음 실증 기준

다음 파일럿은 production 적용 전에 아래 기준으로 통과 여부를 본다.

정량 기준:

- 현재 상위 10개 중 넓은 라벨 비율을 10/10에서 3/10 이하로 줄인다.
- 이슈 카드별 대표 evidence는 unique review 비율 100%를 유지한다.
- 주요 이슈는 2개 이상 언어에서 evidence를 확보한다.
- ambiguous/noise 비율을 기록하고 억지 배정을 하지 않는다.
- 같은 의미의 이슈 중복률을 사람이 검수했을 때 20% 이하로 낮춘다.

정성 기준:

- 사용자가 읽고 `그래서 뭐?`라는 느낌이 줄어야 한다.
- 각 카드가 `기획 판단`으로 이어져야 한다.
- 원문 리뷰를 열어봤을 때 카드 내용과 모순되지 않아야 한다.
- 한국어 번역만 읽어도 대략 판단 가능해야 한다.
- 긍정 리뷰 속 불만과 부정 리뷰 핵심 불만을 구분해야 한다.

## 다음 작업 제안

바로 전체 시스템에 적용하지 말고, 세 게임만 대상으로 파일럿을 만든다.

파일럿 산출물:

- 게임당 5개 canonical issue
- 이슈당 검증된 evidence 8개
- evidence별 한국어 번역/요약
- 원문 보기
- LLM verifier 결과
- 현재 이슈 보드와 새 이슈 보드 비교

이 파일럿을 사용자가 직접 보고, 쓸모 있다고 느껴지는지 판단한 뒤 production 적용으로 넘어간다.

## 실험 4: 후보 수집 + 의미 필터 + LLM verifier 검증

목적:

- 앞선 결론인 `후보 수집 → semantic filtering → LLM verifier → card generation`이 실제로 이전 방식보다 나은지 확인한다.
- 단순히 좋은 문장을 만드는 것이 아니라, 잘못된 근거를 `reject` 또는 `partial`로 걸러낼 수 있는지 확인한다.

방법:

- production 코드는 변경하지 않았다.
- DB는 읽기 전용으로 조회했다.
- 각 게임에서 1~2개의 canonical issue를 골랐다.
- 다국어 regex로 후보를 넓게 수집했다.
- `intfloat/multilingual-e5-large`로 seed issue와 후보 문장의 의미 유사도를 계산했다.
- 점수가 높은 후보를 언어 다양성을 유지하면서 뽑았다.
- LM Studio `supergemma4-e4b-abliterated`에게 각 후보를 `match`, `partial`, `reject`로 판정하게 했다.
- `match`만 사용해 이슈 카드 1개를 생성했다.

검증 대상:

| 게임 | 검증 이슈 |
| --- | --- |
| Legend of Mortal | 업데이트 지연/미완성 콘텐츠 |
| Magical Girl Witch Trials | 추리 논리/마법 규칙 납득성 |
| Marfusha | 짧은 분량/반복 보상 부족 |
| Marfusha | 우울한 엔딩 톤/구원 부족 |

결과:

| 게임 | 이슈 | regex 후보 | LLM 검증 후보 | match | partial | reject | match 언어 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Legend of Mortal | 업데이트 지연/미완성 콘텐츠 | 320 | 15 | 15 | 0 | 0 | ko, zh-CN, zh-TW |
| Magical Girl Witch Trials | 추리 논리/마법 규칙 납득성 | 370 | 13 | 9 | 2 | 2 | ko, zh-CN, ja |
| Marfusha | 짧은 분량/반복 보상 부족 | 342 | 16 | 16 | 0 | 0 | ko, en, ja, zh-CN |
| Marfusha | 우울한 엔딩 톤/구원 부족 | 230 | 12 | 10 | 1 | 1 | ja, ko, en, zh-TW |

좋았던 점:

- 기존 방식이 `밸런스/RNG`, `반복성/콘텐츠`, `general` 같은 넓은 라벨만 만들던 문제를 줄였다.
- 같은 이슈에 여러 언어 evidence가 모였다.
- Magical Girl Witch Trials에서 generic한 비난 문장과 애매한 문장을 `reject`/`partial`로 분리했다.
- Marfusha의 우울한 엔딩 이슈에서 `엔딩 반복이 지루하다`는 문장을 `partial`로, 단순 반복 불만은 `reject`로 분리했다.
- 생성된 카드는 `호평이 관측된다`보다 훨씬 기획 판단에 가까웠다.

생성 카드 예시:

- Legend of Mortal
  - `히로인 루트 미완성 및 게임 완성도 부족`
  - 핵심: 히로인 루트가 미완성이고 메인 스토리 공백이 느껴진다는 근거가 다국어 리뷰에서 확인됨.

- Magical Girl Witch Trials
  - `추리 논리 및 마법 규칙의 납득성 문제`
  - 핵심: 말이 안 되는 범죄를 마법으로 덮거나, 증거와 트릭 연결이 납득되지 않는다는 근거가 확인됨.

- Marfusha, 반복/분량
  - `게임의 반복성과 콘텐츠 양에 대한 피로감`
  - 핵심: 엔딩 수집 외에 동기가 약하고, 다회차가 단조롭다는 근거가 확인됨.

- Marfusha, 엔딩 톤
  - `엔딩 톤의 불만족 및 구원 부족 문제`
  - 핵심: 해피엔딩 선호자에게는 맞지 않고, 좋은 엔딩조차 우울하다는 반응이 여러 언어에서 확인됨.

실패와 위험:

- 한 번에 16개 evidence를 넣은 Marfusha 엔딩 톤 검증에서 LM Studio가 잘못된 JSON을 출력했다.
- 같은 이슈를 6개씩 작은 배치로 나누자 JSON 파싱에 성공했다.
- 따라서 production 구현은 반드시 작은 배치, 재시도, schema validation, raw output 저장이 필요하다.
- LLM 카드의 `evidence_risk`가 가끔 review id가 아니라 `Evidence 1` 같은 임시 번호를 참조했다.
- production에서는 반드시 실제 `review_id`와 `unit_id`를 넣어야 한다.
- verifier가 너무 관대해질 위험이 있다. Legend와 Marfusha 반복 이슈는 뽑힌 후보가 좋아서 전부 `match`였지만, 이게 모든 게임에서 안정적으로 유지된다는 보장은 없다.
- seed issue 정의가 품질을 크게 좌우한다.

판단:

- 이번 실험은 앞선 제안을 지지한다.
- 순수 clustering보다 `candidate recall + semantic filtering + LLM verifier`가 실제 기획 이슈에 더 가깝다.
- 특히 `reject`와 `partial` 단계가 근거 품질을 높이는 데 중요하다.
- 다만 전체 자동화로 바로 넣기보다는, production 전 파일럿으로 게임당 5개 이슈만 먼저 보여줘야 한다.

다음 구현 조건:

- verifier 입력은 5~8개 evidence 단위로 쪼갠다.
- JSON schema 검증에 실패하면 같은 batch를 1회 재시도한다.
- 실패한 raw output은 저장한다.
- 최종 카드에는 반드시 `review_id`, `unit_id`, `language`, `voted_up`, `summary_ko`, `original_text`를 연결한다.
- `partial` evidence는 최종 카드 근거에 넣지 않고 보조 탭에 둔다.
- `reject` evidence는 저장하되 UI에는 기본 숨김 처리한다.
- 이슈 카드는 `match` evidence가 최소 5개 이상일 때만 확정한다.

## 강점 피드백을 함께 다루는 원칙

사용자 피드백:

- 기획자 입장에서는 불만과 문제점만 중요한 것이 아니다.
- 좋은 피드백도 유지해야 할 재미, 후속작에서 강화할 방향, 마케팅 문구, 스토어 페이지 메시지, 패치 노트의 강조점으로 활용할 수 있다.

판단:

- 맞는 지적이다.
- `issue board`라는 이름은 문제 중심으로 들리므로 UI에서는 `인사이트 보드`로 다루는 편이 낫다.
- 불만 카드는 `수정/완화/검토`로 이어지고, 강점 카드는 `유지/확장/홍보/후속작 기준`으로 이어져야 한다.

구현 원칙:

- `complaint`, `bug`, `request`는 문제/개선 카드로 본다.
- `praise`는 강점 카드가 아니라 `활용 포인트`로 표시한다.
- 강점 카드도 반드시 실제 추천 리뷰 evidence와 연결한다.
- 단순히 `호평이 관측된다`라고 쓰지 않는다.
- 강점 카드의 `design_decision`은 다음 중 하나로 작성한다.
  - 유지해야 할 핵심 재미
  - 후속작/패치에서 확장할 축
  - 스토어/마케팅 문구에 쓸 수 있는 실제 유저 표현
  - 불만 리뷰에서도 함께 인정되는 강점

주의:

- 부정 리뷰 안에도 긍정 문장이 섞일 수 있고, 긍정 리뷰 안에도 불만 문장이 섞일 수 있다.
- 따라서 카드 intent와 evidence 문장 의미가 맞지 않으면 `match`가 아니라 `partial`로 낮춰야 한다.
- 예를 들어 complaint 카드에 순수 칭찬 문장이 들어가면 잡음이다.
- 반대로 praise 카드에 순수 불만 문장이 들어가도 잡음이다.
