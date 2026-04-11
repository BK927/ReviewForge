# Single-Game Analysis Enhancement Design

**Date:** 2026-04-11
**Scope:** 단일 게임 분석 기능 강화 — 토픽 품질, 리뷰 서피싱, 교차 분석, 시간축, EA 비교, LLM 인사이트

---

## 1. 개요

ReviewForge의 단일 게임 분석을 기획자/마케터가 바로 판단에 쓸 수 있는 수준으로 끌어올린다. 현재 토픽 분석은 추상적이고 겹치는 결과를 낼 때가 있어 해석이 어렵고, 수집된 데이터(`weighted_vote_score`, `written_during_early_access`, `primarily_steam_deck` 등) 중 활용되지 않는 필드가 많다. 이 6개 기능으로 "데이터 나열"에서 "기획 판단 도구"로 전환한다.

### 대전제

- BERTopic 전면 도입 안 함 — 기존 파이프라인(Sentence Transformers → K-Means/HDBSCAN → YAKE/KeyBERT) 유지, 필요한 기법만 차용
- 1인 기획자/마케터의 빠른 탐색 흐름에 맞는 UX — 수동 검수 큐 없음
- 대시보드(전체 감 잡기) → 딥다이브(상세 분석) 흐름 유지
- LLM 기능은 자동/반자동/수동 3단계로, API 비용 부담 없이도 활용 가능

### 개발 순서

`1 → 2 → 3 → 4 → 5 → 6`

| 순서 | 기능 | 이유 |
|------|------|------|
| 1 | 토픽 품질 개선 | 나머지의 기초 — 토픽이 흐리면 다 흐림 |
| 2 | 핵심 리뷰 서피싱 | 데이터 이미 있음, 빠른 가치 체감 |
| 3 | 세그먼트 × 토픽 교차 분석 | 킬러 기능, 1번 토픽 품질에 의존 |
| 4 | 시간축 토픽 변화 | 1번 토픽 + 시계열 결합 |
| 5 | 얼리 액세스 비교 | 조건부 기능, 4번 시간축과 시너지 |
| 6 | LLM 인사이트 레이어 | 1~5 결과물 위에 얹는 구조 |

---

## 2. Feature 1: 토픽 품질 개선

### 문제

- 한두 단어 리뷰("good", "10/10")가 의미 희박한 임베딩을 생성, 클러스터 경계를 흐림
- 유사 토픽이 별도 클러스터로 분리됨 (예: "combat feel" + "fighting system")
- 토픽 라벨이 키워드 상위 3개 이어붙이기 (`label: ", ".join(kw for kw, _ in keywords[:3])`) — 사람이 읽기 어려움
- **자동 토픽 수 추천(Tier 0 auto mode)이 유의미한 결과를 내지 못함** — 구조적 결함 3가지:
  1. 긍정/부정 그룹에 같은 k를 강제 적용 (`analyzer.py:71,78`에서 동일 `effective_k` 사용)
  2. min-max 정규화가 절대 품질을 숨김 — 모든 k가 나빠도 최선이 1.0으로 정규화됨
  3. 동점권(0.03 이내) 내 최소 k 선택 편향 — 토픽이 너무 넓고 추상적으로 나옴

### 설계

#### 2.1 짧은 리뷰 분리

**위치:** `analyzer.py:run_analysis()` — 감성 분할 직후, 임베딩 생성 전

- 단어 수 기준 임계값(기본값 5단어)으로 필터링. 설정에서 조절 가능
- 임계값 미만 리뷰는 클러스터링 파이프라인에서 제외
- 별도 "초단문 반응" 버킷으로 프론트엔드에 전달 — 총 개수 + 긍/부정 비율 + 가장 빈도 높은 표현 상위 10개
- 분석 결과에 `short_review_summary: { count, positive_rate, frequent_phrases[] }` 추가
- `frequent_phrases` 추출: 초단문 리뷰 텍스트를 소문자 정규화 후 `collections.Counter`로 동일 텍스트 빈도 카운팅. 별도 NLP 불필요 — 초단문이라 텍스트 자체가 구(phrase)임

