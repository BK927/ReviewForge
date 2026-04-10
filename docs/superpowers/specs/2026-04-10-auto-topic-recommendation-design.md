# Auto Topic Recommendation Design

## Overview

`Topics per group`를 사용자가 감으로 정해야 하는 현재 UI를 개선한다. 앞으로는 사용자가 `Auto (recommended)` 또는 `Manual` 중 하나를 선택할 수 있게 하고, `Auto`를 선택한 경우 분석 파이프라인이 실행되는 동안 추천 토픽 수를 계산해 실제 분석에 사용한다.

이번 설계의 목표는 추천값을 "그럴듯한 기본값"이 아니라, 반복 실행 안정성과 군집 품질을 기준으로 방어 가능한 값으로 만드는 것이다. 동시에 추천 계산 때문에 분석 시작 전 UX가 멈추지 않도록, 추천값 계산은 분석 진행 단계 안에 포함하고 프로그레스 UI에 명시적으로 노출한다.

## Goals

- 사용자가 `Auto`와 `Manual` 모드 중 하나를 선택할 수 있게 한다.
- `Auto` 모드에서는 분석 중 추천 토픽 수를 계산해 KMeans에 사용한다.
- 추천값 계산 과정을 프로그레스바 단계에 포함해 사용자가 기다리는 이유를 이해할 수 있게 한다.
- 분석 결과에 실제 사용된 토픽 수와 추천 근거를 남겨, 이후 수동 조정의 기준점으로 활용할 수 있게 한다.
- 추천 로직은 "한 번 점수가 높았던 k"가 아니라 "여러 번 흔들어도 안정적인 k"를 우선하도록 설계한다.

## Non-Goals

- 분석 시작 전에 정밀 추천값을 미리 계산해 즉시 표시하는 UX는 이번 범위에 포함하지 않는다.
- Tier 1의 HDBSCAN 동작을 수동 토픽 수 입력으로 덮어쓰지 않는다.
- 절대적으로 정답인 토픽 수를 찾는 것은 목표가 아니다. 이번 설계는 사용 가능한 시간 안에서 설명 가능한 추천값을 산출하는 데 집중한다.

## User Experience

### Control Model

- 토픽 수 UI를 숫자 입력 하나에서 `mode + value` 구조로 바꾼다.
- 기본 선택은 `Auto (recommended)`로 둔다.
- `Manual`을 선택한 경우에만 숫자 입력을 활성화한다.
- `Auto`를 선택한 경우 실행 전에는 숫자를 강제로 보여주지 않고, "분석 중 데이터 기준으로 자동 추천"이라는 안내 문구를 보여준다.

### Tier Behavior

- Tier 0에서는 `Auto`와 `Manual` 모두 지원한다.
- Tier 1에서는 HDBSCAN이 이미 토픽 수를 자동 결정하므로, 수동 토픽 수 입력을 비활성화한다.
- Tier 1 UI에는 "Auto by HDBSCAN" 같은 설명을 표시해 사용자가 토픽 수를 직접 조정할 수 없는 이유를 이해할 수 있게 한다.

### Progress UX

`Auto + Tier 0`일 때 프로그레스 단계는 아래 순서를 따른다.

1. `Loading reviews from database...`
2. `Generating embeddings...`
3. `Calculating recommended topic count...`
4. `Clustering reviews...`
5. `Extracting keywords...`
6. `Analysis complete`

`Manual + Tier 0`일 때는 추천 단계 없이 바로 클러스터링으로 진행한다.

`Tier 1`일 때는 추천 단계를 별도로 두지 않고 HDBSCAN 자동 결정 흐름으로 진행한다.

### Result UX

분석 완료 후 결과 메타 영역에 아래 정보를 표시한다.

- selection mode: `auto` 또는 `manual`
- effective topic count: 실제 분석에 사용된 값
- recommendation confidence: `high`, `medium`, `low` 중 하나
- short reason: 예: `Best balance of separation and stability across tested k values`

사용자는 `Auto` 실행 결과를 보고 다음 실행에서 `Manual`로 전환해 미세 조정할 수 있다.

Tier 1에서는 단일 `effective_k`를 표시하지 않는다. 대신 결과 메타에 `Auto by HDBSCAN`과 같은 설명을 표시한다.

## Functional Design

### Frontend Request Shape

분석 요청 config는 아래 개념을 포함한다.

- `topicCountMode: "auto" | "manual"`
- `n_topics: number`
  `Manual`일 때만 의미가 있다.
- `maxReviews`
- 기존 필터 정보

Tier 1에서는 UI에서 `Manual` 선택이 불가능하므로, 요청 시점에는 항상 `topicCountMode: "auto"`로 정규화한다.

