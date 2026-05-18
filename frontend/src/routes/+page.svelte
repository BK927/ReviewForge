<script lang="ts">
  import { onMount } from 'svelte';
  import {
    Activity,
    Check,
    ClipboardList,
    Cloud,
    CloudCog,
    Copy,
    Database,
    Download,
    DownloadCloud,
    FileText,
    GitCommitHorizontal,
    ImageDown,
    Info,
    Languages,
    LayoutDashboard,
    MessagesSquare,
    Network,
    Play,
    PlugZap,
    Plus,
    ScanSearch,
    ScanText,
    Search,
    Server,
    Settings2,
    SlidersHorizontal,
    Sparkles,
    Clock
  } from 'lucide-svelte';
  import AuditPanel from '$lib/AuditPanel.svelte';
  import FilterBar from '$lib/FilterBar.svelte';
  import FormPanel from '$lib/FormPanel.svelte';
  import MetricStrip from '$lib/MetricStrip.svelte';
  import PageIntro from '$lib/PageIntro.svelte';
  import QuotePanel from '$lib/QuotePanel.svelte';
  import ReviewTable from '$lib/ReviewTable.svelte';
  import RunPanel from '$lib/RunPanel.svelte';
  import SimpleTable from '$lib/SimpleTable.svelte';
  import TopicPanel from '$lib/TopicPanel.svelte';

  const API_BASE = 'http://127.0.0.1:8000/api';

  type TabId =
    | 'dashboard'
    | 'data'
    | 'patches'
    | 'runs'
    | 'clusters'
    | 'languages'
    | 'evidence'
    | 'report'
    | 'settings';

  type ClusterId = string;

  type Review = {
    language: string;
    reaction: 'good' | 'bad' | 'mixed';
    playtime: string;
    topic: string;
    summary: string;
  };

  type ApiDashboard = {
    total_reviews: number;
    positive_reviews: number;
    negative_reviews: number;
    positive_ratio: number;
    languages: number;
    clusters: number;
    evidence_items: number;
    latest_review_at: string | null;
  };

  type ApiCluster = {
    id: number;
    label: string;
    summary: string;
    sentiment: string;
    language: string | null;
    review_count: number;
    avg_weighted_score: number;
  };

  type ApiReview = {
    language: string;
    review: string;
    voted_up: boolean;
    weighted_vote_score: number;
    playtime_at_review: number;
  };

  const tabs: Array<{ id: TabId; label: string; group: 'Project' | 'Analysis'; icon: typeof LayoutDashboard }> = [
    { id: 'dashboard', label: '대시보드', group: 'Project', icon: LayoutDashboard },
    { id: 'data', label: '데이터 갱신', group: 'Project', icon: Database },
    { id: 'patches', label: '비교 기준', group: 'Project', icon: GitCommitHorizontal },
    { id: 'runs', label: '분석 실행', group: 'Project', icon: Activity },
    { id: 'clusters', label: '리뷰 클러스터', group: 'Analysis', icon: MessagesSquare },
    { id: 'languages', label: '언어권 비교', group: 'Analysis', icon: Languages },
    { id: 'evidence', label: '근거 검증', group: 'Analysis', icon: ScanSearch },
    { id: 'report', label: '리포트', group: 'Analysis', icon: FileText },
    { id: 'settings', label: '모델 설정', group: 'Analysis', icon: SlidersHorizontal }
  ];

  const groupedTabs = ['Project', 'Analysis'].map((group) => ({
    group,
    items: tabs.filter((tab) => tab.group === group)
  }));

  let positiveRatio = 73;
  let projectReviewCount = '48,219';
  let projectLanguageCount = '14';

  let kpis = [
    ['수집 리뷰', '48,219', '최근 동기화 18분 전'],
    ['부정 급증 토픽', '6', '전 패치 대비'],
    ['대표 클러스터', '31', '다국어 묶음'],
    ['우선순위 높음', '4', '기획 검토 후보']
  ];

  let metrics = [
    ['마지막 갱신', '18분 전', 'Steam app/1145350'],
    ['원본 리뷰', '48,219', 'DuckDB 저장 완료'],
    ['분석 대기', '1,284', '최근 리뷰 미처리'],
    ['오프토픽', '제외', '리뷰 폭탄은 별도 분석']
  ];

  type IconComponent = typeof Copy;

  const exportRows: Array<{ label: string; icon: IconComponent }> = [
    { label: '요약 리포트', icon: Copy },
    { label: '대표 리뷰 CSV', icon: Download },
    { label: '패치별 차트 PNG', icon: ImageDown },
    { label: '기획 우선순위 표', icon: ClipboardList }
  ];

  const modelOptions: Array<{ icon: IconComponent; name: string; detail: string; state: string; tone: string }> = [
    { icon: Server, name: 'LM Studio', detail: '로컬 OpenAI 호환 서버 · 비용 없음 · 속도는 PC 사양 영향', state: '연결됨', tone: 'good' },
    { icon: Cloud, name: 'Claude', detail: '고품질 리포트 생성용 · API 키 필요', state: '미설정', tone: 'mixed' },
    { icon: CloudCog, name: 'OpenAI', detail: '요약, 분류, 임베딩 API 선택 가능', state: '미설정', tone: 'mixed' }
  ];

  const chartRows = [
    ['출시 초기', '2024.05', '62%', '62%', '26%', '12%'],
    ['안정성 패치', '2024.06', '68%', '68%', '20%', '12%'],
    ['밸런스 1차', '2024.08', '64%', '64%', '25%', '11%'],
    ['콘텐츠 확장', '2024.10', '76%', '76%', '15%', '9%'],
    ['패치 1.2', '2025.02', '73%', '73%', '17%', '10%']
  ];

  const reviews: Review[] = [
    {
      language: 'EN',
      reaction: 'bad',
      playtime: '38.4h',
      topic: '후반 반복성',
      summary: '초반 전투는 훌륭하지만 30시간 이후 목표와 보상이 반복적으로 느껴진다는 반응입니다.'
    },
    {
      language: 'KO',
      reaction: 'good',
      playtime: '12.1h',
      topic: '전투 손맛',
      summary: '무기별 리듬과 보스전 긴장감이 좋고, 전작 팬에게 기대한 재미를 준다는 반응입니다.'
    },
    {
      language: 'ZH',
      reaction: 'mixed',
      playtime: '22.7h',
      topic: '밸런스',
      summary: '업데이트 후 특정 빌드 효율이 과도하게 낮아졌고 선택지가 줄었다는 의견입니다.'
    }
  ];

  let clusters: Array<{
    id: ClusterId;
    title: string;
    count: string;
    tone: 'good' | 'bad';
    description: string;
    tags: string[];
    samples: Array<{ language: string; playtime: string; reaction: string; text: string; score: string }>;
  }> = [
    {
      id: 'late-game',
      title: '후반 반복성과 보상 밀도',
      count: '3,812',
      tone: 'bad',
      description: '전투 자체는 좋지만 장기 플레이에서 목표와 보상 변화가 부족하다는 의견입니다.',
      tags: ['EN', 'KO', '50h+', '비추천 연결 높음'],
      samples: [
        { language: 'EN', playtime: '62.4h', reaction: '비추천', text: 'The combat is still great, but every run after the credits feels like chasing tiny upgrades.', score: '94%' },
        { language: 'KO', playtime: '48.9h', reaction: '혼합', text: '초반은 정말 좋은데, 어느 순간부터 보상 변화가 작아서 계속할 이유가 약해진다.', score: '88%' },
        { language: 'ES', playtime: '55.1h', reaction: '비추천', text: 'The loop works, but the late rewards do not justify repeating the same route again.', score: '83%' }
      ]
    },
    {
      id: 'combat',
      title: '전투 손맛과 보스전 긴장감',
      count: '8,441',
      tone: 'good',
      description: '타격감, 회피 리듬, 보스전 압박감이 핵심 강점으로 반복 언급됩니다.',
      tags: ['전체 언어', '추천 리뷰', '핵심 재미'],
      samples: [
        { language: 'EN', playtime: '14.2h', reaction: '추천', text: 'Every weapon has a rhythm, and boss fights keep me locked in without feeling cheap.', score: '91%' },
        { language: 'KO', playtime: '12.1h', reaction: '추천', text: '무기별 리듬이 달라서 전투가 계속 새롭고, 보스전 긴장감이 좋다.', score: '87%' }
      ]
    },
    {
      id: 'balance',
      title: '무기 밸런스와 빌드 선택지',
      count: '2,406',
      tone: 'bad',
      description: '패치 이후 선호 빌드가 좁아졌고 실험 동기가 줄었다는 장기 유저 반응입니다.',
      tags: ['패치 후 증가', 'ZH', '25h+'],
      samples: [
        { language: 'ZH', playtime: '31.7h', reaction: '비추천', text: 'After the patch, fewer builds feel worth trying and the weaker weapons fall behind too much.', score: '89%' },
        { language: 'EN', playtime: '27.8h', reaction: '혼합', text: 'The balance pass solved one problem but made experimentation less rewarding.', score: '84%' }
      ]
    },
    {
      id: 'art',
      title: '아트와 캐릭터 매력',
      count: '7,912',
      tone: 'good',
      description: '캐릭터 표현, 일러스트, 분위기는 지역과 플레이타임을 가리지 않고 강하게 호평받습니다.',
      tags: ['공통 강점', '추천 유지', '복귀 유저'],
      samples: [
        { language: 'JA', playtime: '8.3h', reaction: '추천', text: 'The character art and atmosphere are outstanding, and every new interaction feels worth seeing.', score: '90%' },
        { language: 'EN', playtime: '21.6h', reaction: '추천', text: 'The art direction carries so much personality that even downtime feels enjoyable.', score: '86%' }
      ]
    }
  ];

  let activeTab: TabId = 'dashboard';
  let activeCluster: ClusterId = 'late-game';
  let activeSegment = '추천율';
  let apiState: 'checking' | 'online' | 'offline' = 'checking';
  let apiMessage = '백엔드 연결 확인 중';
  let isRefreshing = false;
  let refreshState = '대기 중';

  $: selectedCluster = clusters.find((cluster) => cluster.id === activeCluster) ?? clusters[0];

  onMount(async () => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 1800);

    try {
      const response = await fetch(`${API_BASE}/health`, { signal: controller.signal });
      apiState = response.ok ? 'online' : 'offline';
      apiMessage = response.ok ? '백엔드 연결됨' : `백엔드 응답 오류 ${response.status}`;
      if (response.ok) {
        await loadApiData();
      }
    } catch {
      apiState = 'offline';
      apiMessage = '백엔드 미연결, 샘플 데이터 표시 중';
    } finally {
      window.clearTimeout(timeout);
    }
  });

  async function loadApiData() {
    const [dashboard, apiClusters] = await Promise.all([
      requestJson<ApiDashboard>('/dashboard'),
      requestJson<ApiCluster[]>('/clusters')
    ]);

    positiveRatio = Math.round(dashboard.positive_ratio * 100);
    projectReviewCount = formatCount(dashboard.total_reviews);
    projectLanguageCount = formatCount(dashboard.languages);
    kpis = [
      ['수집 리뷰', formatCount(dashboard.total_reviews), latestLabel(dashboard.latest_review_at)],
      ['비추천 리뷰', formatCount(dashboard.negative_reviews), 'DuckDB 기준'],
      ['대표 클러스터', formatCount(dashboard.clusters), '현재 분석 결과'],
      ['근거 리뷰', formatCount(dashboard.evidence_items), '리포트 검증용']
    ];
    metrics = [
      ['마지막 갱신', latestLabel(dashboard.latest_review_at), 'Steam app/1145350'],
      ['원본 리뷰', formatCount(dashboard.total_reviews), 'DuckDB 저장 완료'],
      ['분석 대기', '0', '샘플 데이터 기준'],
      ['오프토픽', '별도 보관', '리뷰 폭탄은 분리 분석']
    ];

    if (apiClusters.length > 0) {
      clusters = await Promise.all(apiClusters.slice(0, 6).map(mapApiCluster));
      activeCluster = clusters[0].id;
    }
  }

  async function refreshSteamReviews() {
    isRefreshing = true;
    refreshState = '리뷰 갱신 중';
    try {
      const response = await fetch(`${API_BASE}/refresh-steam`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_id: '1145350', max_reviews: 25, use_live_steam: false })
      });
      if (!response.ok) {
        throw new Error(`Refresh failed: ${response.status}`);
      }
      const result = (await response.json()) as { inserted_reviews: number; updated_reviews: number; source: string };
      refreshState = `${formatCount(result.inserted_reviews)}개 추가 · ${formatCount(result.updated_reviews)}개 갱신`;
      await loadApiData();
      apiState = 'online';
      apiMessage = '백엔드 연결됨';
    } catch {
      refreshState = '갱신 실패';
      apiState = 'offline';
      apiMessage = '백엔드 갱신 실패';
    } finally {
      isRefreshing = false;
    }
  }

  async function requestJson<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`);
    if (!response.ok) {
      throw new Error(`API request failed: ${path}`);
    }
    return response.json() as Promise<T>;
  }

  async function mapApiCluster(cluster: ApiCluster) {
    const samples = await requestJson<ApiReview[]>(`/clusters/${cluster.id}/reviews?limit=3`);
    const tone: 'good' | 'bad' = cluster.sentiment === 'positive' ? 'good' : 'bad';
    return {
      id: String(cluster.id),
      title: cluster.label,
      count: formatCount(cluster.review_count),
      tone,
      description: cluster.summary,
      tags: [cluster.language ?? '전체 언어', sentimentLabel(cluster.sentiment), `평균 신뢰 ${Math.round(cluster.avg_weighted_score * 100)}%`],
      samples: samples.map((sample) => ({
        language: steamLanguageLabel(sample.language),
        playtime: formatPlaytime(sample.playtime_at_review),
        reaction: sample.voted_up ? '추천' : '비추천',
        text: sample.review,
        score: `${Math.round(sample.weighted_vote_score * 100)}%`
      }))
    };
  }

  function formatCount(value: number) {
    return new Intl.NumberFormat('ko-KR').format(value);
  }

  function formatPlaytime(minutes: number) {
    if (!minutes) return '미상';
    return `${(minutes / 60).toFixed(1)}h`;
  }

  function latestLabel(value: string | null) {
    if (!value) return '수집 기록 없음';
    return new Intl.DateTimeFormat('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
  }

  function sentimentLabel(value: string) {
    if (value === 'positive') return '추천 연결 높음';
    if (value === 'negative') return '비추천 연결 높음';
    return '혼합 반응';
  }

  function steamLanguageLabel(value: string) {
    const labels: Record<string, string> = {
      english: 'EN',
      koreana: 'KO',
      schinese: 'ZH',
      japanese: 'JA',
      spanish: 'ES'
    };
    return labels[value] ?? value.toUpperCase();
  }

  function setTab(tab: TabId) {
    activeTab = tab;
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  function reactionLabel(reaction: Review['reaction']) {
    return reaction === 'good' ? '추천' : reaction === 'bad' ? '비추천' : '혼합';
  }
</script>

<svelte:head>
  <title>ReviewForge</title>
  <meta
    name="description"
    content="Local Steam review analysis dashboard for ReviewForge."
  />
</svelte:head>

<div class="app">
  <aside class="sidebar" aria-label="주요 탐색">
    <div class="brand">
      <div class="brand-mark">R</div>
      <div class="brand-text">
        <strong>ReviewForge</strong>
        <span>Steam 리뷰 분석</span>
      </div>
    </div>

    <nav class="nav-group">
      {#each groupedTabs as group}
        <div class="nav-label">{group.group}</div>
        {#each group.items as tab}
          <button
            class:active={activeTab === tab.id}
            class="nav-item"
            type="button"
            on:click={() => setTab(tab.id)}
          >
            <svelte:component this={tab.icon} />
            <span>{tab.label}</span>
          </button>
        {/each}
      {/each}
    </nav>

    <div class="side-note">
      <b>현재 프로젝트</b>
      <dl>
        <dt>게임</dt>
        <dd>Hades II</dd>
        <dt>리뷰</dt>
        <dd>{projectReviewCount}</dd>
        <dt>언어</dt>
        <dd>{projectLanguageCount}</dd>
      </dl>
    </div>
  </aside>

  <div class="workspace">
    <header class="topbar">
      <label class="searchbar">
        <Search />
        <input value="Hades II · app/1145350" aria-label="Steam 게임 검색" />
      </label>
      <div class="actions">
        <span class="status" class:offline={apiState !== 'online'}>{apiMessage}</span>
        <button class="icon-button" title="설정" type="button" on:click={() => setTab('settings')}><Settings2 /></button>
        <button class="ghost-button" title="Steam에서 최신 리뷰를 가져와 로컬 분석 데이터를 갱신" type="button" disabled={isRefreshing} on:click={refreshSteamReviews}>
          <Database /><span>{isRefreshing ? '갱신 중' : '리뷰 갱신'}</span>
        </button>
        <button class="primary-button" type="button" on:click={() => setTab('report')}><Sparkles /><span>AI 리포트</span></button>
      </div>
    </header>

    <div class="content">
      <main class="main">
        <section class:active={activeTab === 'dashboard'} class="tab-view" aria-label="대시보드">
          <section class="overview">
            <div class="panel game-summary">
              <div class="game-title">
                <div class="section-head">
                  <div>
                    <h1>Hades II 리뷰 반응</h1>
                    <p>최근 패치 이후 부정 리뷰는 줄었지만, 후반 반복성과 밸런스 불만은 계속 남아 있습니다.</p>
                  </div>
                </div>
                <div class="tag-row">
                  <span class="tag">2024.05.06 - 2026.05.18</span>
                  <span class="tag">전체 언어</span>
                  <span class="tag">Steam 구매자</span>
                  <span class="tag">패치 7개</span>
                </div>
              </div>
              <div class="score-ring" style={`--score: ${positiveRatio}%`} aria-label={`추천 비율 ${positiveRatio}퍼센트`}>
                <strong>{positiveRatio}%</strong>
                <span>추천</span>
              </div>
            </div>

            <div class="kpis" aria-label="요약 지표">
              {#each kpis as item}
                <div class="kpi"><span>{item[0]}</span><strong>{item[1]}</strong><small>{item[2]}</small></div>
              {/each}
            </div>
          </section>

          <FilterBar />

          <section class="workspace-grid">
            <div class="panel timeline">
              <div class="timeline-toolbar">
                <div class="section-head">
                  <div>
                    <h2>패치별 반응 변화</h2>
                    <p>각 기간의 추천, 비추천, 혼합 반응 비율입니다.</p>
                  </div>
                </div>
                <div class="segmented" aria-label="차트 기준">
                  {#each ['추천율', '불만', '언어'] as segment}
                    <button class="segment" class:active={activeSegment === segment} type="button" on:click={() => (activeSegment = segment)}>{segment}</button>
                  {/each}
                </div>
              </div>

              <div class="chart" aria-label="패치별 반응 차트">
                {#each chartRows as row}
                  <div class="chart-row">
                    <div class="chart-label"><strong>{row[0]}</strong><span>{row[1]}</span></div>
                    <div class="bar-track" style={`--pos: ${row[3]}; --neg: ${row[4]}; --neu: ${row[5]}`}><span></span><span></span><span></span></div>
                    <div class="bar-score">{row[2]}</div>
                  </div>
                {/each}
              </div>
              <div class="legend">
                <span><b style="background: var(--positive)"></b>추천</span>
                <span><b style="background: var(--negative)"></b>비추천</span>
                <span><b style="background: var(--neutral)"></b>혼합</span>
              </div>
            </div>

            <div class="topics">
              <TopicPanel title="불만 토픽" subtitle="비추천 전환과 강하게 연결된 항목입니다." topics={[['후반 반복성', '비슷한 리뷰 3,812개', '+18%', 'up'], ['무기 밸런스 편차', '비슷한 리뷰 2,406개', '+11%', 'up'], ['UI 가독성', '비슷한 리뷰 1,744개', '+2%', 'flat']]} />
              <TopicPanel title="호평 토픽" subtitle="추천 리뷰에서 반복적으로 나타난 강점입니다." topics={[['전투 손맛', '비슷한 리뷰 8,441개', '유지', 'down'], ['아트와 캐릭터', '비슷한 리뷰 7,912개', '+6%', 'down'], ['음악과 분위기', '비슷한 리뷰 4,320개', '+4%', 'down']]} />
            </div>
          </section>

          <ReviewTable title="대표 리뷰" subtitle="각 클러스터를 대표하는 원문과 자동 번역 요약입니다." />
        </section>

        <section class:active={activeTab === 'data'} class="tab-view" aria-label="데이터 갱신">
          <PageIntro title="데이터 갱신" subtitle="Steam 리뷰를 가져오고, 원본 저장과 분석 대기 상태를 확인합니다.">
            <button class="primary-button" type="button" disabled={isRefreshing} on:click={refreshSteamReviews}><DownloadCloud /><span>{isRefreshing ? '가져오는 중' : '리뷰 가져오기'}</span></button>
          </PageIntro>
          <div class="method-note"><Info /><div><strong>최근 갱신</strong><span>{refreshState}</span></div></div>
          <MetricStrip items={metrics} />
          <section class="control-grid">
            <FormPanel title="수집 조건" subtitle="Steam API에서 가져올 범위와 저장 방식을 정합니다." fields={['Steam App ID', '언어', '리뷰 타입', '구매 유형', '오프토픽 리뷰', '페이지 크기']} />
            <RunPanel />
          </section>
          <AuditPanel title="데이터 품질 체크" rows={[['중복 리뷰', 'review_id 기준 중복 0건. 재수집해도 같은 리뷰는 덮어씁니다.', '정상', 'good'], ['플레이타임 누락', '전체 리뷰의 1.8%는 작성 시점 플레이타임이 없습니다.', '허용', 'mixed'], ['언어 불일치', 'Steam 언어값과 자동 감지 언어가 다른 리뷰 2.6%는 검토 플래그를 붙입니다.', '검토', 'mixed']]} />
          <SimpleTable title="저장되는 원본 필드" headers={['필드', '용도', '화면 연결']} rows={[['timestamp_created', '기간 집계와 이벤트 전후 비교', '비교 기준, 대시보드'], ['voted_up', '추천/비추천 기본 신호', '모든 차트'], ['language', '언어권 비교와 번역 대상 결정', '언어권 비교'], ['playtime_at_review', '플레이타임 구간 분석', '필터, 클러스터']]} />
        </section>

        <section class:active={activeTab === 'patches'} class="tab-view" aria-label="비교 기준">
          <PageIntro title="비교 기준" subtitle="패치, 세일, 서버 장애 같은 날짜를 입력해 리뷰를 전후 기간으로 나눠 봅니다."><span class="status">기준 이벤트 11개</span></PageIntro>
          <section class="event-guide">
            {#each [['1', '날짜를 등록합니다', 'Steam 리뷰만으로는 패치일을 알 수 없어서 패치, 세일, 운영 이슈를 직접 넣습니다.'], ['2', '전후 기간을 정합니다', '예: 패치 전 14일과 후 14일의 추천율, 토픽, 대표 리뷰를 비교합니다.'], ['3', '변화를 해석합니다', '패치가 원인이라고 단정하지 않고, 같은 시점에 늘어난 반응으로 표시합니다.']] as step}
              <article class="step-card"><span class="step-number">{step[0]}</span><div><h3>{step[1]}</h3><p>{step[2]}</p></div></article>
            {/each}
          </section>
          <MetricStrip items={[['현재 비교 창', '전후 14일', '이벤트별 변경 가능'], ['가장 큰 변화', '+12%p', '콘텐츠 확장 전후'], ['같이 표시할 변수', '세일', '유입 증가와 분리해서 해석'], ['해석 방식', '상관', '인과로 단정하지 않음']]} />
          <FormPanel title="기준 이벤트 추가" subtitle="이 날짜를 기준으로 리뷰를 전후로 나눠 비교합니다." fields={['이벤트 이름', '이벤트 유형', '날짜', '비교 창']} action="이벤트 추가" />
          <section class="detail-grid">
            <div class="panel">
              <div class="section-head"><div><h2>등록된 기준과 전후 변화</h2><p>각 이벤트의 전 14일과 후 14일 리뷰를 비교한 결과입니다.</p></div></div>
              <div class="patch-list">
                {#each [['2024.05.06', '얼리 액세스 출시', '출시 후 14일 기준 추천율입니다. 아트, 전투, 음악 호평과 크래시 불만이 함께 나타납니다.', '추천 62%'], ['2024.06.18', '안정성 패치', '패치 후 크래시, 로딩, 진행 불가 언급이 줄었습니다.', '+6%p'], ['2024.08.02', '밸런스 1차', '패치 후 특정 무기와 빌드 효율 언급이 늘었습니다.', '-4%p'], ['2024.10.21', '콘텐츠 확장', '패치 후 신규 콘텐츠, 복귀, 가격 대비 만족 언급이 함께 늘어났습니다.', '+12%p']] as event}
                  <article class="topic-item"><div><strong>{event[1]}</strong><span>{event[0]} · {event[2]}</span></div><span class="status">{event[3]}</span></article>
                {/each}
              </div>
            </div>
            <TopicPanel title="선택 이벤트의 변화" subtitle="현재 선택한 이벤트 전후로 함께 늘어난 표현입니다." topics={[['“too repetitive”', '전 14일 7% -> 후 14일 25%', '+18%p', 'up'], ['“build variety”', '전 14일 5% -> 후 14일 16%', '+11%p', 'up'], ['“runs better now”', '전 14일 2% -> 후 14일 11%', '+9%p', 'down']]} />
          </section>
        </section>

        <section class:active={activeTab === 'runs'} class="tab-view" aria-label="분석 실행">
          <PageIntro title="분석 실행" subtitle="임베딩, 클러스터링, 토픽 태깅, AI 요약을 배치 작업으로 실행하고 결과를 캐시합니다."><button class="primary-button" type="button"><Play /><span>분석 시작</span></button></PageIntro>
          <MetricStrip items={[['현재 분석 버전', 'v0.4', '2026.05.19 생성'], ['처리된 리뷰', '46,935', '97.3%'], ['LLM 호출', '128', '클러스터 대표만 요약'], ['재실행 필요', '있음', '새 리뷰 1,284개']]} />
          <AuditPanel title="분석 품질" rows={[['클러스터 포함률', '분석 대상 리뷰의 91.6%가 의미 있는 클러스터에 묶였습니다.', '양호', 'good'], ['잡음 리뷰', '짧은 감탄사, ASCII 아트, 중복 문구 8.4%는 토픽 분석에서 제외했습니다.', '제외', 'mixed'], ['사람 검증', '상위 불만 클러스터 12개 중 7개는 원문 샘플 확인이 끝났습니다.', '진행', 'mixed']]} />
          <section class="control-grid"><RunPanel pipeline /><FormPanel title="실행 옵션" subtitle="속도와 비용에 영향을 주는 설정입니다." fields={['분석 범위', '임베딩 모델', '요약 모델', '요약 방식']} /></section>
        </section>

        <section class:active={activeTab === 'clusters'} class="tab-view" aria-label="리뷰 클러스터">
          <PageIntro title="리뷰 클러스터" subtitle="언어가 달라도 같은 의미의 리뷰를 묶어서 호평, 불만, 기능 요청을 한 번에 봅니다."><span class="status">31개 묶음</span></PageIntro>
          <FilterBar cluster />
          <section class="cluster-grid">
            {#each clusters as cluster}
              <button class="cluster-node" class:active={activeCluster === cluster.id} type="button" on:click={() => (activeCluster = cluster.id)}>
                <header><h3>{cluster.title}</h3><span class={`sentiment ${cluster.tone}`}>{cluster.count}</span></header>
                <p>{cluster.description}</p>
                <div class="cluster-tags">{#each cluster.tags as tag}<span class="cluster-tag">{tag}</span>{/each}</div>
              </button>
            {/each}
          </section>
          <section class="panel cluster-detail">
            <div class="detail-head"><div><h2>{selectedCluster.title}</h2><p>이 클러스터에 묶인 리뷰 중 대표성이 높은 원문 샘플입니다.</p></div><span class={`sentiment ${selectedCluster.tone}`}>{selectedCluster.tone === 'good' ? '추천 연결 높음' : '비추천 연결 높음'}</span></div>
            <div class="review-samples">
              {#each selectedCluster.samples as sample}
                <article class="review-sample"><div class="sample-meta"><strong>{sample.language}</strong><span>{sample.playtime}</span><span>{sample.reaction}</span></div><p>“{sample.text}”</p><small>대표도 {sample.score}</small></article>
              {/each}
            </div>
          </section>
        </section>

        <section class:active={activeTab === 'languages'} class="tab-view" aria-label="언어권 비교">
          <PageIntro title="언어권 비교" subtitle="글로벌 공통 이슈와 특정 언어권에서만 커지는 불만을 분리합니다."><span class="status">14개 언어</span></PageIntro>
          <MetricStrip items={[['공통 호평', '전투', '전체 언어 상위권'], ['공통 불만', '후반부', '9개 언어에서 증가'], ['지역 특이점', '가격', '중국어권 비중 높음'], ['번역 이슈', '낮음', '현재 큰 신호 없음']]} />
          <AuditPanel title="언어 데이터 품질" rows={[['표본 충분 언어', '영어, 중국어, 한국어, 일본어는 각 1,000개 이상으로 비교 가능합니다.', '4개', 'good'], ['소표본 언어', '포르투갈어, 태국어는 표본이 적어 대시보드 집계만 표시합니다.', '주의', 'mixed'], ['번역 사용', 'AI 요약에는 한국어 번역문을 쓰고, 근거 검증에는 원문을 함께 표시합니다.', '분리', 'good']]} />
          <section class="detail-grid">
            <div class="panel">
              <div class="section-head"><div><h2>언어별 반응</h2><p>추천, 비추천, 혼합 반응의 상대 비중입니다.</p></div></div>
              <div class="language-list">
                {#each [['영어', '74% · n=21,804', '후반 반복성'], ['한국어', '77% · n=2,914', '전투 손맛'], ['중국어', '68% · n=7,332', '가격/밸런스'], ['일본어', '81% · n=1,246', '캐릭터'], ['스페인어', '72% · n=884', '콘텐츠 양']] as language}
                  <div class="language-row"><strong>{language[0]}</strong><div class="spark"><b></b><b></b><b></b></div><span>{language[1]}</span><span>{language[2]}</span></div>
                {/each}
              </div>
            </div>
            <TopicPanel title="지역별 읽을거리" subtitle="기획 회의에서 따로 볼 만한 차이입니다." topics={[['중국어권', '가격과 밸런스 언급이 평균보다 높음', '주의', 'up'], ['일본어권', '캐릭터와 아트 호평 비중이 높음', '강점', 'down'], ['한국어권', '플레이타임 20시간 이후 반복성 언급 증가', '검토', 'flat']]} />
          </section>
        </section>

        <section class:active={activeTab === 'evidence'} class="tab-view" aria-label="근거 검증">
          <PageIntro title="근거 검증" subtitle="숫자로 계산된 결과와 AI가 해석한 문장을 분리해서 확인합니다."><span class="status">검토 필요 5개</span></PageIntro>
          <section class="control-grid">
            <div class="panel form-panel">
              <div class="section-head"><div><h2>주요 주장</h2><p>리포트에 들어갈 문장이 어떤 근거에서 나왔는지 확인합니다.</p></div></div>
              <div class="truth-list">
                {#each [['후반 반복성은 비추천 전환과 강하게 연결됩니다.', '비추천 리뷰 3,812개 클러스터와 50시간 이상 플레이 구간에서 함께 증가했습니다.', '숫자 근거', 'numeric'], ['기술적 불만은 안정성 패치 이후 줄었습니다.', '크래시, 로딩, 진행 불가 키워드의 비중이 전후 14일 비교에서 감소했습니다.', '숫자 근거', 'numeric'], ['유저는 전투 자체보다 오래 붙잡을 동기가 부족하다고 느낍니다.', '대표 리뷰 요약에서 나온 해석입니다. 원문 샘플 확인 후 리포트 반영이 필요합니다.', 'AI 해석', 'ai']] as claim}
                  <article class="truth-item"><div><h3>{claim[0]}</h3><p>{claim[1]}</p></div><span class={`claim ${claim[3]}`}>{claim[2]}</span></article>
                {/each}
              </div>
            </div>
            <QuotePanel />
          </section>
          <SimpleTable title="검증 큐" headers={['상태', '문장', '근거 유형', '처리']} rows={[['대기', '중국어권에서 가격 불만이 상대적으로 높습니다.', '언어별 집계', '샘플 확인'], ['확인', '아트와 캐릭터 호평은 전체 언어권에서 유지됩니다.', '클러스터 집계', '리포트 포함'], ['주의', '밸런스 패치 이후 비추천 리뷰와 밸런스 불만이 함께 증가했습니다.', '전후 비교', '문구 수정']]} />
        </section>

        <section class:active={activeTab === 'report'} class="tab-view" aria-label="리포트">
          <PageIntro title="리포트" subtitle="현재 필터와 기간을 기준으로 기획자가 바로 읽을 수 있는 요약 문서를 만듭니다."><button class="primary-button" type="button"><Sparkles /><span>다시 생성</span></button></PageIntro>
          <AuditPanel title="리포트 검증 상태" rows={[['데이터 버전', 'reviews_2026-05-19_0302 · 새 리뷰 1,284개는 아직 반영 전입니다.', '갱신 필요', 'mixed'], ['AI 생성 범위', '전체 원문이 아니라 클러스터 대표 리뷰 128묶음만 요약했습니다.', '절약', 'good'], ['근거 확인', '핵심 주장 9개 중 6개는 원문 샘플 확인 완료, 3개는 검토 대기입니다.', '검토', 'mixed']]} />
          <section class="report-layout">
            <article class="panel report-doc">
              {#each [['요약', '최근 패치 이후 기술적 불만은 줄었지만, 장기 플레이 구간에서는 보상 루프와 빌드 다양성에 대한 불만이 유지됩니다. 핵심 전투 평가는 여전히 강점입니다.'], ['호평', '전투 손맛, 보스전 긴장감, 아트와 캐릭터 매력이 전체 언어권에서 반복적으로 나타납니다. 이 강점은 신규 유저와 복귀 유저 양쪽에서 유지됩니다.'], ['불만', '후반 반복성, 무기 밸런스 편차, UI 가독성이 우선 검토 후보입니다. 특히 후반 반복성은 비추천 전환과 가장 강하게 연결됩니다.'], ['다음 액션', '다음 패치에서는 후반 보상 루프와 빌드 선택지를 먼저 검토하고, UI 가독성은 낮은 비용의 빠른 개선 후보로 분리하는 것이 좋습니다.']] as block}
                <section class="report-block"><h2>{block[0]}</h2><p>{block[1]}</p></section>
              {/each}
            </article>
            <aside class="panel export-stack">
              <div class="section-head"><div><h2>내보내기</h2><p>회의 자료로 옮길 단위를 고릅니다.</p></div></div>
              {#each exportRows as row}
                {@const ExportIcon = row.icon}
                <div class="export-row"><span>{row.label}</span><button class="icon-button" title={row.label} type="button"><ExportIcon /></button></div>
              {/each}
            </aside>
          </section>
        </section>

        <section class:active={activeTab === 'settings'} class="tab-view" aria-label="모델 설정">
          <PageIntro title="모델 설정" subtitle="분석에 쓰는 로컬/클라우드 모델과 비용, 품질, 개인정보 옵션을 관리합니다."><button class="ghost-button" type="button"><PlugZap /><span>연결 확인</span></button></PageIntro>
          <div class="method-note"><Info /><div><strong>구현 기준</strong><span> 요약/분류는 LLM으로 처리하고, 다국어 의미 묶기는 임베딩 모델로 따로 실행합니다. 긴 작업은 백엔드 작업 큐에 넣고 화면은 진행률만 갱신합니다.</span></div></div>
          <section class="settings-grid">
            <div class="panel connection-card">
              <div class="section-head"><div><h2>LLM 연결</h2><p>요약과 분류는 선택한 모델로 실행합니다.</p></div></div>
              {#each modelOptions as model}
                {@const ModelIcon = model.icon}
                <div class="model-option"><ModelIcon /><div><strong>{model.name}</strong><span>{model.detail}</span></div><span class={`sentiment ${model.tone}`}>{model.state}</span></div>
              {/each}
            </div>
            <FormPanel title="분석 기본값" subtitle="느린 작업과 비용이 큰 작업은 명시적으로 실행합니다." fields={['기본 요약 모델', '기본 임베딩', '리포트 생성', '캐시 정책', '원문 전송', '실패 처리']} />
          </section>
          <SimpleTable title="구현 메모" headers={['화면', '백엔드 역할', '기술']} rows={[['데이터 갱신', 'Steam API 호출, cursor 저장, DuckDB upsert', 'FastAPI + DuckDB'], ['분석 실행', '임베딩/클러스터링 배치 작업과 진행률 저장', 'Python worker'], ['AI 리포트', '클러스터 대표 리뷰를 LLM에 보내고 결과 캐시', 'LM Studio/Claude/OpenAI'], ['근거 검증', '요약 문장과 원문 리뷰 연결 관계 저장', 'DuckDB']]} />
        </section>
      </main>

      <aside class="inspector" aria-label="AI 분석 패널">
        <div class="inspector-inner">
          <section class="panel ai-panel">
            <div class="section-head"><div><h3>AI 브리프</h3><p>패치 1.2 이후</p></div><span class="status">LM Studio</span></div>
            <div class="ai-summary">
              <p>기술적 불만은 줄었지만, 장기 플레이 구간에서 반복성과 보상 밀도에 대한 불만이 유지되고 있습니다.</p>
              <p>비추천 리뷰와 가장 강하게 함께 나타나는 표현은 “좋은 전투를 오래 붙잡을 동기 부족”에 가깝습니다.</p>
            </div>
          </section>
          <AuditPanel title="분석 신뢰도" rows={[['데이터 최신성', '최근 리뷰 1,284개는 아직 클러스터링 전입니다.', '주의', 'mixed'], ['표본 크기', '현재 필터 기준 리뷰 12,430개로 비교 가능 범위입니다.', '충분', 'good'], ['AI 문장 검증', '리포트 후보 9개 중 6개가 원문 샘플과 연결됐습니다.', '진행', 'mixed']]} compact />
          <section class="panel priority">
            <div class="section-head"><div><h3>기획 우선순위</h3><p>빈도, 심각도, 최근성을 함께 반영했습니다.</p></div></div>
            <ol class="priority-list">
              {#each [['1', '후반 보상 루프', '고빈도 · 장기 유저 중심', '높음', 'bad'], ['2', '무기 밸런스 편차', '패치 후 증가', '높음', 'bad'], ['3', 'UI 가독성', '낮은 수정 난이도', '중간', 'mixed']] as item}
                <li><span class="rank">{item[0]}</span><div><strong>{item[1]}</strong><span>{item[2]}</span></div><span class={`sentiment ${item[4]}`}>{item[3]}</span></li>
              {/each}
            </ol>
          </section>
          <QuotePanel />
        </div>
      </aside>
    </div>
  </div>
</div>