**단어 수 카운팅:** 공백 기준 split. 중국어/일본어 등 공백 없는 언어는 문자 수 기준 별도 임계값(기본 10자) 적용. 언어 필드(`language`)로 분기.

#### 2.2 유사 토픽 자동 병합

**위치:** `analyzer.py:_analyze_group()` — 클러스터링 완료 후, 키워드 추출 전

1. 각 클러스터의 centroid 계산 (클러스터 내 임베딩 평균)
2. centroid 간 코사인 유사도 행렬 계산
3. 유사도가 임계값(기본 0.80) 이상인 쌍을 병합 — 작은 클러스터를 큰 클러스터에 흡수
4. 병합은 greedy 방식: 가장 유사한 쌍부터 순차 병합, 병합 후 centroid 재계산. 1회 패스만 수행 — 이미 병합된 클러스터를 다시 병합하지 않음 (단순성, 예측 가능성 우선)
5. 병합 임계값은 설정(`config.merge_threshold`)에서 조절 가능. 기본값 0.80은 초기 추정치 — 실제 데이터로 검증 후 조정 필요

**결과에 추가:** `merge_info: { original_count, merged_count, merges: [{ from, to, similarity }] }`

#### 2.3 자동 토픽 수 추천 개선

**위치:** `topic_recommendation.py` 전체 리팩터링

**현재 구조의 문제와 개선:**

**(a) 긍정/부정 별도 k 추천**

현재: `recommend_topic_count()` → 하나의 `effective_k` 반환 → 긍정/부정 모두 동일 k 적용.

개선: 긍정/부정 각각 독립적으로 최적 k를 추천. 반환값을 `effective_k` 단일 값에서 `positive_k`, `negative_k` 쌍으로 변경.

```python
# 현재
{"effective_k": 5, "confidence": "medium", ...}

# 개선
{
    "positive_k": 4,
    "negative_k": 6,
    "positive_confidence": "high",
    "negative_confidence": "medium",
    "positive_reason": str,
    "negative_reason": str,
    "details": { ... }  # 그룹별 상세 포함
}
```

`analyzer.py`에서 `_analyze_group()` 호출 시 각 그룹에 해당하는 k 사용:
```python
pos_topics = _analyze_group(..., positive_k, ...)
neg_topics = _analyze_group(..., negative_k, ...)
```

프론트엔드: 기존 `effective_k` 단일 표시 → "긍정 토픽 N개 / 부정 토픽 M개" 표시. confidence 배지도 그룹별로 분리.

**(b) 절대 품질 임계값 추가**

현재: `_normalize_scores()`로 min-max 정규화 → 절대 품질 무시.

개선: 정규화 전, 각 후보 k의 `separation_median`(실루엣 점수 중앙값) 확인. 모든 후보의 `separation_median`이 임계값(기본 0.05) 미만이면 "의미 있는 클러스터 구조 없음"으로 판단하고 fallback 사용.

```python
# _evaluate_group_candidates() 후, 정규화 전
max_separation = max(m["separation_median"] for m in candidate_scores.values())
if max_separation < MIN_SEPARATION_THRESHOLD:  # 0.05
    return _fallback_result(...)  # 기존 sqrt(N)/2 휴리스틱
```

**(c) 작은 k 편향 완화**

현재: 점수 차이 0.03 이내면 가장 작은 k 선택.

개선: 동점 판정 범위를 0.03에서 0.01로 축소. 추가로, 후보 k 간 inertia(SSE) 감소율을 보조 지표로 활용하여 엘보우 지점 감지. 정규화 점수와 엘보우 지점이 일치하면 신뢰도 상승.

```python
# _pick_winning_k() 수정
contenders = [item for item in ranked if (top_score - item[1]) < 0.01]  # 0.03 → 0.01
```