### Backend Decision Flow

1. 메인 프로세스가 분석 요청과 현재 settings를 받아 최종 tier를 결정한다.
2. Python analyzer가 리뷰를 로드하고 임베딩을 생성한다.
3. `tier === 0` 이고 `topicCountMode === "auto"`이면 추천기(`recommend_topic_count`)를 실행한다.
4. 추천기가 반환한 `effective_k`를 KMeans에 전달한다.
5. `tier === 0` 이고 `topicCountMode === "manual"`이면 사용자가 입력한 `n_topics`를 그대로 사용한다.
6. `tier >= 1`이면 기존처럼 HDBSCAN을 사용하고, `effective_k`는 `null`로 둔다.

## Recommendation Algorithm

### Applicability

안정성 기반 추천기는 `Tier 0 + Auto`에만 적용한다. 이유는 다음과 같다.

- Tier 0은 KMeans가 `k`를 필요로 한다.
- Tier 1은 HDBSCAN이 이미 자동으로 토픽 수를 정한다.
- 추천기를 Tier 1에 억지로 적용하면 현재 설계와 사용자 기대 모두 흐려진다.

### Input Preparation

- 추천기는 positive, negative 그룹을 각각 독립적으로 평가한다.
- 단, 최종 분석 파이프라인은 현재 구조를 유지하기 위해 그룹 공통의 단일 `effective_k`를 사용한다.
- 각 그룹은 최대 `600`개 리뷰까지만 샘플링한다.
- 샘플링은 재현성을 위해 고정 시드 기반 random sampling을 사용한다.

샘플 상한을 두는 이유는 추천기 계산 시간이 전체 UX를 압도하지 않게 만들기 위해서다. 임베딩은 이미 생성된 상태이므로, 추천기 추가 비용은 주로 KMeans 반복 실행 비용이다.

### Eligibility

- 그룹 리뷰 수가 `20` 미만이면 해당 그룹은 안정성 평가 대상에서 제외한다.
- positive와 negative 둘 다 평가 대상이 아니면 fallback heuristic으로 내려간다.

### Candidate k Range

후보 `k` 범위는 샘플 수 기준으로 제한한다.

- sample count `20-59`: `k = 2..4`
- sample count `60-149`: `k = 3..6`
- sample count `150-299`: `k = 4..8`
- sample count `300+`: `k = 5..10`

이 범위는 지나치게 넓은 탐색으로 시간을 쓰지 않으면서도, 리뷰 수가 많을수록 더 세분화된 토픽 수를 검토할 수 있게 한다.

### Repeated Evaluation Per k

각 후보 `k`는 총 4회 평가한다.

- full sample, seed 11
- full sample, seed 23
- 85% subsample, seed 101
- 85% subsample, seed 202

이 조합은 다음 두 가지를 동시에 확인한다.

- 초기 중심점 변화에 민감한지
- 일부 리뷰가 빠져도 비슷한 군집 구조가 유지되는지

### Per-Run Metrics

각 실행마다 아래 값을 계산한다.

- `separation_score`
  silhouette score. 값이 높을수록 군집 간 분리가 좋다.
- `fragmentation_penalty`
  지나치게 작은 군집 비율에 대한 패널티.
  tiny cluster는 `max(8, ceil(sample_size * 0.05))`보다 작은 군집으로 정의한다.
  패널티는 `tiny_cluster_points / sample_size`로 계산한다.

### Stability Metric

같은 `k`의 실행 결과들끼리 pairwise `Adjusted Rand Index (ARI)`를 계산한다.

- ARI 평균값을 `stability_score`로 사용한다.
- ARI가 높을수록 다른 시드와 샘플에서도 유사한 군집 구성이 유지된다는 뜻이다.

### Final Group Score

각 그룹에서 후보 `k`의 최종 점수는 아래 식으로 계산한다.

`group_score = 0.55 * median(separation_score) + 0.35 * mean(stability_score) - 0.10 * mean(fragmentation_penalty)`

가중치는 다음 우선순위를 반영한다.

- 가장 중요한 것은 실제 분리도
- 두 번째는 반복 실행 안정성
- 과분할 억제는 필요하지만 분리도와 안정성보다 낮은 비중

### Cross-Group Aggregation

현재 파이프라인은 positive/negative에 같은 `n_topics`를 사용하므로, 추천기 역시 단일 공통 `effective_k`를 반환한다.

- 그룹별 점수는 각 그룹 내부에서 min-max normalization을 거친다.
- 최종 점수는 `group review count` 비율을 가중치로 써서 합산한다.
- 점수 차가 `0.03` 미만이면 더 작은 `k`를 선택한다.

