# ReviewForge

Steam 게임 리뷰를 수집·분석하는 데스크탑 앱입니다. 리뷰 트렌드 시각화, AI 기반 토픽 분석, 세그먼트 분석, LLM 프롬프트용 내보내기 기능을 제공합니다.

## 기능

- **리뷰 수집** — Steam API로 최대 수십만 건의 리뷰를 로컬 DB에 저장
- **Dashboard** — 긍/부정 비율, 시간별 트렌드, 언어 분포 차트
- **Topic Analysis** — SentenceTransformer + HDBSCAN 클러스터링으로 긍정/부정 토픽 자동 추출
- **Segment Analysis** — 플레이타임·언어·구매 유형별 긍정률 비교
- **Export** — CSV, Markdown 파일 내보내기 및 LLM 프롬프트용 클립보드 복사
- **Compare** — 여러 게임 통계 나란히 비교

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 프레임워크 | Electron 36 + electron-vite |
| UI | React 18 + TypeScript + ECharts |
| DB | better-sqlite3 (로컬 SQLite) |
| AI 분석 | Python 사이드카 (sentence-transformers, HDBSCAN, YAKE) |
| 모델 | `intfloat/multilingual-e5-small` (첫 실행 시 자동 다운로드) |

## 요구 사항

- Node.js 18+
- pnpm
- Python 3.10+ (분석 기능 사용 시)

## 설치 및 실행

```bash
# 의존성 설치
pnpm install

# better-sqlite3 네이티브 바이너리 재빌드 (필수)
cd node_modules/better-sqlite3 && npx prebuild-install --runtime electron --target 36.0.0 --arch x64 --download --tag-prefix v && cd ../..

# Python 의존성 설치
cd python && pip install -r requirements.txt && cd ..

# 개발 서버 실행
pnpm dev
```

## 빌드

```bash
# Windows
pnpm build:win

# macOS
pnpm build:mac

# Linux
pnpm build:linux
```

## 프로젝트 구조

```
src/
  main/           # Electron 메인 프로세스 (IPC, DB, Steam API)
  preload/        # Preload 스크립트
  renderer/       # React UI
    components/   # Dashboard, TopicAnalysis, SegmentAnalysis 등
    hooks/        # useApi, useCountUp
python/           # AI 분석 사이드카
  main.py         # JSON-line 프로토콜 진입점
  analyzer.py     # 분석 파이프라인
  clustering.py   # HDBSCAN 클러스터링
  embeddings.py   # SentenceTransformer 임베딩
tests/
  main/           # Electron 메인 프로세스 테스트 (Vitest)
  python/         # Python 사이드카 테스트 (pytest)
```

## 데이터 저장 위치

- DB 파일: `~/.reviewforge/reviews.db`
- AI 모델 캐시: `~/.reviewforge/models/`