**스키마 영향:** 기존 `effective_k` 필드 제거, `positive_k`/`negative_k` 추가. `recommendation_confidence` → `positive_confidence`/`negative_confidence`. 프론트엔드 `TopicAnalysis.tsx`의 메타데이터 표시 영역 수정 필요.

#### 2.4 토픽 라벨링 개선

**현재:** `analyzer.py:127` — `"label": ", ".join(kw for kw, _ in keywords[:3])`

**개선 (LLM 없이):** 키워드 상위 3개를 조합하되, 키프레이즈(bigram 이상) 우선 배치. 단일 단어만 있으면 현재 방식 유지.

**개선 (LLM 있을 때):** Feature 6에서 토픽 라벨을 LLM으로 생성하는 옵션 제공. 키워드 + 샘플 리뷰 5개를 입력으로 "이 리뷰 그룹을 대표하는 짧은 명사구(3~6단어)" 요청.

### 분석 결과 스키마 변경

```python
# 최상위 결과 변경/추가:
{
    # 기존 effective_k → 그룹별 분리
    "positive_k": int,
    "negative_k": int,
    "positive_confidence": "high" | "medium" | "low",
    "negative_confidence": "high" | "medium" | "low",
    "positive_recommendation_reason": str,
    "negative_recommendation_reason": str,

    # 신규 추가
    "short_review_summary": {
        "count": int,
        "positive_rate": float,
        "frequent_phrases": [{"phrase": str, "count": int}, ...]
    },
    "merge_info": {
        "positive": {
            "original_topic_count": int,
            "merged_topic_count": int,
            "merges": [{"from_id": int, "to_id": int, "similarity": float}, ...]
        },
        "negative": { ... }  # 동일 구조
    }
}

# 기존 필드 제거: effective_k, recommendation_confidence, recommendation_reason
# (하위 호환: manual 모드에서는 requested_k 유지, positive_k/negative_k에 동일값 설정)
```

### 설정 추가

`NormalizedAnalysisConfig`에:
- `min_review_words`: int (기본 5) — 짧은 리뷰 분리 임계값
- `merge_threshold`: float (기본 0.80) — 토픽 병합 유사도 임계값

캐시 해시에 두 값 포함 — 값이 바뀌면 캐시 무효화.

---

## 3. Feature 2: 핵심 리뷰 서피싱

### 문제

`weighted_vote_score`, `votes_up`, `votes_funny` 데이터가 수집되지만 분석에 활용되지 않음. 어떤 리뷰가 커뮤니티에서 중요하게 여겨지는지 알 수 없음.

### 설계

#### 3.1 Most Helpful 리뷰

- `weighted_vote_score` 기준 상위 10개 (긍정/부정 각각 5개)
- 커뮤니티가 가장 공감한 의견

#### 3.2 Most Representative 리뷰

- 각 토픽의 centroid에 가장 가까운 리뷰 (코사인 유사도 기준)
- 그 토픽의 가장 전형적인 의견
- 토픽 분석 완료 후 계산 가능 — Feature 1에 의존

#### 3.3 UI 위치

대시보드 탭 하단 또는 별도 섹션. 두 리스트를 나란히 표시:
- **"커뮤니티 공감 리뷰"** — Most Helpful
- **"토픽 대표 리뷰"** — Most Representative (토픽 분석 실행 후 표시)

### 데이터 흐름

Most Helpful은 DB 쿼리만으로 가능 — 분석 파이프라인 불필요:
```sql
SELECT * FROM reviews
WHERE app_id = ? AND voted_up = ?
ORDER BY weighted_vote_score DESC
LIMIT 5
```

Most Representative는 임베딩 + 클러스터링 결과 필요 — 토픽 분석 결과에 포함시킴:
```python
# _analyze_group()에서 각 토픽의 centroid 최근접 리뷰 인덱스 계산
# Topic 구조에 추가:
{
    "representative_review": str  # centroid에 가장 가까운 리뷰 텍스트
}
```