평가 가능한 그룹이 하나뿐이면 해당 그룹 점수만으로 `effective_k`를 정한다.

이 tie-break 규칙은 과분할보다 약간 보수적인 토픽 수를 선호하게 만든다.

### Fallback

추천기 평가가 불가능하거나 수치가 불안정하면 heuristic fallback을 사용한다.

- fallback formula: `clamp(round(sqrt(total_selected_reviews) / 2), 2, 8)`
- fallback confidence: `low`
- fallback reason: `Insufficient stable signal; using conservative heuristic`

## Data Flow

### Python Analyzer

Python analyzer는 아래 순서로 동작한다.

1. 리뷰 분할
2. 임베딩 생성
3. 필요 시 추천 토픽 수 계산
4. 실제 클러스터링 실행
5. 키워드 추출
6. 결과 반환

추천기 구현은 analyzer 내부 헬퍼 또는 별도 `topic_recommendation.py` 모듈로 분리한다. 별도 모듈로 두는 쪽을 권장한다. 점수 계산과 후보 탐색 로직이 길어질 가능성이 높고, 추후 테스트 분리도 쉬워지기 때문이다.

### Returned Result Shape

분석 결과 JSON에는 아래 메타데이터를 추가한다.

- `topic_count_mode`
- `requested_k`
- `effective_k`
- `recommendation_confidence`
- `recommendation_reason`
- `recommendation_details`

`requested_k`는 manual mode일 때만 숫자를 가지며, auto mode에서는 `null`이다. `effective_k`는 Tier 0에서만 숫자를 가지며, Tier 1에서는 `null`이다.

`recommendation_details`에는 최소한 아래가 들어간다.

- tested candidate range
- per-group sample counts
- winning k score summary
- whether fallback was used

### Cache Behavior

분석 캐시 hash는 아래 값을 포함해야 한다.

- tier
- topic count mode
- manual `n_topics` if present
- maxReviews
- active filter values

이 변경은 auto/manual과 필터 조합이 달라도 잘못된 캐시를 재사용하지 않기 위해 필요하다.

## Error Handling

- 추천기 계산 중 일부 후보 `k`가 실패하면 전체 분석을 중단하지 않고, 해당 후보만 제외하고 계속 진행한다.
- 모든 후보 평가가 실패하면 fallback heuristic으로 내려간다.
- silhouette score 계산이 불가능한 결과가 나오면 해당 run은 무효 처리한다.
- 추천기에서 fallback이 발생해도 분석 자체는 성공으로 처리한다.
- 결과 메타에는 fallback 여부를 남겨 사용자와 디버깅 양쪽에서 확인 가능하게 한다.

## Testing Strategy

### Unit Tests

- candidate range selection
- tiny cluster penalty calculation
- stability score aggregation
- tie-break behavior
- fallback trigger and output
- Tier 1에서 manual mode가 auto로 정규화되는지

### Integration Tests

- `Auto + Tier 0` 요청 시 recommendation 단계가 실행되고 `effective_k`가 결과에 포함되는지
- `Manual + Tier 0` 요청 시 입력한 `n_topics`가 그대로 사용되는지
- `Tier 1` 요청 시 추천기가 실행되지 않고 HDBSCAN 흐름으로 가는지
- 캐시 hash가 mode, tier, filter 차이를 반영하는지

### UI Tests

- mode toggle에 따라 숫자 입력 활성화 상태가 바뀌는지
- `Auto`에서 분석 중 recommendation progress 문구가 표시되는지
- 완료 후 result meta에 `effective_k`와 confidence가 표시되는지

### Performance Guardrails

- 추천기 샘플 상한은 그룹당 `600`
- 후보 범위 상한은 `10`
- 후보당 반복 횟수는 `4`

이 세 제한을 유지하면 추천기 추가 비용이 전체 임베딩 비용보다 커지지 않도록 제어할 수 있다.

## Rollout Notes

- 기존 저장 결과와의 호환성을 위해 새 메타데이터 필드는 optional read로 처리한다.
- 초기 버전에서는 recommendation details를 UI에 모두 노출하지 않고, 요약 문구만 보여준다.
- 로그 또는 개발자 콘솔에는 상세 점수 정보를 남겨 추천 로직 튜닝에 활용할 수 있게 한다.

## Open Decisions Resolved

- 추천값은 분석 시작 전에 미리 계산하지 않는다.
- 추천값 계산은 분석 프로그레스 단계에 포함한다.
- 사용자는 `Auto`와 `Manual`을 선택할 수 있다.
- 안정성 기반 추천은 처음부터 적용한다.
- Tier 1은 HDBSCAN 자동 결정 흐름을 유지하고, manual topic count는 지원하지 않는다.
