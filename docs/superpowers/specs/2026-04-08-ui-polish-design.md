# UI Polish: Compact Layout + Juicy Interactions

**Date:** 2026-04-08
**Status:** Approved

## Overview

ReviewForge UI의 두 가지 문제를 해결한다:
1. 콘텐츠 영역 양쪽 여백이 과도하게 넓어 공간 낭비
2. 인터랙션 피드백이 전혀 없어 앱이 정적으로 느껴짐

## 1. Compact Layout

현재 `.tab-content`의 padding이 24px로 설정되어 있어 사이드바(260px) 옆 콘텐츠 영역이 좁아 보인다.

### 변경 사항
- `.tab-content` padding: `24px` → `12px`
- `.charts-grid` gap: `24px` → `12px`
- 카드 스타일 유지: `border-radius: 12px`, `box-shadow: 0 1px 3px rgba(0,0,0,0.1)`
- 카드 내부 패딩은 기존 유지 (가독성 보존)

### 영향 범위
- `src/renderer/src/assets/styles.css` — `.tab-content`, `.charts-grid` 수정

## 2. Hover & Press 피드백

### 카드 호버
- `transform: translateY(-2px)`
- `box-shadow` 확대 (기존 → `0 8px 25px rgba(109, 40, 217, 0.12)`)
- `transition: all 200ms ease-out`

### 버튼 호버 & 프레스
- 호버: `transform: scale(1.02)`, 배경색 약간 밝게
- Active: `transform: scale(0.97)`
- `transition: all 150ms ease-out`

### 사이드바 게임 항목
- 호버 시 배경색 하이라이트 (`rgba(255,255,255,0.05)` 등)
- `transition: background-color 150ms`

### 영향 범위
- `src/renderer/src/assets/styles.css` — `.chart-card`, `.game-item`, 버튼 클래스들

## 3. 로딩 스켈레톤 & 프로그레스

### 스켈레톤 UI
- 데이터 로딩 중 카드/차트 자리에 shimmer 애니메이션 스켈레톤 표시
- `@keyframes shimmer` — `background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%)`로 반짝이는 효과
- 스켈레톤 컴포넌트: `SkeletonCard`, `SkeletonText`, `SkeletonCircle`

### 프로그레스 바
- 리뷰 수집(Steam API 호출) 시 진행률 표시
- 현재 `collectReviews` IPC에서 이미 progress 이벤트를 보내고 있으므로, renderer에서 프로그레스 바 UI만 추가

### 영향 범위
- 새 파일: `src/renderer/src/components/Skeleton.tsx` — 스켈레톤 컴포넌트
- `src/renderer/src/components/Dashboard.tsx` — 로딩 상태에 스켈레톤 적용
- `src/renderer/src/components/TopicAnalysis.tsx` — 로딩 상태에 스켈레톤 적용
- `src/renderer/src/components/SegmentAnalysis.tsx` — 로딩 상태에 스켈레톤 적용
- `src/renderer/src/components/GameInput.tsx` — 수집 프로그레스 바
- `src/renderer/src/assets/styles.css` — 스켈레톤/프로그레스 스타일

## 4. 숫자 & 차트 애니메이션

### 숫자 카운트업
- 대시보드 통계 숫자(총 리뷰 수, 긍정률 등)가 0에서 목표값까지 카운트업
- duration: 600ms, easing: ease-out
- 커스텀 훅: `useCountUp(targetValue, duration)`

### 차트 애니메이션
- ECharts에 내장된 애니메이션 옵션 활용
- `animationDuration: 400`, `animationEasing: 'cubicOut'`
- 순차 딜레이: `animationDelay: (idx) => idx * 100`

### 영향 범위
- 새 파일: `src/renderer/src/hooks/useCountUp.ts`
- `src/renderer/src/components/Dashboard.tsx` — 통계 숫자에 카운트업 적용
- ECharts 옵션에 animation 설정 추가

## 5. 탭 전환 트랜지션

### 탭 인디케이터
- 현재 탭 아래에 슬라이딩 인디케이터 바 추가
- `transition: left 300ms cubic-bezier(0.4, 0, 0.2, 1), width 300ms cubic-bezier(0.4, 0, 0.2, 1)`

### 콘텐츠 전환
- 탭 변경 시 콘텐츠가 `opacity: 0, translateX(12px)` → `opacity: 1, translateX(0)` 로 전환
- duration: 250ms, CSS 트랜지션 또는 간단한 클래스 토글로 구현

### 영향 범위
- `src/renderer/src/components/App.tsx` 또는 탭 네비게이션 컴포넌트 — 인디케이터 + 전환 로직
- `src/renderer/src/assets/styles.css` — `.tab-indicator`, `.tab-content-enter` 등

## 타이밍 원칙 (Mixed)

| 카테고리 | duration | easing | 예시 |
|---------|----------|--------|------|
| Snappy | 150ms | ease-out | 버튼, 호버, 토글 |
| Standard | 200~250ms | ease-out | 카드 호버, 콘텐츠 전환 |
| Smooth | 300~500ms | cubic-bezier(0.4,0,0.2,1) | 탭 인디케이터, 차트, 카운트업 |

## 구현 순서 (권장)

1. Compact Layout (CSS만 수정, 가장 빠름)
2. Hover & Press 피드백 (CSS만 수정)
3. 탭 전환 트랜지션 (CSS + 약간의 JSX)
4. 숫자 & 차트 애니메이션 (훅 + ECharts 설정)
5. 로딩 스켈레톤 (새 컴포넌트 + 각 탭 수정, 가장 큰 작업)

## 제외 사항

- 사이드바 디자인 변경 없음
- 색상/테마 변경 없음
- 폰트 변경 없음
- 특정 탭 레이아웃 재구성 없음