### IPC 추가

- `reviews:top-helpful` — app_id, sentiment, limit → 상위 리뷰 반환 (DB 쿼리)
- Most Representative는 기존 `analysis:run` 결과에 포함

---

## 4. Feature 3: 세그먼트 × 토픽 교차 분석

### 문제

현재 토픽 탭과 세그먼트 탭이 별개. "50시간 유저는 어떤 토픽에 대해 불만인가?"를 알려면 머릿속에서 조합해야 함.

### 설계

#### 4.1 분석 방식

글로벌 토픽(전체 리뷰로 클러스터링한 결과)을 기준으로, 각 세그먼트의 리뷰가 어느 토픽에 얼마나 속하는지 비중을 계산. 세그먼트별로 별도 클러스터링하지 않음 — 토픽 정의는 하나, 분포만 세그먼트별로 다르게 봄.

**처리 흐름:**
1. Feature 1의 토픽 분석 결과(클러스터 라벨)를 가져옴
2. 각 리뷰의 세그먼트 속성(playtime_bin, language, steam_deck 등) 매핑
3. 세그먼트별 토픽 비중 + 긍/부정 비율 계산

#### 4.2 세그먼트 축

| 세그먼트 | 구간 | 소스 필드 |
|----------|------|-----------|
| 플레이타임 | 0-2h, 2-10h, 10-50h, 50h+ | `playtime_at_review` (분→시간 변환) |
| 언어 | 상위 10개 언어 (리뷰 수 기준) | `language` |
| Steam Deck | Deck / Non-Deck | `primarily_steam_deck` |
| 구매 유형 | 구매 / 무료 | `steam_purchase` |
| 기간 | 전체/30일/90일/1년 | `timestamp_created` |

#### 4.3 결과 스키마

```python
{
    "segment_topic_matrix": {
        "segment_type": "playtime",  # 또는 "language", "steam_deck" 등
        "segments": [
            {
                "segment_label": "50h+",
                "total_reviews": int,
                "positive_rate": float,
                "topic_distribution": [
                    {
                        "topic_id": int,
                        "topic_label": str,
                        "review_count": int,
                        "proportion": float,  # 이 세그먼트 내 비중
                        "positive_rate": float,  # 이 세그먼트×토픽의 긍정률
                        "representative_review": str
                    }
                ]
            }
        ]
    }
}
```

#### 4.4 처리 위치

Python 파이프라인에서 계산. `analyzer.py`에 `compute_segment_topic_matrix()` 추가. 토픽 분석 완료 후 실행되며, 세그먼트 속성은 리뷰 메타데이터에서 가져옴 — 현재 `reviews` 파라미터에 `text`와 `voted_up`만 전달하는데, 세그먼트용 필드(`playtime_at_review`, `language`, `primarily_steam_deck`, `steam_purchase`, `timestamp_created`) 추가 전달 필요.

#### 4.5 UI 위치

기존 세그먼트 탭 확장. 현재 플레이타임/언어별 긍정률 바 차트 아래에 "토픽 교차 분석" 섹션 추가. 세그먼트 축 선택 드롭다운 → 히트맵 또는 그룹화된 바 차트로 시각화.

토픽 분석이 아직 실행되지 않았으면 "토픽 분석을 먼저 실행해주세요" 안내 표시.

---

## 5. Feature 4: 시간축 토픽 변화

### 문제

현재 대시보드의 시계열은 긍/부정 비율만 보여줌. 특정 불만이 언제부터 나타났는지, 업데이트 후 개선됐는지 알 수 없음.

### 설계

#### 5.1 분석 방식

글로벌 토픽(전체 기간 리뷰로 클러스터링)을 기준으로, 시간 구간별 토픽 비중 변화를 계산. 시간 구간별로 별도 클러스터링하지 않음.

**처리 흐름:**
1. Feature 1의 토픽 분석 결과(클러스터 라벨) 가져옴
2. 리뷰를 시간 구간(주/월)으로 그룹화
3. 각 구간별 토픽 비중 + 토픽 내 긍/부정 비율 계산

#### 5.2 시간 단위

- 주(週) 단위: 리뷰 수가 충분할 때 (총 1000개 이상)
- 월 단위: 리뷰 수가 적거나 장기간 분석 시
- 프론트엔드에서 전환 가능 (대시보드 시계열과 동일한 Daily/Weekly/Monthly 토글)

#### 5.3 결과 스키마

```python
{
    "topics_over_time": [
        {
            "period": "2025-W03",  # 또는 "2025-01"
            "total_reviews": int,
            "topic_distribution": [
                {
                    "topic_id": int,
                    "topic_label": str,
                    "review_count": int,
                    "proportion": float,
                    "positive_rate": float
                }
            ]
        }
    ]
}
```

#### 5.4 UI 위치

토픽 분석 탭 내 하위 섹션. Stacked area chart 또는 multi-line chart로 시각화. X축: 시간, Y축: 토픽 비중. 토픽 클릭 시 해당 토픽의 긍/부정 비율 변화 드릴다운.

---

## 6. Feature 5: 얼리 액세스 비교

### 문제

`written_during_early_access` 플래그가 수집되지만 분석에 활용되지 않음.

### 설계

#### 6.1 활성화 조건

EA 리뷰 비율이 전체의 10% 이상이고 EA 리뷰 수가 50개 이상일 때만 UI에 표시. 조건 미달 시 섹션 숨김.

#### 6.2 분석 방식

Feature 3(세그먼트×토픽)의 특수 케이스. `written_during_early_access`를 세그먼트 축으로 사용:
- 구간: EA / Post-Launch
- 글로벌 토픽 기준으로 두 구간의 토픽 비중 비교

#### 6.3 문제 생애주기 분류

각 토픽을 EA와 Post-Launch 존재 여부로 분류:

| EA 존재 | Post-Launch 존재 | 분류 |
|---------|-----------------|------|
| O | O | **미해결 이슈** (Persistent) |
| O | X | **해결된 피드백** (Resolved) |
| X | O | **출시 후 신규** (New) |

"존재"의 기준: 해당 구간에서 토픽 비중 5% 이상.

#### 6.4 결과 스키마

```python
{
    "early_access_comparison": {
        "ea_review_count": int,
        "post_launch_review_count": int,
        "lifecycle": [
            {
                "topic_id": int,
                "topic_label": str,
                "status": "persistent" | "resolved" | "new",
                "ea_proportion": float,
                "post_launch_proportion": float,
                "ea_positive_rate": float,
                "post_launch_positive_rate": float
            }
        ]
    }
}
```

#### 6.5 UI 위치

세그먼트 탭 내 조건부 섹션. 상태별 색상 구분: 미해결(빨강), 해결됨(초록), 신규(노랑). 각 토픽에 EA/Post-Launch 비중 비교 바.

---

## 7. Feature 6: LLM 인사이트 레이어

### 문제

분석 결과를 해석하고 "그래서 이 게임은 뭘 잘하고 뭘 못하는 건데?"까지 연결하는 것이 사용자에게 부담.

### 설계

#### 7.1 3단계 지원

| 모드 | 동작 | 설정 |
|------|------|------|
| **자동** | API 키 설정 → 분석 완료 시 LLM 해석 자동 실행, 결과 인앱 표시 | `apiProvider` + `apiKey` 설정 |
| **반자동** | 분석 데이터를 담은 특화 프롬프트 생성 → 클립보드 복사 → 사용자가 본인 구독 챗봇에 붙여넣기 | 프롬프트 복사 버튼 |
| **수동** | 기존 CSV/마크다운 내보내기 | 현재 기능 유지 |

#### 7.2 LLM 적용 지점

| 적용 지점 | 입력 | 출력 | 우선도 |
|-----------|------|------|--------|
| 토픽 라벨링 | 키워드 + 샘플 리뷰 5개 (토픽당) | 짧은 명사구 (3~6단어) | 높음 |
| 전체 분석 요약 | 모든 토픽 키워드 + 통계 | 핵심 강점/약점 요약 (1~2 문단) | 높음 |
| 세그먼트×토픽 해석 | 교차 분석 매트릭스 데이터 | 세그먼트별 핵심 차이점 요약 | 중간 |
| 시간축 서사 | 시간별 토픽 변화 데이터 | 주요 변화 시점과 원인 추정 | 중간 |

#### 7.3 자동 모드 구현

**위치:** `src/main/llm-service.ts` (신규)

- 지원 프로바이더: Claude, OpenAI, Gemini (기존 설정 UI 활용)
- 각 적용 지점별 시스템 프롬프트 + 데이터 프롬프트 템플릿
- 토픽 라벨링: 토픽 수만큼 API 호출 (배치 가능 — 여러 토픽을 한 번에 요청)
- 전체 요약: 1회 호출
- 응답 언어: 분석 대상 리뷰의 주 언어 또는 사용자 설정 언어
- 결과를 분석 캐시에 함께 저장

**비용 최적화:**
- 토픽 라벨링은 토픽당 입력 ~500 토큰, 출력 ~20 토큰 → 10개 토픽 배치 시 ~5,200 토큰
- 전체 요약은 입력 ~2,000 토큰, 출력 ~300 토큰
- 게임 하나당 총 ~8,000 토큰 이내 — 비용 미미

#### 7.4 반자동 모드 구현

**위치:** 각 분석 탭에 "프롬프트 복사" 버튼 추가

- 현재 `ExportPanel.tsx`의 LLM 프롬프트 생성을 각 분석 탭으로 확장
- 적용 지점별 특화된 프롬프트 템플릿:
  - 토픽 라벨링: "아래 키워드와 샘플 리뷰를 보고 각 그룹을 대표하는 짧은 한국어 명사구를 만들어주세요"
  - 전체 요약: "아래 분석 데이터를 보고 이 게임의 핵심 강점과 약점을 요약해주세요"
  - 세그먼트 해석: "아래 세그먼트별 토픽 분포를 보고 각 사용자 그룹의 핵심 차이를 설명해주세요"
  - 시간축 서사: "아래 시간별 토픽 변화를 보고 주요 변화 시점과 추정 원인을 설명해주세요"
- 분석 데이터를 구조화하여 프롬프트에 삽입
- 클립보드 복사 + 복사 완료 피드백

#### 7.5 설정

기존 `analysis-settings.ts`의 `apiProvider`, `apiKey` 활용. 추가:
- `llmMode`: 'auto' | 'semi' | 'off' (기본: 'semi')
- `llmLanguage`: 'auto' | 'ko' | 'en' | ... (기본: 'auto' — 리뷰 주 언어 따름)

---

## 8. 아키텍처 변경 요약

### 8.1 Python 파이프라인 변경

```
analyzer.py (수정)
├── 짧은 리뷰 분리 로직 추가 (2.1)
├── _analyze_group() 내 토픽 병합 단계 추가 (2.2)
├── _analyze_group() 내 representative_review 계산 추가 (3.2)
├── compute_segment_topic_matrix() 신규 (4)
├── compute_topics_over_time() 신규 (5)
└── compute_ea_comparison() 신규 (6) — 내부적으로 segment_topic_matrix 활용

topic_merge.py (신규)
└── centroid 계산, 코사인 유사도 행렬, greedy 병합

short_review.py (신규)
└── 단어 수 카운팅 (언어별 분기), 빈도 표현 추출
```

### 8.2 IPC 추가

| 채널 | 설명 |
|------|------|
| `reviews:top-helpful` | 상위 helpful 리뷰 조회 (DB 쿼리) |
| `llm:generate` | LLM API 호출 (자동 모드) |
| `llm:build-prompt` | 특화 프롬프트 생성 (반자동 모드) |

기존 `analysis:run`의 반환값 확장 — `short_review_summary`, `merge_info` 추가 (Feature 1, 기본 토픽 분석과 함께 실행).

`segment_topic_matrix`, `topics_over_time`, `early_access_comparison`은 `analysis:run`에 포함하지 않음. 이들은 기존 클러스터 라벨을 재사용하는 경량 후처리이므로 별도 IPC로 온디맨드 실행:

| 채널 | 트리거 | 설명 |
|------|--------|------|
| `analysis:segment-topics` | 세그먼트 탭에서 교차 분석 섹션 진입 시 | 세그먼트×토픽 매트릭스 계산 |
| `analysis:topics-over-time` | 토픽 탭에서 시간축 섹션 진입 시 | 시간별 토픽 분포 계산 |
| `analysis:ea-comparison` | 세그먼트 탭에서 EA 섹션 진입 시 | EA vs Post-Launch 비교 |

이 분리의 이점: 기본 분석("분석 실행" 버튼) 속도를 유지하면서, 사용자가 실제로 보는 분석만 계산. 클러스터 라벨과 임베딩은 캐시에서 재사용하므로 후처리 자체는 빠름(재임베딩/재클러스터링 없음).

### 8.3 Node.js 신규 모듈

```
src/main/llm-service.ts (신규)
└── Claude/OpenAI/Gemini API 호출, 프롬프트 템플릿 관리, 응답 파싱
```

### 8.4 프론트엔드 변경

| 컴포넌트 | 변경 |
|----------|------|
| `TopicAnalysis.tsx` | 초단문 요약 섹션, 병합 정보 표시, 시간축 차트 섹션, LLM 요약 표시/프롬프트 복사 버튼 |
| `SegmentAnalysis.tsx` | 토픽 교차 분석 섹션, EA 비교 섹션 (조건부), LLM 해석/프롬프트 복사 버튼 |
| `Dashboard.tsx` | Most Helpful / Most Representative 리뷰 섹션 |
| `ExportPanel.tsx` | 적용 지점별 특화 프롬프트 템플릿 추가 |

### 8.5 DB 스키마 변경

없음. 기존 `reviews` 테이블에 필요한 필드는 모두 있고, 분석 결과는 `analysis_cache.result_json`에 저장. 캐시 해시에 `min_review_words`, `merge_threshold` 추가.

### 8.6 설정 변경

`NormalizedAnalysisConfig` 확장:
```typescript
{
    // 기존
    tier: number
    topicCountMode: 'auto' | 'manual'
    n_topics?: number
    maxReviews?: number
    filter?: Record<string, unknown>
    // 추가
    min_review_words: number      // 기본 5
    merge_threshold: number       // 기본 0.80
    llmMode: 'auto' | 'semi' | 'off'
    llmLanguage: 'auto' | string
}
```

---

## 9. 리뷰 데이터 전달 확장

현재 `analysis:run`에서 Python에 전달하는 리뷰 데이터:
```typescript
{ text: string, voted_up: boolean }
```

Feature 3~5를 위해 확장:
```typescript
{
    text: string,
    voted_up: boolean,
    recommendation_id: string,        // representative 리뷰 조회용
    playtime_at_review: number,       // 세그먼트: 플레이타임
    language: string,                 // 세그먼트: 언어
    primarily_steam_deck: boolean,    // 세그먼트: Steam Deck
    steam_purchase: boolean,          // 세그먼트: 구매 유형
    timestamp_created: number,        // 시간축 + 기간 세그먼트
    written_during_early_access: boolean  // EA 비교
}
```

성능 고려: 필드 추가로 IPC 페이로드가 커지지만, 기존에도 전체 리뷰 텍스트를 전달하므로 메타데이터 추가분은 비중이 작음.
