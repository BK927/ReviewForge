<script lang="ts">
  import { onMount } from 'svelte';
  import {
    Activity,
    Check,
    Clock,
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
    Library,
    LayoutDashboard,
    MessagesSquare,
    Network,
    Play,
    PlugZap,
    Plus,
    ScanSearch,
    Search,
    Server,
    Settings2,
    SlidersHorizontal,
    Sparkles
  } from 'lucide-svelte';
  import AuditPanel from '$lib/AuditPanel.svelte';
  import MetricStrip from '$lib/MetricStrip.svelte';
  import PageIntro from '$lib/PageIntro.svelte';
  import SimpleTable from '$lib/SimpleTable.svelte';
  import TopicPanel from '$lib/TopicPanel.svelte';

  const API_BASE = 'http://127.0.0.1:8000/api';
  const DEFAULT_APP_ID = '1145350';

  type TabId =
    | 'library'
    | 'dashboard'
    | 'data'
    | 'patches'
    | 'runs'
    | 'clusters'
    | 'languages'
    | 'evidence'
    | 'report'
    | 'settings';

  type Tone = 'good' | 'bad' | 'mixed';
  type ClusterId = string;
  type LibraryFilter = 'all' | 'ready' | 'needs-analysis' | 'needs-sync' | 'watch';
  type ClusterToneFilter = 'all' | 'bad' | 'mixed' | 'good';

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

  type ApiLanguage = {
    language: string;
    review_count: number;
    positive_count: number;
    negative_count: number;
    positive_ratio: number;
    avg_weighted_score: number;
  };

  type ApiEvent = {
    id: number;
    title: string;
    event_type: string;
    description?: string | null;
    occurred_at: string;
    created_at?: string;
  };

  type ApiCluster = {
    id: number;
    label: string;
    summary: string;
    sentiment: string;
    language: string | null;
    review_count: number;
    avg_weighted_score: number;
    exemplar_review_id?: string | null;
    created_at?: string;
  };

  type ApiReview = {
    recommendation_id?: string;
    language: string;
    review: string;
    voted_up: boolean;
    weighted_vote_score: number;
    playtime_at_review: number;
    cluster_score?: number;
    steam_created_at?: string | null;
  };

  type ApiEvidence = {
    id: number;
    review_id: string;
    cluster_id: number | null;
    quote: string;
    evidence_type: string;
    note: string | null;
    created_at: string;
  };

  type ApiReport = {
    id: number;
    title: string;
    summary: string;
    filters: Record<string, unknown>;
    created_at: string;
  };

  type ApiSettingValue = {
    key: string;
    value: Record<string, unknown>;
    updated_at: string | null;
  };

  type ApiGame = {
    app_id: string;
    name: string;
    short_name?: string | null;
    status?: string | null;
    note?: string | null;
    tags?: string[] | null;
    review_count?: number;
    language_count?: number;
    positive_ratio?: number | null;
    cluster_count?: number;
    evidence_count?: number;
    last_sync_at?: string | null;
    last_refreshed_at?: string | null;
    latest_review_at?: string | null;
    last_analysis_at?: string | null;
    next_action?: 'sync' | 'analyze' | 'open' | string;
  };

  type ApiJob = {
    id: number;
    job_type: string;
    status: string;
    message: string | null;
    progress: number;
    started_at: string;
    finished_at: string | null;
    metadata?: Record<string, unknown>;
  };

  type RefreshResult = {
    job?: ApiJob;
    job_id?: number;
    inserted_reviews?: number;
    updated_reviews?: number;
    source?: string;
    status?: string;
    message?: string;
  };

  type AnalysisRunResult = {
    analysis_run?: ApiAnalysisRun;
    job?: ApiJob;
    job_id?: number;
    id?: number;
    status?: string;
    message?: string;
    progress?: number;
    clusterer?: string;
    reviews_analyzed?: number;
    clusters_created?: number;
    evidence_created?: number;
  };

  type ApiAnalysisRun = {
    id: number;
    app_id?: string | null;
    status: string;
    progress: number;
    message?: string | null;
    params: Record<string, unknown>;
    started_at: string;
    finished_at?: string | null;
  };

  type TimelineBucket = {
    label: string;
    bucket: string;
    positive_ratio: number;
    negative_ratio: number;
    mixed_ratio: number;
    review_count: number;
  };

  type ClusterView = {
    id: ClusterId;
    title: string;
    count: string;
    countValue: number;
    tone: Tone;
    description: string;
    tags: string[];
    backend: boolean;
    samples: ReviewSample[];
  };

  type ReviewSample = {
    language: string;
    playtime: string;
    reaction: string;
    reactionTone: Tone;
    text: string;
    score: string;
  };

  type EventImpactView = {
    beforeCount: number;
    afterCount: number;
    beforePositiveRatio: number | null;
    afterPositiveRatio: number | null;
    deltaPoints: number | null;
    notes: string[];
    topics: string[][];
  };

  type IconComponent = typeof Copy;

  type ModelOption = {
    icon: IconComponent;
    name: string;
    detail: string;
    state: string;
    tone: Tone;
  };

  type RunStatusRow = {
    icon: IconComponent;
    title: string;
    detail: string;
    state: string;
    tone: Tone;
  };

  type GameProject = {
    id: string;
    name: string;
    appId: string;
    shortName: string;
    status: string;
    statusTone: Tone;
    reviewCount: number;
    languages: number;
    positiveRatio: number;
    clusters: number;
    evidenceItems: number;
    lastSync: string | null;
    lastAnalysis: string | null;
    queue: string;
    note: string;
    tags: string[];
    nextAction: 'sync' | 'analyze' | 'open';
  };

  const tabs: Array<{ id: TabId; label: string; group: 'Project' | 'Analysis'; icon: IconComponent }> = [
    { id: 'library', label: '게임 라이브러리', group: 'Project', icon: Library },
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

  const exportRows: Array<{ label: string; icon: IconComponent }> = [
    { label: '요약 리포트', icon: Copy },
    { label: '대표 리뷰 CSV', icon: Download },
    { label: '패치별 차트 PNG', icon: ImageDown },
    { label: '기획 우선순위 표', icon: FileText }
  ];

  const libraryFilterOptions: Array<{ id: LibraryFilter; label: string }> = [
    { id: 'all', label: '전체' },
    { id: 'ready', label: '분석 완료' },
    { id: 'needs-analysis', label: '분석 대기' },
    { id: 'needs-sync', label: '수집 필요' },
    { id: 'watch', label: '관찰' }
  ];

  const clusterToneOptions: Array<{ id: ClusterToneFilter; label: string }> = [
    { id: 'all', label: '전체' },
    { id: 'bad', label: '불만' },
    { id: 'mixed', label: '혼합' },
    { id: 'good', label: '호평' }
  ];

  const emptyDashboard: ApiDashboard = {
    total_reviews: 0,
    positive_reviews: 0,
    negative_reviews: 0,
    positive_ratio: 0,
    languages: 0,
    clusters: 0,
    evidence_items: 0,
    latest_review_at: null
  };

  const sampleDashboard: ApiDashboard = {
    total_reviews: 48_219,
    positive_reviews: 35_200,
    negative_reviews: 13_019,
    positive_ratio: 0.73,
    languages: 14,
    clusters: 31,
    evidence_items: 128,
    latest_review_at: '2026-05-18T11:12:00Z'
  };

  const sampleTimeline: TimelineBucket[] = [
    { label: '출시 초기', bucket: '2024-05', positive_ratio: 0.62, negative_ratio: 0.26, mixed_ratio: 0.12, review_count: 8200 },
    { label: '안정성 패치', bucket: '2024-06', positive_ratio: 0.68, negative_ratio: 0.2, mixed_ratio: 0.12, review_count: 6100 },
    { label: '밸런스 1차', bucket: '2024-08', positive_ratio: 0.64, negative_ratio: 0.25, mixed_ratio: 0.11, review_count: 5400 },
    { label: '콘텐츠 확장', bucket: '2024-10', positive_ratio: 0.76, negative_ratio: 0.15, mixed_ratio: 0.09, review_count: 7200 },
    { label: '패치 1.2', bucket: '2025-02', positive_ratio: 0.73, negative_ratio: 0.17, mixed_ratio: 0.1, review_count: 6800 }
  ];

  const sampleLanguages: ApiLanguage[] = [
    { language: 'english', review_count: 21804, positive_count: 16135, negative_count: 5669, positive_ratio: 0.74, avg_weighted_score: 0.79 },
    { language: 'koreana', review_count: 2914, positive_count: 2244, negative_count: 670, positive_ratio: 0.77, avg_weighted_score: 0.76 },
    { language: 'schinese', review_count: 7332, positive_count: 4986, negative_count: 2346, positive_ratio: 0.68, avg_weighted_score: 0.72 },
    { language: 'japanese', review_count: 1246, positive_count: 1009, negative_count: 237, positive_ratio: 0.81, avg_weighted_score: 0.8 }
  ];

  const sampleClusters: ClusterView[] = [
    {
      id: 'sample-late-game',
      title: '후반 반복성과 보상 밀도',
      count: '3,812',
      countValue: 3812,
      tone: 'bad',
      description: '샘플 데이터입니다. 장기 플레이에서 반복성, 보상 변화 부족, 루프 피로가 함께 언급됩니다.',
      tags: ['샘플', 'EN/KO', '비추천 연결 높음'],
      backend: false,
      samples: [
        {
          language: 'EN',
          playtime: '62.4h',
          reaction: '비추천',
          reactionTone: 'bad',
          text: 'The combat is still great, but every run after the credits feels like chasing tiny upgrades.',
          score: '94%'
        },
        {
          language: 'KO',
          playtime: '48.9h',
          reaction: '혼합',
          reactionTone: 'mixed',
          text: '초반은 정말 좋은데, 어느 순간부터 보상 변화가 작아서 계속할 이유가 약해진다.',
          score: '88%'
        }
      ]
    },
    {
      id: 'sample-combat',
      title: '전투 손맛과 보스전 긴장감',
      count: '8,441',
      countValue: 8441,
      tone: 'good',
      description: '샘플 데이터입니다. 타격감, 회피 리듬, 보스전 압박감이 강점으로 반복 언급됩니다.',
      tags: ['샘플', '전체 언어', '추천 연결 높음'],
      backend: false,
      samples: [
        {
          language: 'EN',
          playtime: '14.2h',
          reaction: '추천',
          reactionTone: 'good',
          text: 'Every weapon has a rhythm, and boss fights keep me locked in without feeling cheap.',
          score: '91%'
        },
        {
          language: 'KO',
          playtime: '12.1h',
          reaction: '추천',
          reactionTone: 'good',
          text: '무기별 리듬이 달라서 전투가 계속 새롭고, 보스전 긴장감이 좋다.',
          score: '87%'
        }
      ]
    }
  ];

  const sampleGameProjects: GameProject[] = [
    {
      id: '1145350',
      name: 'Hades II',
      appId: '1145350',
      shortName: 'HII',
      status: '분석 완료',
      statusTone: 'good',
      reviewCount: 48_219,
      languages: 14,
      positiveRatio: 0.73,
      clusters: 31,
      evidenceItems: 128,
      lastSync: '2026-05-18T11:12:00Z',
      lastAnalysis: '2026-05-19T05:24:37Z',
      queue: '패치 1.2 이후 장기 플레이 불만 재확인',
      note: '현재 목업의 실제 데이터 기준 게임입니다.',
      tags: ['라이브 분석', '패치 추적', '주요 프로젝트'],
      nextAction: 'open'
    },
    {
      id: '730',
      name: 'Counter-Strike 2',
      appId: '730',
      shortName: 'CS2',
      status: '수집됨',
      statusTone: 'mixed',
      reviewCount: 5,
      languages: 2,
      positiveRatio: 0.6,
      clusters: 0,
      evidenceItems: 0,
      lastSync: '2026-05-19T04:38:00Z',
      lastAnalysis: null,
      queue: '표본을 늘린 뒤 클러스터링 필요',
      note: 'DB에는 들어갈 수 있지만 화면의 게임별 분리가 아직 필요합니다.',
      tags: ['수집 테스트', '분석 대기'],
      nextAction: 'analyze'
    },
    {
      id: '2379780',
      name: 'Balatro',
      appId: '2379780',
      shortName: 'BAL',
      status: '등록 예정',
      statusTone: 'mixed',
      reviewCount: 0,
      languages: 0,
      positiveRatio: 0,
      clusters: 0,
      evidenceItems: 0,
      lastSync: null,
      lastAnalysis: null,
      queue: 'Steam App ID 등록 후 첫 수집',
      note: '여러 게임을 비교할 때 필요한 빈 프로젝트 상태입니다.',
      tags: ['신규 후보', '비교군'],
      nextAction: 'sync'
    }
  ];

  const gameImplementationRows: string[][] = [
    ['게임 목록', 'app_id, 이름, 별칭, 메모를 저장하는 games 테이블', '필수', 'good'],
    ['현재 선택 게임', '모든 API 요청에 선택 app_id를 전달', '필수', 'good'],
    ['대시보드 분리', '요약, 언어, 리포트도 app_id 필터 지원', '필수', 'mixed'],
    ['비교 보기', '게임 간 추천율과 불만 토픽을 나란히 비교', '후순위', 'mixed']
  ];

  const defaultModelOptions: ModelOption[] = [
    { icon: Server, name: 'LM Studio', detail: '/api/settings/models 응답 대기 중', state: '상태 미확인', tone: 'mixed' },
    { icon: Cloud, name: 'Claude', detail: '클라우드 리포트 생성 공급자', state: '미설정', tone: 'mixed' },
    { icon: CloudCog, name: 'OpenAI', detail: '요약, 분류, 임베딩 API 공급자', state: '미설정', tone: 'mixed' }
  ];

  let gameProjects: GameProject[] = sampleGameProjects;
  let activeTab: TabId = 'library';
  let selectedGameId = gameProjects[0].id;
  let activeCluster: ClusterId = sampleClusters[0].id;
  let activeSegment = '추천율';
  let apiState: 'checking' | 'online' | 'partial' | 'offline' = 'checking';
  let apiMessage = '백엔드 연결 확인 중';
  let dataSource: 'api' | 'sample' | 'empty' = 'empty';
  let endpointWarnings: string[] = [];
  let isLoading = true;

  let dashboard = emptyDashboard;
  let timelineRows: TimelineBucket[] = [];
  let languages: ApiLanguage[] = [];
  let events: ApiEvent[] = [];
  let selectedEventId = '';
  let impactWindowDays = 14;
  let eventImpact: EventImpactView | null = null;
  let eventImpactState = '이벤트를 선택하면 전후 변화를 불러옵니다.';
  let clusters: ClusterView[] = [];
  let clusterSource: 'backend' | 'sample' | 'empty' = 'empty';
  let selectedReviews: ReviewSample[] = [];
  let evidenceItems: ApiEvidence[] = [];
  let reports: ApiReport[] = [];
  let analysisRuns: ApiAnalysisRun[] = [];
  let modelOptions: ModelOption[] = defaultModelOptions;

  let isRefreshing = false;
  let refreshState = '대기 중';
  let refreshJob: ApiJob | null = null;
  let refreshOptions = {
    max_reviews: 25,
    language: 'all',
    review_type: 'all',
    purchase_type: 'all',
    sample_mode: true,
    use_live_steam: false
  };

  let isAnalyzing = false;
  let analysisState = '대기 중';
  let analysisJob: ApiJob | AnalysisRunResult | null = null;
  let analysisOptions = {
    scope: 'new' as 'all' | 'new',
    embedding_model: 'intfloat/multilingual-e5-large',
    min_cluster_size: 20,
    generate_ai_summary: true,
    llm_provider: 'lm_studio'
  };

  let isCreatingEvent = false;
  let eventState = '등록된 이벤트를 선택하세요.';
  let newEvent = {
    title: '',
    event_type: 'patch',
    occurred_at: localDateTimeValue(),
    description: ''
  };

  let isGeneratingReport = false;
  let reportState = '대기 중';
  let refreshRunRows: RunStatusRow[] = [];
  let analysisPipelineRows: RunStatusRow[] = [];
  let libraryQuery = '';
  let libraryFilter: LibraryFilter = 'all';
  let clusterQuery = '';
  let clusterToneFilter: ClusterToneFilter = 'all';
  let showGameDialog = false;
  let showSettingsPanel = false;
  let gameForm = {
    app_id: '',
    name: '',
    short_name: '',
    note: '',
    tags: ''
  };
  let gameFormState = 'Steam App ID와 게임명을 입력하세요.';

  $: clusterSourceText = clusterSourceLabel(clusterSource);
  $: dataSourceText = dataSourceLabel(dataSource);
  $: showInspector = activeTab === 'dashboard' || activeTab === 'report';
  $: latestAnalysisRun = analysisRuns[0] ?? null;
  $: analysisRunSummary = buildAnalysisRunSummary(latestAnalysisRun);
  $: analysisRunRows = buildAnalysisRunRows(analysisRuns);
  $: positiveRatio = Math.round(safeRatio(dashboard.positive_ratio) * 100);
  $: projectReviewCount = formatCount(dashboard.total_reviews);
  $: projectLanguageCount = formatCount(dashboard.languages);
  $: selectedCluster = clusters.find((cluster) => cluster.id === activeCluster) ?? clusters[0] ?? null;
  $: latestReport = reports[0] ?? null;
  $: kpis = buildKpis(dashboard, clusterSourceText);
  $: metrics = buildDataMetrics(dashboard, refreshJob, dataSourceText);
  $: chartRows = buildChartRows(timelineRows, dashboard);
  $: negativeTopics = buildTopicRows('bad');
  $: positiveTopics = buildTopicRows('good');
  $: languageMetrics = buildLanguageMetrics(languages, dataSourceText);
  $: languageRows = buildLanguageRows(languages);
  $: evidenceClaims = buildEvidenceClaims(evidenceItems);
  $: evidenceTableRows = buildEvidenceTableRows(evidenceItems);
  $: reportBlocks = buildReportBlocks(latestReport, dashboard, clusters, evidenceItems);
  $: analysisMetrics = buildAnalysisMetrics(dashboard, clusters, evidenceItems, reports, analysisJob, clusterSourceText);
  $: inspectorRows = buildInspectorRows(dashboard, evidenceItems.length);
  $: priorityItems = buildPriorityItems();
  $: aiBrief = buildAiBrief(latestReport, clusters, dashboard);
  $: selectedGame = gameProjects.find((game) => game.id === selectedGameId) ?? gameProjects[0] ?? sampleGameProjects[0];
  $: selectedAppId = selectedGame?.appId ?? DEFAULT_APP_ID;
  $: libraryMetrics = buildLibraryMetrics(gameProjects);
  $: selectedGameFacts = buildSelectedGameFacts(selectedGame);
  $: selectedGameSteps = buildSelectedGameSteps(selectedGame);
  $: gameComparisonRows = buildGameComparisonRows(gameProjects);
  $: filteredLibraryGames = filterLibraryGames(gameProjects, libraryQuery, libraryFilter);
  $: filteredClusters = filterClusters(clusters, clusterQuery, clusterToneFilter);
  $: clusterMetrics = buildClusterMetrics(clusters, clusterSourceText);
  $: clusterFocusRows = buildClusterFocusRows(clusters);
  $: roleReadinessRows = buildRoleReadinessRows(dashboard, clusters, evidenceItems, languages, analysisRuns, events, reports);
  $: refreshRunRows = [
    {
      icon: DownloadCloud,
      title: 'Steam API 요청',
      detail: refreshOptions.use_live_steam ? 'Live Steam 호출' : '샘플 리뷰 사용',
      state: isRefreshing ? '진행' : '대기',
      tone: isRefreshing ? 'mixed' : 'good'
    },
    {
      icon: Database,
      title: '원본 리뷰 저장',
      detail: refreshJob?.message ?? refreshState,
      state: refreshJob ? statusLabel(refreshJob.status) : '대기',
      tone: refreshJob?.status === 'failed' ? 'bad' : 'mixed'
    },
    {
      icon: Check,
      title: '화면 데이터 재로딩',
      detail: apiMessage,
      state: isLoading ? '진행' : '준비',
      tone: isLoading ? 'mixed' : 'good'
    }
  ];
  $: analysisPipelineRows = [
    {
      icon: Languages,
      title: '언어 정규화',
      detail: `${formatCount(languages.length)}개 언어`,
      state: languages.length ? '준비' : '대기',
      tone: languages.length ? 'good' : 'mixed'
    },
    {
      icon: Network,
      title: '클러스터링',
      detail: `${formatCount(clusters.length)}개 묶음`,
      state: clusterSource === 'backend' ? '준비' : '대기',
      tone: clusterSource === 'backend' ? 'good' : 'mixed'
    },
    {
      icon: ScanSearch,
      title: '근거 연결',
      detail: `${formatCount(evidenceItems.length)}개 근거`,
      state: evidenceItems.length ? '준비' : '대기',
      tone: evidenceItems.length ? 'good' : 'mixed'
    },
    {
      icon: Sparkles,
      title: 'AI 요약',
      detail: reports.length ? latestLabel(reports[0].created_at) : '리포트 없음',
      state: reports.length ? '준비' : '선택',
      tone: reports.length ? 'good' : 'mixed'
    }
  ];

  onMount(async () => {
    await bootstrap();
  });

  async function bootstrap() {
    isLoading = true;
    try {
      await requestJson('/health', undefined, 1800);
      apiState = 'online';
      apiMessage = '백엔드 연결됨';
      await loadApiData();
    } catch {
      useSampleFallback('백엔드 미연결, 샘플 데이터 표시 중');
    } finally {
      isLoading = false;
    }
  }

  async function loadApiData(appIdOverride?: string) {
    isLoading = true;
    const warnings: string[] = [];
    async function get<T>(path: string, label: string): Promise<T | null> {
      try {
        return await requestJson<T>(path);
      } catch {
        warnings.push(label);
        return null;
      }
    }

    const gamesResult = await get<ApiGame[]>('/games', '게임');
    if (Array.isArray(gamesResult) && gamesResult.length > 0) {
      gameProjects = gamesResult.map(mapApiGame);
      if (!gameProjects.some((game) => game.id === selectedGameId)) {
        selectedGameId = gameProjects[0].id;
      }
    } else if (gameProjects.length === 0) {
      gameProjects = sampleGameProjects;
      selectedGameId = sampleGameProjects[0].id;
    }

    const activeAppId =
      appIdOverride ??
      gameProjects.find((game) => game.id === selectedGameId)?.appId ??
      gameProjects[0]?.appId ??
      DEFAULT_APP_ID;
    const appQuery = `app_id=${encodeURIComponent(activeAppId)}`;

    const [
      dashboardResult,
      languagesResult,
      eventsResult,
      timelineResult,
      clustersResult,
      evidenceResult,
      reportsResult,
      analysisRunsResult,
      modelsResult
    ] = await Promise.all([
      get<ApiDashboard>(`/dashboard?${appQuery}`, '대시보드'),
      get<ApiLanguage[]>(`/languages?${appQuery}`, '언어'),
      get<ApiEvent[]>(`/events?${appQuery}`, '이벤트'),
      get<unknown>(`/timeline?${appQuery}&bucket=month`, '타임라인'),
      get<ApiCluster[]>(`/clusters?${appQuery}`, '클러스터'),
      get<ApiEvidence[]>(`/evidence?${appQuery}`, '근거'),
      get<ApiReport[]>(`/reports?${appQuery}`, '리포트'),
      get<ApiAnalysisRun[]>(`/analysis-runs?${appQuery}`, '분석 이력'),
      loadModelOptions(warnings)
    ]);

    dashboard = dashboardResult ?? emptyDashboard;
    languages = Array.isArray(languagesResult) ? languagesResult : [];
    events = Array.isArray(eventsResult) ? eventsResult : [];
    timelineRows = normalizeTimeline(timelineResult);
    evidenceItems = Array.isArray(evidenceResult) ? evidenceResult : [];
    reports = Array.isArray(reportsResult) ? reportsResult : [];
    analysisRuns = Array.isArray(analysisRunsResult) ? analysisRunsResult : [];
    modelOptions = modelsResult;

    if (Array.isArray(clustersResult) && clustersResult.length > 0) {
      clusters = clustersResult.map(mapApiCluster);
      clusterSource = 'backend';
      dataSource = 'api';
      if (!clusters.some((cluster) => cluster.id === activeCluster)) {
        activeCluster = clusters[0].id;
      }
      await loadClusterReviews(activeCluster);
    } else {
      clusters = [];
      selectedReviews = [];
      clusterSource = 'empty';
      dataSource = 'api';
    }

    if (!events.some((event) => String(event.id) === selectedEventId)) {
      selectedEventId = events[0] ? String(events[0].id) : '';
    }
    if (selectedEventId) {
      await loadEventImpact();
    } else {
      eventImpact = null;
      eventImpactState = '등록된 이벤트가 없습니다.';
    }

    endpointWarnings = warnings;
    apiState = warnings.length > 0 ? 'partial' : 'online';
    apiMessage = warnings.length > 0 ? `백엔드 일부 연결 · ${warnings.length}개 항목 대기` : '백엔드 연결됨';
    isLoading = false;
  }

  async function loadModelOptions(warnings: string[]): Promise<ModelOption[]> {
    try {
      const modelPayload = await requestJson<unknown>('/settings/models');
      return normalizeModelOptions(modelPayload, true);
    } catch {
      warnings.push('모델 설정');
      try {
        const settings = await requestJson<ApiSettingValue[]>('/settings');
        return normalizeModelOptions(settings, false);
      } catch {
        return defaultModelOptions;
      }
    }
  }

  function useSampleFallback(message: string) {
    apiState = 'offline';
    apiMessage = message;
    dataSource = 'sample';
    endpointWarnings = ['백엔드 API'];
    gameProjects = sampleGameProjects;
    selectedGameId = sampleGameProjects[0].id;
    dashboard = sampleDashboard;
    timelineRows = sampleTimeline;
    languages = sampleLanguages;
    events = [];
    eventImpact = null;
    eventImpactState = '백엔드 연결 후 이벤트 전후 비교를 사용할 수 있습니다.';
    clusters = sampleClusters;
    clusterSource = 'sample';
    activeCluster = sampleClusters[0].id;
    selectedReviews = sampleClusters[0].samples;
    evidenceItems = sampleClusters.flatMap((cluster, index) =>
      cluster.samples.slice(0, 1).map((sample, sampleIndex) => ({
        id: index * 10 + sampleIndex + 1,
        review_id: `sample-${index}-${sampleIndex}`,
        cluster_id: null,
        quote: sample.text,
        evidence_type: 'sample',
        note: cluster.title,
        created_at: sampleDashboard.latest_review_at ?? new Date().toISOString()
      }))
    );
    reports = [];
    analysisRuns = [];
    modelOptions = defaultModelOptions;
    refreshState = '백엔드 미연결';
    analysisState = '백엔드 미연결';
    reportState = '백엔드 미연결';
    isLoading = false;
  }

  async function refreshSteamReviews(appId = selectedAppId) {
    isRefreshing = true;
    refreshState = '리뷰 갱신 요청 중';
    refreshJob = null;
    try {
      const payload = {
        app_id: appId,
        max_reviews: Number(refreshOptions.max_reviews),
        language: refreshOptions.language,
        review_type: refreshOptions.review_type,
        purchase_type: refreshOptions.purchase_type,
        use_live_steam: refreshOptions.use_live_steam,
        sample_mode: refreshOptions.sample_mode
      };
      const result = await requestJson<RefreshResult>('/refresh-steam', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      refreshJob = result.job ?? null;
      if (refreshJob && !isTerminalJob(refreshJob.status)) {
        refreshState = jobStatusLabel(refreshJob);
        refreshJob = await pollJob(refreshJob.id, (job) => {
          refreshJob = job;
          refreshState = jobStatusLabel(job);
        });
      }
      const inserted = result.inserted_reviews ?? numberFromMetadata(refreshJob, 'inserted');
      const updated = result.updated_reviews ?? numberFromMetadata(refreshJob, 'updated');
      const source = result.source ?? String(refreshJob?.metadata?.source ?? (refreshOptions.use_live_steam ? 'steam' : 'sample'));
      refreshState = `${formatCount(inserted)}개 추가 · ${formatCount(updated)}개 갱신 · ${sourceLabel(source)}`;
      await loadApiData(appId);
    } catch {
      refreshState = '/api/refresh-steam 요청에 실패했습니다.';
      apiState = apiState === 'online' ? 'partial' : apiState;
      apiMessage = '리뷰 갱신 실패';
    } finally {
      isRefreshing = false;
    }
  }

  async function startAnalysisRun(appId = selectedAppId) {
    isAnalyzing = true;
    analysisState = '분석 실행 요청 중';
    analysisJob = null;
    try {
      const result = await requestJson<AnalysisRunResult>('/analysis-runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_id: appId,
          scope: analysisOptions.scope,
          embedding_model: analysisOptions.embedding_model,
          min_cluster_size: Number(analysisOptions.min_cluster_size),
          generate_ai_summary: analysisOptions.generate_ai_summary,
          llm_provider: analysisOptions.llm_provider
        })
      });
      analysisJob = result.job ?? result;
      const jobId = result.job?.id ?? result.job_id ?? (typeof result.id === 'number' ? result.id : null);
      if (jobId) {
        const polled = await pollJob(jobId, (job) => {
          analysisJob = job;
          analysisState = jobStatusLabel(job);
        });
        analysisJob = polled;
        analysisState = jobStatusLabel(polled);
      } else {
        analysisState = result.message ?? statusLabel(result.status ?? 'submitted');
      }
      await loadApiData(appId);
    } catch {
      analysisState = '/api/analysis-runs가 아직 응답하지 않습니다. 현재 화면은 기존 클러스터와 근거를 표시합니다.';
    } finally {
      isAnalyzing = false;
    }
  }

  async function loadClusterReviews(clusterId: ClusterId) {
    activeCluster = clusterId;
    const cluster = clusters.find((item) => item.id === clusterId);
    if (!cluster) {
      selectedReviews = [];
      return;
    }
    if (!cluster.backend) {
      selectedReviews = cluster.samples;
      return;
    }
    selectedReviews = [];
    try {
      const reviews = await requestJson<ApiReview[]>(`/clusters/${clusterId}/reviews?limit=8`);
      selectedReviews = reviews.map(mapApiReview);
      clusters = clusters.map((item) => (item.id === clusterId ? { ...item, samples: selectedReviews } : item));
    } catch {
      selectedReviews = [];
    }
  }

  async function loadEventImpact() {
    if (!selectedEventId) {
      eventImpact = null;
      eventImpactState = '등록된 이벤트가 없습니다.';
      return;
    }
    eventImpactState = '전후 변화 계산 중';
    try {
      const payload = await requestJson<unknown>(
        `/events/${selectedEventId}/impact?window_days=${impactWindowDays}&app_id=${encodeURIComponent(selectedAppId)}`
      );
      eventImpact = normalizeEventImpact(payload);
      eventImpactState = eventImpact ? '전후 비교 결과' : '비교 결과가 없습니다.';
    } catch {
      eventImpact = null;
      eventImpactState = '/api/events/{id}/impact가 아직 준비되지 않았습니다.';
    }
  }

  async function createEvent() {
    if (!newEvent.title.trim()) {
      eventState = '이벤트 이름을 입력하세요.';
      return;
    }
    isCreatingEvent = true;
    eventState = '이벤트 등록 중';
    try {
      const created = await requestJson<ApiEvent>('/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newEvent.title.trim(),
          event_type: newEvent.event_type,
          description: newEvent.description.trim() || null,
          occurred_at: new Date(newEvent.occurred_at).toISOString(),
          app_id: selectedAppId
        })
      });
      newEvent = { title: '', event_type: 'patch', occurred_at: localDateTimeValue(), description: '' };
      eventState = '이벤트가 등록되었습니다.';
      selectedEventId = String(created.id);
      await loadApiData();
    } catch {
      eventState = '/api/events 등록에 실패했습니다.';
    } finally {
      isCreatingEvent = false;
    }
  }

  async function generateReport() {
    isGeneratingReport = true;
    reportState = '리포트 생성 요청 중';
    try {
      const created = await requestJson<ApiReport>('/reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `ReviewForge summary ${new Date().toISOString().slice(0, 10)}`,
          summary: buildGeneratedSummary(dashboard, clusters, evidenceItems),
          filters: {
            app_id: selectedAppId,
            source: dataSource,
            cluster_count: clusters.length,
            evidence_count: evidenceItems.length
          }
        })
      });
      reports = [created, ...reports.filter((report) => report.id !== created.id)];
      reportState = '리포트가 생성되었습니다.';
    } catch {
      reportState = '/api/reports 생성이 지원되지 않아 현재 API 데이터로 미리보기를 표시합니다.';
    } finally {
      isGeneratingReport = false;
    }
  }

  async function requestJson<T>(path: string, init?: RequestInit, timeoutMs = 8000): Promise<T> {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      return (await response.json()) as T;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function pollJob(jobId: number, onUpdate: (job: ApiJob) => void): Promise<ApiJob> {
    let lastJob = await requestJson<ApiJob>(`/jobs/${jobId}`);
    onUpdate(lastJob);
    for (let attempt = 0; attempt < 20 && !isTerminalJob(lastJob.status); attempt += 1) {
      await delay(1000);
      lastJob = await requestJson<ApiJob>(`/jobs/${jobId}`);
      onUpdate(lastJob);
    }
    return lastJob;
  }

  function delay(ms: number) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function setTab(tab: TabId) {
    activeTab = tab;
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  function mapApiGame(game: ApiGame): GameProject {
    const reviewCount = numberFrom(game.review_count);
    const clusterCount = numberFrom(game.cluster_count);
    const statusKey = String(game.status ?? '').toLowerCase();
    const nextAction = (game.next_action as GameProject['nextAction']) ?? inferNextAction(reviewCount, clusterCount);
    const status = game.status ? gameStatusLabel(game.status) : gameStatusFromAction(nextAction);
    return {
      id: game.app_id,
      name: game.name || `Steam app/${game.app_id}`,
      appId: game.app_id,
      shortName: game.short_name || shortNameFor(game.name || game.app_id),
      status,
      statusTone: statusToneFor(statusKey, nextAction),
      reviewCount,
      languages: numberFrom(game.language_count),
      positiveRatio: ratioMaybe(game.positive_ratio) ?? 0,
      clusters: clusterCount,
      evidenceItems: numberFrom(game.evidence_count),
      lastSync: game.last_sync_at ?? game.last_refreshed_at ?? game.latest_review_at ?? null,
      lastAnalysis: game.last_analysis_at ?? null,
      queue: nextActionLabel(nextAction),
      note: game.note || `${game.name || game.app_id}의 Steam 리뷰를 게임별로 분리해 관리합니다.`,
      tags: Array.isArray(game.tags) && game.tags.length ? game.tags : defaultGameTags(nextAction),
      nextAction
    };
  }

  function filterLibraryGames(projects: GameProject[], queryValue: string, filterValue: string) {
    const q = queryValue.trim().toLowerCase();
    return projects.filter((game) => {
      const text = `${game.name} ${game.appId} ${game.status} ${game.tags.join(' ')}`.toLowerCase();
      const statusMatch =
        filterValue === 'all' ||
        (filterValue === 'ready' && game.nextAction === 'open') ||
        (filterValue === 'needs-analysis' && game.nextAction === 'analyze') ||
        (filterValue === 'needs-sync' && game.nextAction === 'sync') ||
        (filterValue === 'watch' && game.status.includes('관찰'));
      return statusMatch && (!q || text.includes(q));
    });
  }

  function filterClusters(clusterItems: ClusterView[], queryValue: string, toneFilter: ClusterToneFilter) {
    const q = queryValue.trim().toLowerCase();
    return clusterItems
      .filter((cluster) => {
        const text = `${cluster.title} ${cluster.description} ${cluster.tags.join(' ')}`.toLowerCase();
        const toneMatch = toneFilter === 'all' || cluster.tone === toneFilter;
        return toneMatch && (!q || text.includes(q));
      })
      .sort((a, b) => clusterPriorityScore(b) - clusterPriorityScore(a));
  }

  function clusterPriorityScore(cluster: ClusterView) {
    const toneWeight = cluster.tone === 'bad' ? 3 : cluster.tone === 'mixed' ? 2 : 1;
    return toneWeight * 1_000_000 + cluster.countValue;
  }

  async function runGameAction(game: GameProject) {
    selectedGameId = game.id;
    if (game.nextAction === 'sync') {
      await refreshSteamReviews(game.appId);
      return;
    }
    if (game.nextAction === 'analyze') {
      await startAnalysisRun(game.appId);
      return;
    }
    await loadApiData(game.appId);
    setTab('dashboard');
  }

  async function openGame(game: GameProject) {
    selectedGameId = game.id;
    await loadApiData(game.appId);
    setTab('dashboard');
  }

  async function createGame() {
    const appId = gameForm.app_id.trim();
    const name = gameForm.name.trim();
    if (!appId || !name) {
      gameFormState = 'Steam App ID와 게임명을 모두 입력하세요.';
      return;
    }
    gameFormState = '게임 저장 중';
    try {
      const created = await requestJson<ApiGame>('/games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_id: appId,
          name,
          short_name: gameForm.short_name.trim() || null,
          note: gameForm.note.trim() || null,
          tags: gameForm.tags
            .split(',')
            .map((tag) => tag.trim())
            .filter(Boolean)
        })
      });
      const mapped = mapApiGame(created);
      selectedGameId = mapped.id;
      resetGameForm();
      showGameDialog = false;
      await loadApiData(mapped.appId);
      activeTab = 'library';
    } catch {
      gameFormState = '/api/games 저장에 실패했습니다. App ID가 이미 등록됐는지 확인하세요.';
    }
  }

  function resetGameForm() {
    gameForm = { app_id: '', name: '', short_name: '', note: '', tags: '' };
    gameFormState = 'Steam App ID와 게임명을 입력하세요.';
  }

  function inferNextAction(reviewCount: number, clusterCount: number): GameProject['nextAction'] {
    if (reviewCount <= 0) return 'sync';
    if (clusterCount <= 0) return 'analyze';
    return 'open';
  }

  function gameStatusFromAction(action: GameProject['nextAction']) {
    if (action === 'sync') return '수집 필요';
    if (action === 'analyze') return '분석 대기';
    return '분석 완료';
  }

  function gameStatusLabel(value: string) {
    const normalized = value.toLowerCase();
    if (['ready', 'analyzed', 'complete', 'completed'].includes(normalized)) return '분석 완료';
    if (['needs_sync', 'sync', 'new'].includes(normalized)) return '수집 필요';
    if (['needs_analysis', 'collected'].includes(normalized)) return '분석 대기';
    if (['running', 'queued'].includes(normalized)) return '작업 중';
    if (['watch'].includes(normalized)) return '관찰 대상';
    return value;
  }

  function statusToneFor(statusKey: string, action: GameProject['nextAction']): Tone {
    if (statusKey.includes('watch') || statusKey.includes('running') || action === 'analyze') return 'mixed';
    if (action === 'sync') return 'bad';
    return 'good';
  }

  function nextActionLabel(action: GameProject['nextAction']) {
    if (action === 'sync') return 'Steam 리뷰를 먼저 수집하세요.';
    if (action === 'analyze') return '수집된 리뷰를 클러스터링하세요.';
    return '대시보드에서 최신 반응을 검토하세요.';
  }

  function actionButtonLabel(action: GameProject['nextAction']) {
    if (action === 'sync') return '리뷰 수집';
    if (action === 'analyze') return '분석 실행';
    return '열기';
  }

  function defaultGameTags(action: GameProject['nextAction']) {
    if (action === 'sync') return ['신규', '수집 필요'];
    if (action === 'analyze') return ['분석 대기'];
    return ['분석 완료'];
  }

  function shortNameFor(value: string) {
    const compact = value
      .split(/[\s:_-]+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join('')
      .slice(0, 3)
      .toUpperCase();
    return compact || value.slice(0, 3).toUpperCase();
  }

  function mapApiCluster(cluster: ApiCluster): ClusterView {
    const tone = sentimentTone(cluster.sentiment);
    return {
      id: String(cluster.id),
      title: cluster.label || `Cluster ${cluster.id}`,
      count: formatCount(cluster.review_count),
      countValue: cluster.review_count,
      tone,
      description: cluster.summary || '아직 요약이 없습니다.',
      tags: [
        cluster.language ? steamLanguageLabel(cluster.language) : '전체 언어',
        sentimentLabel(cluster.sentiment),
        `대표도 ${formatPercent(cluster.avg_weighted_score)}`
      ],
      backend: true,
      samples: []
    };
  }

  function mapApiReview(review: ApiReview): ReviewSample {
    return {
      language: steamLanguageLabel(review.language),
      playtime: formatPlaytime(review.playtime_at_review),
      reaction: review.voted_up ? '추천' : '비추천',
      reactionTone: review.voted_up ? 'good' : 'bad',
      text: review.review,
      score: formatPercent(review.cluster_score ?? review.weighted_vote_score)
    };
  }

  function normalizeTimeline(payload: unknown): TimelineBucket[] {
    const rows = arrayFromPayload(payload, ['items', 'buckets', 'timeline', 'rows', 'data']);
    return rows
      .map((row, index) => {
        const item = objectFromUnknown(row);
        const positive = ratioValue(item.positive_ratio ?? item.positive_rate ?? item.recommended_ratio);
        const negative = ratioValue(item.negative_ratio ?? item.negative_rate ?? item.not_recommended_ratio);
        const mixed = ratioValue(item.mixed_ratio ?? item.neutral_ratio ?? Math.max(0, 1 - positive - negative));
        const bucket = String(item.bucket ?? item.month ?? item.date ?? item.period ?? `bucket-${index + 1}`);
        return {
          label: String(item.label ?? item.title ?? monthLabel(bucket)),
          bucket,
          positive_ratio: positive,
          negative_ratio: negative,
          mixed_ratio: mixed,
          review_count: numberFrom(item.review_count ?? item.count ?? item.total_reviews)
        };
      })
      .filter((row) => row.review_count > 0 || row.positive_ratio > 0 || row.negative_ratio > 0);
  }

  function normalizeEventImpact(payload: unknown): EventImpactView | null {
    const item = objectFromUnknown(payload);
    if (Object.keys(item).length === 0) return null;
    const before = objectFromUnknown(item.before);
    const after = objectFromUnknown(item.after);
    const beforeCount = numberFrom(item.before_count ?? before.review_count ?? before.count);
    const afterCount = numberFrom(item.after_count ?? after.review_count ?? after.count);
    const beforePositive = ratioMaybe(item.before_positive_ratio ?? before.positive_ratio ?? before.positive_rate);
    const afterPositive = ratioMaybe(item.after_positive_ratio ?? after.positive_ratio ?? after.positive_rate);
    const delta =
      ratioMaybe(item.positive_ratio_delta ?? item.delta_positive_ratio ?? item.delta) ??
      (beforePositive !== null && afterPositive !== null ? afterPositive - beforePositive : null);
    const topicRows = arrayFromPayload(item.topics ?? item.changes ?? item.deltas, ['items', 'rows']).slice(0, 5);
    return {
      beforeCount,
      afterCount,
      beforePositiveRatio: beforePositive,
      afterPositiveRatio: afterPositive,
      deltaPoints: delta,
      notes: [
        String(item.summary ?? item.note ?? '같은 기간에 함께 움직인 리뷰 신호만 표시합니다.'),
        beforeCount || afterCount ? `표본: 전 ${formatCount(beforeCount)}개, 후 ${formatCount(afterCount)}개` : ''
      ].filter(Boolean),
      topics: topicRows.map((topic) => {
        const row = objectFromUnknown(topic);
        const label = String(row.label ?? row.topic ?? row.term ?? row.name ?? '변화 항목');
        const detail = String(row.detail ?? row.description ?? row.summary ?? '전후 기간의 언급 변화를 비교했습니다.');
        const deltaLabel = deltaLabelFrom(row.delta ?? row.change ?? row.delta_points);
        return [label, detail, deltaLabel, deltaLabel.startsWith('-') ? 'down' : 'up'];
      })
    };
  }

  function normalizeModelOptions(payload: unknown, fromModelsEndpoint: boolean): ModelOption[] {
    const rows = Array.isArray(payload)
      ? payload
      : arrayFromPayload(payload, ['providers', 'models', 'items', 'data', 'settings']);
    const settings = Array.isArray(payload) ? (payload as unknown[]) : rows;
    const lowered = JSON.stringify(payload ?? {}).toLowerCase();
    const lmStudioKnown = lowered.includes('lm') || lowered.includes('studio') || fromModelsEndpoint;
    const lmStudioConnected =
      lowered.includes('"connected":true') ||
      lowered.includes('"available":true') ||
      lowered.includes('"status":"connected"') ||
      lowered.includes('"status":"ok"');

    const dynamic: ModelOption[] = [];
    for (const rawRow of rows) {
      const row = objectFromUnknown(rawRow);
      const name = String(row.name ?? row.provider ?? row.key ?? '');
      if (!name) continue;
      const connected = row.connected === true || row.available === true || String(row.status ?? '').toLowerCase() === 'connected';
      dynamic.push({
        icon: name.toLowerCase().includes('lm') ? Server : name.toLowerCase().includes('openai') ? CloudCog : Cloud,
        name,
        detail: String(row.detail ?? row.base_url ?? row.model ?? row.value ?? '모델 설정에서 전달된 공급자입니다.'),
        state: connected ? '연결됨' : String(row.status ?? '상태 미확인'),
        tone: connected ? 'good' : 'mixed'
      });
    }

    const lmStudio: ModelOption = {
      icon: Server,
      name: 'LM Studio',
      detail: fromModelsEndpoint ? '/api/settings/models에서 확인' : '/api/settings fallback에서 확인',
      state: lmStudioConnected ? '연결됨' : lmStudioKnown ? '상태 확인 필요' : '상태 미확인',
      tone: lmStudioConnected ? 'good' : 'mixed'
    };

    const merged = [lmStudio, ...dynamic.filter((item) => item.name.toLowerCase() !== 'lm studio')];
    return merged.length > 0 ? merged : defaultModelOptions;
  }

  function buildKpis(summary: ApiDashboard, sourceLabel: string): string[][] {
    return [
      ['수집 리뷰', formatCount(summary.total_reviews), latestLabel(summary.latest_review_at)],
      ['추천 리뷰', formatCount(summary.positive_reviews), `${formatPercent(summary.positive_ratio)} 추천`],
      ['대표 클러스터', formatCount(summary.clusters), sourceLabel],
      ['근거 리뷰', formatCount(summary.evidence_items), summary.evidence_items ? 'API 근거 표시' : '근거 대기']
    ];
  }

  function buildLibraryMetrics(projects: GameProject[]): string[][] {
    const reviewTotal = projects.reduce((total, game) => total + game.reviewCount, 0);
    const analyzed = projects.filter((game) => game.lastAnalysis).length;
    const waiting = projects.filter((game) => !game.lastAnalysis).length;
    const latest = projects
      .map((game) => game.lastSync)
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1);
    return [
      ['관리 게임', formatCount(projects.length), '로컬 라이브러리'],
      ['저장 리뷰', formatCount(reviewTotal), '게임별 app_id 기준'],
      ['분석 완료', formatCount(analyzed), `${formatCount(waiting)}개 대기`],
      ['최근 수집', latestLabel(latest ?? null), 'Steam 리뷰 기준']
    ];
  }

  function buildSelectedGameFacts(game: GameProject): string[][] {
    return [
      ['Steam App ID', game.appId, '수집 키'],
      ['리뷰 수', formatCount(game.reviewCount), game.lastSync ? latestLabel(game.lastSync) : '수집 전'],
      ['추천율', formatPercent(game.positiveRatio), `${formatCount(game.languages)}개 언어`],
      ['분석 상태', game.status, game.lastAnalysis ? latestLabel(game.lastAnalysis) : '분석 전']
    ];
  }

  function buildSelectedGameSteps(game: GameProject): string[][] {
    return [
      ['1', '게임 등록', `Steam app/${game.appId} · ${game.name}`, 'good'],
      ['2', '리뷰 수집', game.lastSync ? latestLabel(game.lastSync) : '아직 수집하지 않음', game.lastSync ? 'good' : 'mixed'],
      ['3', '분석 실행', game.lastAnalysis ? latestLabel(game.lastAnalysis) : '클러스터링 대기', game.lastAnalysis ? 'good' : 'mixed'],
      ['4', '기획 큐', game.queue, game.statusTone]
    ];
  }

  function buildGameComparisonRows(projects: GameProject[]): string[][] {
    return projects.map((game) => [
      `${game.name} · app/${game.appId}`,
      formatCount(game.reviewCount),
      game.reviewCount ? formatPercent(game.positiveRatio) : '수집 전',
      game.status
    ]);
  }

  function buildClusterMetrics(clusterItems: ClusterView[], sourceLabel: string): string[][] {
    const risky = clusterItems.filter((cluster) => cluster.tone !== 'good');
    const largestRisk = [...risky].sort((a, b) => b.countValue - a.countValue)[0];
    const largest = [...clusterItems].sort((a, b) => b.countValue - a.countValue)[0];
    return [
      ['전체 묶음', formatCount(clusterItems.length), sourceLabel],
      ['먼저 볼 묶음', formatCount(risky.length), '불만/혼합 기준'],
      ['최대 불만', largestRisk ? largestRisk.title : '없음', largestRisk ? `${largestRisk.count}개` : '현재 없음'],
      ['최대 묶음', largest ? largest.title : '없음', largest ? `${largest.count}개` : '분석 대기']
    ];
  }

  function buildClusterFocusRows(clusterItems: ClusterView[]): string[][] {
    const rows = clusterItems
      .filter((cluster) => cluster.tone !== 'good')
      .sort((a, b) => clusterPriorityScore(b) - clusterPriorityScore(a))
      .slice(0, 4)
      .map((cluster) => [
        cluster.title,
        `${cluster.count}개 리뷰 · ${cluster.tags.slice(0, 2).join(' · ')}`,
        cluster.tone === 'bad' ? '우선' : '관찰',
        cluster.tone
      ]);
    return rows.length ? rows : [['불만 신호 부족', '현재 분석에서는 호평 클러스터가 대부분입니다. 비추천 필터로 재수집하거나 기간을 좁혀 보세요.', '관찰', 'mixed']];
  }

  function buildRoleReadinessRows(
    summary: ApiDashboard,
    clusterItems: ClusterView[],
    evidence: ApiEvidence[],
    languageItems: ApiLanguage[],
    runs: ApiAnalysisRun[],
    eventItems: ApiEvent[],
    reportItems: ApiReport[]
  ): string[][] {
    const latestRun = runs[0] ?? null;
    const riskyClusters = clusterItems.filter((cluster) => cluster.tone !== 'good').length;
    return [
      [
        '데이터 사이언티스트',
        `${formatCount(summary.total_reviews)}개 리뷰, ${formatCount(languageItems.length || summary.languages)}개 언어, ${latestRun ? analysisMethodLabel(latestRun) : '분석 이력 없음'}`,
        summary.total_reviews >= 1000 && latestRun ? '사용 가능' : '보강',
        summary.total_reviews >= 1000 && latestRun ? 'good' : 'mixed'
      ],
      [
        '기획자',
        `${formatCount(riskyClusters)}개 불만/혼합 묶음과 ${formatCount(evidence.length)}개 원문 근거로 우선순위를 볼 수 있습니다.`,
        riskyClusters && evidence.length ? '사용 가능' : '보강',
        riskyClusters && evidence.length ? 'good' : 'mixed'
      ],
      [
        '마케터',
        `${formatCount(reportItems.length)}개 리포트와 언어권 강점은 있지만, 바로 쓸 캠페인 문구/인용문 선별은 아직 수동 확인이 필요합니다.`,
        reportItems.length ? '부분 가능' : '보강',
        reportItems.length ? 'mixed' : 'bad'
      ],
      [
        '운영/PM',
        `${formatCount(eventItems.length)}개 이벤트 기준이 저장되어 있습니다. 패치/세일 날짜가 있어야 전후 반응을 읽을 수 있습니다.`,
        eventItems.length ? '사용 가능' : '보강',
        eventItems.length ? 'good' : 'mixed'
      ]
    ];
  }

  function buildAnalysisRunRows(runs: ApiAnalysisRun[]): string[][] {
    return runs.slice(0, 5).map((run) => [
      `#${run.id}`,
      statusLabel(run.status),
      analysisMethodLabel(run),
      run.finished_at ? formatDateTime(run.finished_at) : latestLabel(run.started_at)
    ]);
  }

  function buildAnalysisRunSummary(run: ApiAnalysisRun | null) {
    if (!run) return '분석 이력이 아직 없습니다. 리뷰 수집 후 분석 실행을 시작하세요.';
    const params = run.params ?? {};
    const model = String(params.embedding_model ?? analysisOptions.embedding_model ?? '기본 임베딩');
    const scope = String(params.scope ?? 'all') === 'new' ? '새 리뷰' : '전체 리뷰';
    return `${statusLabel(run.status)} · ${scope} · ${model} · ${formatDateTime(run.finished_at ?? run.started_at)}`;
  }

  function analysisMethodLabel(run: ApiAnalysisRun) {
    const params = run.params ?? {};
    const model = String(params.embedding_model ?? '기본 임베딩');
    const minSize = numberFrom(params.min_cluster_size);
    return `${model}${minSize ? ` · 최소 ${formatCount(minSize)}개` : ''}`;
  }

  function buildDataMetrics(summary: ApiDashboard, job: ApiJob | null, sourceLabel: string): string[][] {
    return [
      ['마지막 갱신', latestLabel(summary.latest_review_at), `Steam app/${selectedAppId}`],
      ['원본 리뷰', formatCount(summary.total_reviews), sourceLabel],
      ['최근 작업', job ? statusLabel(job.status) : '없음', job?.message ?? refreshState],
      ['수집 모드', refreshOptions.use_live_steam ? 'Live Steam' : 'Sample', refreshOptions.sample_mode ? '샘플 허용' : '샘플 끔']
    ];
  }

  function buildAnalysisMetrics(
    summary: ApiDashboard,
    clusterItems: ClusterView[],
    evidence: ApiEvidence[],
    reportItems: ApiReport[],
    job: ApiJob | AnalysisRunResult | null,
    sourceLabel: string
  ): string[][] {
    const status = job && 'status' in job && job.status ? statusLabel(job.status) : analysisState;
    const progress = job && 'progress' in job && typeof job.progress === 'number' ? formatPercent(job.progress) : '대기';
    return [
      ['분석 대상', formatCount(summary.total_reviews), analysisOptions.scope === 'all' ? '전체 리뷰' : '새 리뷰'],
      ['클러스터', formatCount(clusterItems.length), sourceLabel],
      ['근거', formatCount(evidence.length), '리포트 검증용'],
      ['작업 상태', progress, status || '대기 중']
    ];
  }

  function buildChartRows(rows: TimelineBucket[], summary: ApiDashboard) {
    const sourceRows = rows.length > 0 ? rows : dataSource === 'sample' ? sampleTimeline : [];
    if (sourceRows.length === 0 && summary.total_reviews > 0) {
      const positive = safeRatio(summary.positive_ratio);
      const negative = safeRatio(1 - positive);
      return [
        {
          label: '전체 기간',
          bucket: latestLabel(summary.latest_review_at),
          score: formatPercent(positive),
          pos: Math.round(positive * 100),
          neg: Math.round(negative * 100),
          neu: 0
        }
      ];
    }
    return sourceRows.map((row) => ({
      label: row.label,
      bucket: row.bucket,
      score: formatPercent(row.positive_ratio),
      pos: Math.max(0, Math.round(safeRatio(row.positive_ratio) * 100)),
      neg: Math.max(0, Math.round(safeRatio(row.negative_ratio) * 100)),
      neu: Math.max(0, Math.round(safeRatio(row.mixed_ratio) * 100))
    }));
  }

  function buildTopicRows(tone: Tone): string[][] {
    const rows = clusters
      .filter((cluster) => cluster.tone === tone)
      .sort((a, b) => b.countValue - a.countValue)
      .slice(0, 4)
      .map((cluster) => [
        cluster.title,
        `${cluster.count}개 리뷰 · ${cluster.tags[0] ?? '전체'}`,
        tone === 'bad' ? '검토' : '강점',
        tone === 'bad' ? 'up' : 'down'
      ]);
    if (rows.length > 0) return rows;
    return [['데이터 대기', '클러스터 API 결과가 들어오면 표시됩니다.', '대기', 'flat']];
  }

  function buildLanguageMetrics(languageItems: ApiLanguage[], sourceLabel: string): string[][] {
    const enough = languageItems.filter((item) => item.review_count >= 1000).length;
    const top = languageItems[0];
    const weakest = [...languageItems].sort((a, b) => a.positive_ratio - b.positive_ratio)[0];
    return [
      ['언어 수', formatCount(languageItems.length || dashboard.languages), sourceLabel],
      ['최대 표본', top ? steamLanguageLabel(top.language) : '없음', top ? `${formatCount(top.review_count)}개` : '언어 API 대기'],
      ['검토 언어', weakest ? steamLanguageLabel(weakest.language) : '없음', weakest ? `${formatPercent(weakest.positive_ratio)} 추천` : '데이터 없음'],
      ['표본 충분', `${formatCount(enough)}개`, '1,000개 이상 기준']
    ];
  }

  function buildLanguageRows(languageItems: ApiLanguage[]): string[][] {
    return languageItems.slice(0, 12).map((item) => [
      steamLanguageLabel(item.language),
      `${formatPercent(item.positive_ratio)} · n=${formatCount(item.review_count)}`,
      `비추천 ${formatCount(item.negative_count)}`,
      `가중 ${formatPercent(item.avg_weighted_score)}`
    ]);
  }

  function buildEvidenceClaims(items: ApiEvidence[]): string[][] {
    const rows = items.slice(0, 4).map((item) => [
      evidenceClaimTitle(item),
      item.quote,
      evidenceTypeLabel(item.evidence_type),
      item.evidence_type === 'ai' ? 'ai' : 'numeric'
    ]);
    if (rows.length > 0) return rows;
    return [['근거 데이터 대기', '/api/evidence 응답이 들어오면 주장과 원문 연결을 표시합니다.', '대기', 'numeric']];
  }

  function buildEvidenceTableRows(items: ApiEvidence[]): string[][] {
    return items.slice(0, 8).map((item) => [
      evidenceTypeLabel(item.evidence_type),
      trimText(item.quote, 88),
      item.cluster_id ? clusterTitle(item.cluster_id) : '미연결',
      formatDate(item.created_at)
    ]);
  }

  function buildReportBlocks(
    report: ApiReport | null,
    summary: ApiDashboard,
    clusterItems: ClusterView[],
    evidence: ApiEvidence[]
  ): string[][] {
    if (report) {
      return [
        ['최근 리포트', report.summary],
        ['생성 시각', `${formatDateTime(report.created_at)} · ${report.title}`],
        ['필터', Object.keys(report.filters ?? {}).length ? JSON.stringify(report.filters) : '필터 없음']
      ];
    }
    const topBad = clusterItems.find((cluster) => cluster.tone === 'bad');
    const topGood = clusterItems.find((cluster) => cluster.tone === 'good');
    return [
      ['요약', buildGeneratedSummary(summary, clusterItems, evidence)],
      ['호평', topGood ? `${topGood.title}: ${topGood.description}` : '추천 연결 클러스터가 아직 없습니다.'],
      ['불만', topBad ? `${topBad.title}: ${topBad.description}` : '비추천 연결 클러스터가 아직 없습니다.'],
      ['다음 액션', evidence.length ? '근거 문장을 확인한 뒤 리포트 문구를 확정하세요.' : '클러스터와 근거 API가 준비되면 액션 항목을 구체화합니다.']
    ];
  }

  function buildGeneratedSummary(summary: ApiDashboard, clusterItems: ClusterView[], evidence: ApiEvidence[]) {
    const topBad = clusterItems.find((cluster) => cluster.tone === 'bad');
    const topGood = clusterItems.find((cluster) => cluster.tone === 'good');
    const conflictText =
      topGood && topBad && topGood.title === topBad.title
        ? `강점과 검토 신호가 모두 "${topGood.title}"에 모여 있어 세부 원문 확인이 필요합니다. `
        : `${topGood ? `강점 신호는 "${topGood.title}"이고, ` : ''}${
            topBad ? `검토 신호는 "${topBad.title}"입니다. ` : '검토 클러스터는 아직 충분하지 않습니다. '
          }`;
    return `현재 ${formatCount(summary.total_reviews)}개 리뷰 기준 추천율은 ${formatPercent(summary.positive_ratio)}입니다. ${
      conflictText
    }${evidence.length ? `근거 ${formatCount(evidence.length)}개가 연결되어 있습니다.` : '근거 API 데이터는 아직 없습니다.'}`;
  }

  function buildInspectorRows(summary: ApiDashboard, evidenceCount: number): string[][] {
    return [
      ['데이터 최신성', latestLabel(summary.latest_review_at), summary.latest_review_at ? '확인' : '대기', summary.latest_review_at ? 'good' : 'mixed'],
      ['표본 크기', `${formatCount(summary.total_reviews)}개 리뷰`, summary.total_reviews > 0 ? '사용 가능' : '대기', summary.total_reviews > 0 ? 'good' : 'mixed'],
      ['근거 검증', `${formatCount(evidenceCount)}개 근거`, evidenceCount ? '진행' : '대기', evidenceCount ? 'good' : 'mixed']
    ];
  }

  function buildPriorityItems(): string[][] {
    const rows = clusters
      .filter((cluster) => cluster.tone !== 'good')
      .slice(0, 3)
      .map((cluster, index) => [
        String(index + 1),
        cluster.title,
        `${cluster.count}개 · ${cluster.tags[0] ?? '전체'}`,
        cluster.tone === 'bad' ? '높음' : '중간',
        cluster.tone
      ]);
    return rows.length
      ? rows
      : [['1', '클러스터 대기', '분석 실행 후 표시', '대기', 'mixed']];
  }

  function buildAiBrief(report: ApiReport | null, clusterItems: ClusterView[], summary: ApiDashboard) {
    if (report) return [report.summary];
    const topBad = clusterItems.find((cluster) => cluster.tone === 'bad');
    const topGood = clusterItems.find((cluster) => cluster.tone === 'good');
    return [
      `${formatCount(summary.total_reviews)}개 리뷰 기준 추천율은 ${formatPercent(summary.positive_ratio)}입니다.`,
      topBad
        ? `가장 먼저 볼 불만 신호는 "${topBad.title}"입니다. 인과가 아니라 같은 기간에 관측된 리뷰 신호로만 다룹니다.`
        : topGood
          ? `현재 가장 큰 긍정 신호는 "${topGood.title}"입니다.`
          : '클러스터 API가 준비되면 AI 브리프가 더 구체화됩니다.'
    ];
  }

  function clusterTitle(clusterId: number | null) {
    if (clusterId === null) return '';
    return clusters.find((cluster) => cluster.id === String(clusterId))?.title ?? `Cluster ${clusterId}`;
  }

  function clusterSourceLabel(source: typeof clusterSource) {
    if (source === 'backend') return '백엔드 클러스터';
    if (source === 'sample') return '샘플 클러스터';
    return '클러스터 없음';
  }

  function dataSourceLabel(source: typeof dataSource) {
    if (source === 'api') return '백엔드 API';
    if (source === 'sample') return '샘플 표시';
    return '데이터 대기';
  }

  function sourceLabel(source: string) {
    if (source === 'steam') return 'Steam live';
    if (source === 'stub' || source === 'sample') return '샘플';
    return source;
  }

  function sentimentTone(value: string): Tone {
    const normalized = value.toLowerCase();
    if (normalized.includes('positive') || normalized.includes('good')) return 'good';
    if (normalized.includes('negative') || normalized.includes('bad')) return 'bad';
    return 'mixed';
  }

  function sentimentLabel(value: string) {
    const tone = sentimentTone(value);
    if (tone === 'good') return '추천 연결 높음';
    if (tone === 'bad') return '비추천 연결 높음';
    return '혼합 반응';
  }

  function evidenceTypeLabel(value: string) {
    if (value === 'placeholder') return '자동 근거';
    if (value === 'sample') return '샘플';
    if (value === 'ai') return 'AI 해석';
    if (value === 'praise') return '호평 근거';
    if (value === 'complaint') return '불만 근거';
    if (value === 'mixed') return '혼합 근거';
    return value || '근거';
  }

  function evidenceClaimTitle(item: ApiEvidence) {
    const cluster = clusterTitle(item.cluster_id);
    if (!item.note) return cluster || '근거 문장';
    if (item.note.toLowerCase().startsWith('representative review score')) return cluster || '대표 리뷰';
    return item.note;
  }

  function statusLabel(value: string) {
    const normalized = value.toLowerCase();
    if (['succeeded', 'success', 'completed', 'complete'].includes(normalized)) return '완료';
    if (['failed', 'error'].includes(normalized)) return '실패';
    if (['running', 'queued', 'pending', 'submitted'].includes(normalized)) return '진행';
    return value || '대기';
  }

  function jobStatusLabel(job: ApiJob) {
    const percent = formatPercent(job.progress ?? 0);
    return `${statusLabel(job.status)} · ${percent}${job.message ? ` · ${job.message}` : ''}`;
  }

  function isTerminalJob(status: string) {
    return ['succeeded', 'success', 'completed', 'complete', 'failed', 'error', 'cancelled', 'canceled'].includes(
      status.toLowerCase()
    );
  }

  function numberFromMetadata(job: ApiJob | null, key: string) {
    return numberFrom(job?.metadata?.[key]);
  }

  function steamLanguageLabel(value: string) {
    const labels: Record<string, string> = {
      all: '전체',
      english: 'EN',
      koreana: 'KO',
      schinese: 'ZH',
      tchinese: 'ZH-TW',
      japanese: 'JA',
      spanish: 'ES',
      french: 'FR',
      german: 'DE',
      russian: 'RU',
      brazilian: 'PT-BR'
    };
    return labels[value] ?? value.toUpperCase();
  }

  function formatCount(value: number) {
    return new Intl.NumberFormat('ko-KR').format(Math.max(0, Math.round(numberFrom(value))));
  }

  function formatPercent(value: number) {
    return `${Math.round(safeRatio(value) * 100)}%`;
  }

  function formatPlaytime(minutes: number) {
    if (!minutes) return '미상';
    return `${(minutes / 60).toFixed(1)}h`;
  }

  function latestLabel(value: string | null) {
    if (!value) return '수집 기록 없음';
    return new Intl.DateTimeFormat('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
  }

  function formatDate(value: string | null) {
    if (!value) return '날짜 없음';
    return new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' }).format(new Date(value));
  }

  function formatDateTime(value: string | null) {
    if (!value) return '날짜 없음';
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(value));
  }

  function monthLabel(value: string) {
    if (/^\d{4}-\d{2}/.test(value)) {
      const [year, month] = value.split('-');
      return `${year}.${month}`;
    }
    return value;
  }

  function localDateTimeValue(date = new Date()) {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 16);
  }

  function safeRatio(value: number) {
    if (!Number.isFinite(value)) return 0;
    return value > 1 ? value / 100 : Math.max(0, Math.min(1, value));
  }

  function ratioValue(value: unknown) {
    return safeRatio(numberFrom(value));
  }

  function ratioMaybe(value: unknown) {
    if (value === null || value === undefined || value === '') return null;
    return ratioValue(value);
  }

  function numberFrom(value: unknown) {
    if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
    if (typeof value === 'string') {
      const parsed = Number(value.replace('%', ''));
      return Number.isFinite(parsed) ? parsed : 0;
    }
    return 0;
  }

  function objectFromUnknown(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
  }

  function arrayFromPayload(payload: unknown, keys: string[] = []): unknown[] {
    if (Array.isArray(payload)) return payload;
    const object = objectFromUnknown(payload);
    for (const key of keys) {
      const value = object[key];
      if (Array.isArray(value)) return value;
    }
    return [];
  }

  function deltaLabelFrom(value: unknown) {
    const numeric = numberFrom(value);
    if (!numeric) return '변화';
    const points = Math.abs(numeric) <= 1 ? numeric * 100 : numeric;
    return `${points > 0 ? '+' : ''}${Math.round(points)}%p`;
  }

  function trimText(value: string, maxLength: number) {
    return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
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
        <dd>{selectedGame.name}</dd>
        <dt>App ID</dt>
        <dd>{selectedGame.appId}</dd>
        <dt>리뷰</dt>
        <dd>{formatCount(selectedGame.reviewCount)}</dd>
      </dl>
    </div>
  </aside>

  <div class="workspace">
    <header class="topbar">
      <label class="searchbar">
        <Search />
        <input value={`${selectedGame.name} · app/${selectedGame.appId}`} aria-label="Steam 게임 검색" readonly />
      </label>
      <div class="actions">
        <span class="status" class:offline={apiState !== 'online'}>{apiMessage}</span>
        <button class="icon-button" title="설정" type="button" on:click={() => (showSettingsPanel = true)}><Settings2 /></button>
        <button class="ghost-button" title="Steam에서 최신 리뷰를 가져와 로컬 분석 데이터를 갱신" type="button" disabled={isRefreshing} on:click={() => refreshSteamReviews()}>
          <Database /><span>{isRefreshing ? '갱신 중' : '리뷰 갱신'}</span>
        </button>
        <button class="primary-button" type="button" on:click={() => setTab('report')}><Sparkles /><span>AI 리포트</span></button>
      </div>
    </header>

    <div class="content" class:library-content={activeTab === 'library'} class:wide-content={!showInspector}>
      <main class="main">
        <section class:active={activeTab === 'library'} class="tab-view" aria-label="게임 라이브러리">
          <PageIntro title="게임 라이브러리" subtitle="여러 Steam 게임을 프로젝트처럼 저장하고, 수집·분석·리포트 상태를 한 화면에서 관리합니다.">
            <div class="actions">
              <button class="ghost-button" type="button" on:click={() => (showSettingsPanel = true)}><Settings2 /><span>설정</span></button>
              <button class="primary-button" type="button" on:click={() => (showGameDialog = true)}><Plus /><span>게임 추가</span></button>
            </div>
          </PageIntro>

          <MetricStrip items={libraryMetrics} />

          <section class="library-panel" aria-label="게임 목록">
            <div class="library-toolbar">
              <label class="library-search">
                <Search />
                <input bind:value={libraryQuery} placeholder="게임명, Steam App ID, 태그 검색" />
              </label>
              <div class="library-filters">
                {#each libraryFilterOptions as filter}
                  <button
                    class="segment"
                    class:active={libraryFilter === filter.id}
                    type="button"
                    on:click={() => (libraryFilter = filter.id)}
                  >
                    {filter.label}
                  </button>
                {/each}
              </div>
            </div>

            <div class="library-summary">
              <span>{formatCount(filteredLibraryGames.length)}개 표시</span>
              <span>{formatCount(gameProjects.reduce((sum, game) => sum + game.reviewCount, 0))}개 리뷰 저장됨</span>
            </div>

            <div class="library-table">
              <div class="library-head">
                <span>게임</span>
                <span>상태</span>
                <span>리뷰</span>
                <span>추천율</span>
                <span>최근 수집</span>
                <span>작업</span>
              </div>
              <div class="library-rows">
                {#each filteredLibraryGames as game}
                  <article class="library-row" class:active={selectedGameId === game.id}>
                    <button class="library-game" type="button" on:click={() => openGame(game)}>
                      <span class="game-cover">{game.shortName}</span>
                      <span>
                        <strong>{game.name}</strong>
                        <small>app/{game.appId} · {game.tags.slice(0, 2).join(' · ')} · {game.queue}</small>
                      </span>
                    </button>
                    <span class={`sentiment ${game.statusTone}`}>{game.status}</span>
                    <span>{formatCount(game.reviewCount)}</span>
                    <span class="score-cell">
                      <strong>{game.reviewCount ? formatPercent(game.positiveRatio) : '-'}</strong>
                      <span class="mini-track" style={`--score: ${Math.round(safeRatio(game.positiveRatio) * 100)}%`}><b></b></span>
                    </span>
                    <span>{latestLabel(game.lastSync)}</span>
                    <span class="row-actions">
                      <button
                        class={game.nextAction === 'open' ? 'ghost-button compact' : 'primary-button compact'}
                        type="button"
                        disabled={isRefreshing || isAnalyzing}
                        on:click={() => runGameAction(game)}
                      >
                        {actionButtonLabel(game.nextAction)}
                      </button>
                    </span>
                  </article>
                {:else}
                  <div class="empty-state">검색 결과가 없습니다.</div>
                {/each}
              </div>
            </div>
          </section>
        </section>

        <section class:active={activeTab === 'dashboard'} class="tab-view" aria-label="대시보드">
          <section class="overview">
            <div class="panel game-summary">
              <div class="game-title">
                <div class="section-head">
                  <div>
                    <h1>{selectedGame.name} 리뷰 반응</h1>
                    <p>{buildGeneratedSummary(dashboard, clusters, evidenceItems)}</p>
                  </div>
                </div>
                <div class="tag-row">
                  <span class="tag">{dataSourceText}</span>
                  <span class="tag">Steam app/{selectedAppId}</span>
                  <span class="tag">{formatCount(dashboard.languages)}개 언어</span>
                  <span class="tag">{clusterSourceText}</span>
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

          <section class="decision-strip">
            <AuditPanel title="직군별 활용성 점검" rows={roleReadinessRows} />
            <div class="method-note analysis-method">
              <Info />
              <div>
                <strong>최근 분석 방식</strong>
                <span>{analysisRunSummary}</span>
              </div>
            </div>
          </section>

          {#if apiState !== 'online' || endpointWarnings.length > 0}
            <div class="method-note"><Info /><div><strong>데이터 상태</strong><span>{apiMessage}. {endpointWarnings.slice(0, 3).join(', ')} 항목은 준비되는 대로 채워집니다.</span></div></div>
          {/if}

          <section class="workspace-grid">
            <div class="panel timeline">
              <div class="timeline-toolbar">
                <div class="section-head">
                  <div>
                    <h2>기간별 반응 변화</h2>
                    <p>타임라인 API가 있으면 월별 추천, 비추천, 혼합 비율을 표시합니다.</p>
                  </div>
                </div>
                <div class="segmented" aria-label="차트 기준">
                  {#each ['추천율', '불만', '언어'] as segment}
                    <button class="segment" class:active={activeSegment === segment} type="button" on:click={() => (activeSegment = segment)}>{segment}</button>
                  {/each}
                </div>
              </div>

              {#if chartRows.length > 0}
                <div class="chart" aria-label="기간별 반응 차트">
                  {#each chartRows as row}
                    <div class="chart-row">
                      <div class="chart-label"><strong>{row.label}</strong><span>{row.bucket}</span></div>
                      <div class="bar-track" style={`--pos: ${row.pos}%; --neg: ${row.neg}%; --neu: ${row.neu}%`}><span></span><span></span><span></span></div>
                      <div class="bar-score">{row.score}</div>
                    </div>
                  {/each}
                </div>
                <div class="legend">
                  <span><b style="background: var(--positive)"></b>추천</span>
                  <span><b style="background: var(--negative)"></b>비추천</span>
                  <span><b style="background: var(--neutral)"></b>혼합</span>
                </div>
              {:else}
                <div class="empty-state">타임라인 데이터가 아직 없습니다. /api/timeline 응답이 준비되면 이 영역이 채워집니다.</div>
              {/if}
            </div>

            <div class="topics">
              <TopicPanel title="불만 토픽" subtitle="비추천 리뷰와 함께 나타나는 클러스터입니다." topics={negativeTopics} />
              <TopicPanel title="호평 토픽" subtitle="추천 리뷰에서 반복적으로 나타난 강점입니다." topics={positiveTopics} />
            </div>
          </section>

          <section class="panel reviews">
            <div class="section-head">
              <div>
                <h2>최근 근거와 대표 리뷰</h2>
                <p>근거 API와 선택 클러스터 리뷰를 함께 확인합니다.</p>
              </div>
            </div>
            <div class="quote-list">
              {#each evidenceItems.slice(0, 3) as evidence}
                <article class="quote">
                  <p>“{evidence.quote}”</p>
                  <footer><span>{evidenceTypeLabel(evidence.evidence_type)}</span><span>{clusterTitle(evidence.cluster_id)}</span><span>{formatDate(evidence.created_at)}</span></footer>
                </article>
              {:else}
                {#each selectedReviews.slice(0, 3) as review}
                  <article class="quote">
                    <p>“{review.text}”</p>
                    <footer><span>{review.language}</span><span>{review.playtime}</span><span>{review.reaction}</span></footer>
                  </article>
                {:else}
                  <div class="empty-state">대표 리뷰가 없습니다. 클러스터를 선택하거나 리뷰를 갱신하세요.</div>
                {/each}
              {/each}
            </div>
          </section>
        </section>

        <section class:active={activeTab === 'data'} class="tab-view" aria-label="데이터 갱신">
          <PageIntro title="데이터 갱신" subtitle="Steam 리뷰를 가져오고 원본 저장, 작업 상태, 분석 대기 상태를 확인합니다.">
            <button class="primary-button" type="button" disabled={isRefreshing} on:click={() => refreshSteamReviews()}><DownloadCloud /><span>{isRefreshing ? '가져오는 중' : '리뷰 가져오기'}</span></button>
          </PageIntro>
          <div class="method-note"><Info /><div><strong>최근 갱신</strong><span>{refreshState}</span></div></div>
          <MetricStrip items={metrics} />
          <section class="control-grid">
            <section class="panel form-panel">
              <div class="section-head">
                <div><h2>수집 조건</h2><p>/api/refresh-steam에 전달할 Steam 리뷰 수집 옵션입니다.</p></div>
              </div>
              <div class="field-grid">
                <label class="field"><span>최대 리뷰 수</span><input type="number" min="1" max="50000" bind:value={refreshOptions.max_reviews} /></label>
                <label class="field"><span>언어</span><select bind:value={refreshOptions.language}><option value="all">전체</option><option value="english">English</option><option value="koreana">Korean</option><option value="schinese">Simplified Chinese</option><option value="japanese">Japanese</option></select></label>
                <label class="field"><span>리뷰 타입</span><select bind:value={refreshOptions.review_type}><option value="all">전체</option><option value="positive">추천</option><option value="negative">비추천</option></select></label>
                <label class="field"><span>구매 유형</span><select bind:value={refreshOptions.purchase_type}><option value="all">전체</option><option value="steam">Steam 구매</option><option value="non_steam_purchase">비 Steam 구매</option></select></label>
                <label class="field toggle-field"><span>샘플 모드</span><input type="checkbox" bind:checked={refreshOptions.sample_mode} /></label>
                <label class="field toggle-field"><span>Live Steam</span><input type="checkbox" bind:checked={refreshOptions.use_live_steam} /></label>
              </div>
            </section>
            <section class="panel">
              <div class="section-head"><div><h2>갱신 작업</h2><p>백엔드가 job을 반환하면 완료까지 폴링합니다.</p></div></div>
              <div class="run-list">
                {#each refreshRunRows as row}
                  {@const RowIcon = row.icon}
                  <div class="run-row"><span class="run-icon"><RowIcon /></span><div><strong>{row.title}</strong><span>{row.detail}</span></div><span class={`sentiment ${row.tone}`}>{row.state}</span></div>
                {/each}
              </div>
            </section>
          </section>
          <AuditPanel title="데이터 품질 체크" rows={[
            ['중복 리뷰', 'review_id 기준 upsert로 재수집 시 같은 리뷰는 갱신됩니다.', '확인', 'good'],
            ['API 상태', endpointWarnings.length ? `${endpointWarnings.join(', ')} 응답 대기` : '필수 데이터 로딩 완료', endpointWarnings.length ? '주의' : '정상', endpointWarnings.length ? 'mixed' : 'good'],
            ['분석 대기', '리뷰 갱신 후 분석 실행 탭에서 새 리뷰 범위로 재실행할 수 있습니다.', '선택', 'mixed']
          ]} />
          <SimpleTable title="저장되는 원본 필드" headers={['필드', '용도', '화면 연결']} rows={[
            ['steam_created_at', '기간 집계와 이벤트 전후 비교', '비교 기준, 대시보드'],
            ['voted_up', '추천/비추천 기본 신호', '모든 차트'],
            ['language', '언어권 비교와 번역 대상 결정', '언어권 비교'],
            ['playtime_at_review', '플레이타임 구간 분석', '클러스터 샘플']
          ]} />
        </section>

        <section class:active={activeTab === 'patches'} class="tab-view" aria-label="비교 기준">
          <PageIntro title="비교 기준" subtitle="패치, 세일, 서버 장애 같은 기준 날짜 전후의 리뷰 신호를 비교합니다. 인과로 단정하지 않습니다.">
            <span class="status">기준 이벤트 {formatCount(events.length)}개</span>
          </PageIntro>
          <section class="event-guide">
            {#each [['1', '날짜를 등록합니다', '패치, 세일, 운영 이슈를 기준 이벤트로 저장합니다.'], ['2', '전후 기간을 정합니다', `현재 비교 창은 전후 ${impactWindowDays}일입니다.`], ['3', '함께 움직인 신호만 봅니다', '패치가 원인이라고 쓰지 않고 같은 기간에 증가/감소한 표현으로 표시합니다.']] as step}
              <article class="step-card"><span class="step-number">{step[0]}</span><div><h3>{step[1]}</h3><p>{step[2]}</p></div></article>
            {/each}
          </section>

          <section class="control-grid">
            <section class="panel form-panel">
              <div class="section-head"><div><h2>기준 이벤트 추가</h2><p>/api/events에 저장할 비교 기준입니다.</p></div><button class="ghost-button" type="button" disabled={isCreatingEvent} on:click={createEvent}><Plus /><span>{isCreatingEvent ? '등록 중' : '이벤트 추가'}</span></button></div>
              <div class="field-grid">
                <label class="field"><span>이벤트 이름</span><input bind:value={newEvent.title} placeholder="예: Patch 1.2" /></label>
                <label class="field"><span>이벤트 유형</span><select bind:value={newEvent.event_type}><option value="patch">패치</option><option value="sale">세일</option><option value="incident">장애</option><option value="note">메모</option></select></label>
                <label class="field"><span>날짜</span><input type="datetime-local" bind:value={newEvent.occurred_at} /></label>
                <label class="field"><span>설명</span><input bind:value={newEvent.description} placeholder="선택 사항" /></label>
              </div>
            </section>
            <section class="panel form-panel">
              <div class="section-head"><div><h2>전후 비교</h2><p>{eventImpactState}</p></div><button class="ghost-button" type="button" on:click={loadEventImpact}><Clock /><span>다시 계산</span></button></div>
              <div class="field-grid">
                <label class="field"><span>선택 이벤트</span><select bind:value={selectedEventId} on:change={loadEventImpact}><option value="">이벤트 없음</option>{#each events as event}<option value={String(event.id)}>{event.title}</option>{/each}</select></label>
                <label class="field"><span>비교 창</span><input type="number" min="1" max="60" bind:value={impactWindowDays} /></label>
              </div>
              <p class="form-message">{eventState}</p>
            </section>
          </section>

          {#if events.length === 0}
            <div class="empty-state">등록된 이벤트가 없습니다. 패치나 세일 날짜를 추가하면 전후 비교를 시작할 수 있습니다.</div>
          {:else}
            <section class="detail-grid">
              <div class="panel">
                <div class="section-head"><div><h2>등록된 기준</h2><p>선택한 이벤트의 전후 리뷰 신호를 별도로 불러옵니다.</p></div></div>
                <div class="patch-list">
                  {#each events as event}
                    <button class="topic-item event-button" class:active={selectedEventId === String(event.id)} type="button" on:click={() => { selectedEventId = String(event.id); loadEventImpact(); }}>
                      <div><strong>{event.title}</strong><span>{formatDate(event.occurred_at)} · {event.description ?? event.event_type}</span></div><span class="status">{event.event_type}</span>
                    </button>
                  {/each}
                </div>
              </div>
              <div class="panel topic-panel">
                <div class="section-head"><div><h2>선택 이벤트의 변화</h2><p>같은 기간에 관측된 변화입니다. 원인이라고 단정하지 않습니다.</p></div></div>
                {#if eventImpact}
                  <MetricStrip items={[
                    ['전 기간 표본', formatCount(eventImpact.beforeCount), `${impactWindowDays}일`],
                    ['후 기간 표본', formatCount(eventImpact.afterCount), `${impactWindowDays}일`],
                    ['추천율 변화', eventImpact.deltaPoints === null ? '미상' : deltaLabelFrom(eventImpact.deltaPoints), '상관 신호'],
                    ['후 추천율', eventImpact.afterPositiveRatio === null ? '미상' : formatPercent(eventImpact.afterPositiveRatio), '선택 이벤트 기준']
                  ]} />
                  <div class="topic-list">
                    {#each eventImpact.notes as note}
                      <div class="topic-item"><div><strong>해석 메모</strong><span>{note}</span></div><span class="trend flat">주의</span></div>
                    {/each}
                  </div>
                  <TopicPanel title="함께 움직인 표현" subtitle="전후 비교에서 같이 변한 항목입니다." topics={eventImpact.topics.length ? eventImpact.topics : [['표현 데이터 없음', 'impact 응답에 토픽 변화가 없습니다.', '대기', 'flat']]} />
                {:else}
                  <div class="empty-state">{eventImpactState}</div>
                {/if}
              </div>
            </section>
          {/if}
        </section>

        <section class:active={activeTab === 'runs'} class="tab-view" aria-label="분석 실행">
          <PageIntro title="분석 실행" subtitle="임베딩, 클러스터링, 토픽 태깅, AI 요약을 백엔드 작업으로 실행합니다.">
            <button class="primary-button" type="button" disabled={isAnalyzing} on:click={() => startAnalysisRun()}><Play /><span>{isAnalyzing ? '실행 중' : '분석 시작'}</span></button>
          </PageIntro>
          <MetricStrip items={analysisMetrics} />
          <div class="method-note"><Info /><div><strong>분석 상태</strong><span>{analysisState}</span></div></div>
          <section class="control-grid">
            <section class="panel">
              <div class="section-head"><div><h2>파이프라인</h2><p>반환된 job이 있으면 /api/jobs/{'{job_id}'}로 상태를 확인합니다.</p></div></div>
              <div class="run-list">
                {#each analysisPipelineRows as row}
                  {@const RowIcon = row.icon}
                  <div class="run-row"><span class="run-icon"><RowIcon /></span><div><strong>{row.title}</strong><span>{row.detail}</span></div><span class={`sentiment ${row.tone}`}>{row.state}</span></div>
                {/each}
              </div>
            </section>
            <section class="panel form-panel">
              <div class="section-head"><div><h2>실행 옵션</h2><p>/api/analysis-runs에 전달할 범위와 모델 설정입니다.</p></div></div>
              <div class="field-grid">
                <label class="field"><span>분석 범위</span><select bind:value={analysisOptions.scope}><option value="new">새 리뷰</option><option value="all">전체</option></select></label>
                <label class="field"><span>임베딩 모델</span><input bind:value={analysisOptions.embedding_model} /></label>
                <label class="field"><span>최소 클러스터 크기</span><input type="number" min="2" max="500" bind:value={analysisOptions.min_cluster_size} /></label>
                <label class="field"><span>LLM 공급자</span><select bind:value={analysisOptions.llm_provider}><option value="lm_studio">LM Studio</option><option value="openai">OpenAI</option><option value="claude">Claude</option><option value="none">사용 안 함</option></select></label>
                <label class="field toggle-field"><span>AI 요약 생성</span><input type="checkbox" bind:checked={analysisOptions.generate_ai_summary} /></label>
              </div>
            </section>
          </section>
          <AuditPanel title="분석 품질" rows={[
            ['클러스터 포함률', clusterSource === 'backend' ? '백엔드 클러스터 결과를 표시 중입니다.' : '분석 결과가 없거나 샘플 표시 중입니다.', clusterSource === 'backend' ? '확인' : '대기', clusterSource === 'backend' ? 'good' : 'mixed'],
            ['잡음 리뷰', '짧은 문장, 반복 문구, 오프토픽 처리는 백엔드 분석 정책에 따릅니다.', '정책', 'mixed'],
            ['사람 검증', `${formatCount(evidenceItems.length)}개 근거를 근거 검증 탭에서 확인할 수 있습니다.`, evidenceItems.length ? '진행' : '대기', evidenceItems.length ? 'good' : 'mixed']
          ]} />
          <SimpleTable
            title="최근 분석 이력"
            headers={['Run', '상태', '방식', '완료 시각']}
            rows={analysisRunRows.length ? analysisRunRows : [['대기', '분석 이력이 없습니다.', '분석 시작 후 표시', '대기']]}
          />
        </section>

        <section class:active={activeTab === 'clusters'} class="tab-view" aria-label="리뷰 클러스터">
          <PageIntro title="리뷰 클러스터" subtitle="언어가 달라도 같은 의미의 리뷰를 묶어서 호평, 불만, 기능 요청을 봅니다.">
            <span class="status">{clusterSourceText} · {formatCount(filteredClusters.length)}/{formatCount(clusters.length)}개</span>
          </PageIntro>
          <MetricStrip items={clusterMetrics} />
          <AuditPanel title="먼저 볼 클러스터" rows={clusterFocusRows} />
          {#if clusters.length === 0}
            <div class="empty-state">클러스터가 없습니다. 데이터 갱신 후 분석 실행을 시작하세요.</div>
          {:else}
            <section class="cluster-tools" aria-label="클러스터 필터">
              <label class="library-search">
                <Search />
                <input bind:value={clusterQuery} placeholder="클러스터명, 요약, 언어 태그 검색" />
              </label>
              <div class="library-filters">
                {#each clusterToneOptions as filter}
                  <button
                    class="segment"
                    class:active={clusterToneFilter === filter.id}
                    type="button"
                    on:click={() => (clusterToneFilter = filter.id)}
                  >
                    {filter.label}
                  </button>
                {/each}
              </div>
            </section>
            <section class="cluster-grid">
              {#each filteredClusters as cluster}
                <button class="cluster-node" class:active={activeCluster === cluster.id} type="button" on:click={() => loadClusterReviews(cluster.id)}>
                  <header><h3>{cluster.title}</h3><span class={`sentiment ${cluster.tone}`}>{cluster.count}</span></header>
                  <p>{cluster.description}</p>
                  <div class="cluster-tags">{#each cluster.tags as tag}<span class="cluster-tag">{tag}</span>{/each}</div>
                </button>
              {:else}
                <div class="empty-state">조건에 맞는 클러스터가 없습니다.</div>
              {/each}
            </section>
            {#if selectedCluster}
              <section class="panel cluster-detail">
                <div class="detail-head"><div><h2>{selectedCluster.title}</h2><p>{selectedCluster.backend ? '백엔드 리뷰 샘플을 불러온 결과입니다.' : '백엔드 미연결 시 표시하는 샘플입니다.'}</p></div><span class={`sentiment ${selectedCluster.tone}`}>{sentimentLabel(selectedCluster.tone)}</span></div>
                <div class="review-samples">
                  {#each selectedReviews as sample}
                    <article class="review-sample"><div class="sample-meta"><strong>{sample.language}</strong><span>{sample.playtime}</span><span class={`sentiment ${sample.reactionTone}`}>{sample.reaction}</span></div><p>“{sample.text}”</p><small>대표도 {sample.score}</small></article>
                  {:else}
                    <div class="empty-state">이 클러스터의 리뷰 샘플이 아직 없습니다.</div>
                  {/each}
                </div>
              </section>
            {/if}
          {/if}
        </section>

        <section class:active={activeTab === 'languages'} class="tab-view" aria-label="언어권 비교">
          <PageIntro title="언어권 비교" subtitle="/api/languages 기준으로 표본 크기와 추천율 차이를 확인합니다.">
            <span class="status">{formatCount(languages.length)}개 언어</span>
          </PageIntro>
          <MetricStrip items={languageMetrics} />
          <section class="detail-grid">
            <div class="panel">
              <div class="section-head"><div><h2>언어별 반응</h2><p>추천, 비추천, 가중 점수의 상대 비중입니다.</p></div></div>
              <div class="language-list">
                {#each languageRows as language}
                  <div class="language-row"><strong>{language[0]}</strong><div class="spark" style={`--pos: ${language[1].split('%')[0]}%; --neg: 16%; --neu: 10%`}><b></b><b></b><b></b></div><span>{language[1]}</span><span>{language[2]}</span></div>
                {:else}
                  <div class="empty-state">언어 데이터가 없습니다. /api/languages 응답을 기다리는 중입니다.</div>
                {/each}
              </div>
            </div>
            <TopicPanel title="지역별 읽을거리" subtitle="표본 크기와 추천율 차이가 큰 언어입니다." topics={languageRows.slice(0, 3).map((row) => [row[0], row[1], row[2], 'flat'])} />
          </section>
        </section>

        <section class:active={activeTab === 'evidence'} class="tab-view" aria-label="근거 검증">
          <PageIntro title="근거 검증" subtitle="/api/evidence의 원문 근거와 AI 해석을 분리해서 확인합니다.">
            <span class="status">근거 {formatCount(evidenceItems.length)}개</span>
          </PageIntro>
          <section class="control-grid">
            <div class="panel form-panel">
              <div class="section-head"><div><h2>주요 주장</h2><p>리포트에 들어갈 문장이 어떤 근거에서 나왔는지 확인합니다.</p></div></div>
              <div class="truth-list">
                {#each evidenceClaims as claim}
                  <article class="truth-item"><div><h3>{claim[0]}</h3><p>{claim[1]}</p></div><span class={`claim ${claim[3]}`}>{claim[2]}</span></article>
                {/each}
              </div>
            </div>
            <section class="panel evidence">
              <div class="section-head"><div><h3>근거 리뷰</h3><p>대표 클러스터에서 추출한 문장입니다.</p></div></div>
              <div class="quote-list">
                {#each evidenceItems.slice(0, 5) as evidence}
                  <article class="quote">
                    <p>“{evidence.quote}”</p>
                    <footer><span>{evidenceTypeLabel(evidence.evidence_type)}</span><span>{clusterTitle(evidence.cluster_id)}</span><span>{formatDate(evidence.created_at)}</span></footer>
                  </article>
                {:else}
                  <div class="empty-state">근거 리뷰가 없습니다. 분석 실행 후 다시 확인하세요.</div>
                {/each}
              </div>
            </section>
          </section>
          <SimpleTable title="검증 큐" headers={['유형', '문장', '클러스터', '생성일']} rows={evidenceTableRows.length ? evidenceTableRows : [['대기', '근거 데이터가 아직 없습니다.', '미연결', '대기']]} />
        </section>

        <section class:active={activeTab === 'report'} class="tab-view" aria-label="리포트">
          <PageIntro title="리포트" subtitle="/api/reports의 최근 리포트를 읽고, 현재 API 데이터로 간단한 리포트를 생성합니다.">
            <button class="primary-button" type="button" disabled={isGeneratingReport} on:click={generateReport}><Sparkles /><span>{isGeneratingReport ? '생성 중' : '다시 생성'}</span></button>
          </PageIntro>
          <AuditPanel title="리포트 검증 상태" rows={[
            ['데이터 버전', `${dataSourceText} · ${latestLabel(dashboard.latest_review_at)}`, dataSource === 'api' ? '확인' : '샘플', dataSource === 'api' ? 'good' : 'mixed'],
            ['리포트 API', reports.length ? `${formatCount(reports.length)}개 저장됨` : reportState, reports.length ? '준비' : '대기', reports.length ? 'good' : 'mixed'],
            ['근거 확인', `${formatCount(evidenceItems.length)}개 근거 연결`, evidenceItems.length ? '진행' : '대기', evidenceItems.length ? 'good' : 'mixed']
          ]} />
          <section class="report-layout">
            <article class="panel report-doc">
              {#each reportBlocks as block}
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
          <PageIntro title="모델 설정" subtitle="/api/settings/models 기준으로 로컬/클라우드 모델 상태를 확인합니다.">
            <button class="ghost-button" type="button" on:click={() => loadApiData()}><PlugZap /><span>연결 확인</span></button>
          </PageIntro>
          <div class="method-note"><Info /><div><strong>모델 상태</strong><span>우선 /api/settings/models를 읽고, 없으면 현재 백엔드의 /api/settings로 fallback합니다.</span></div></div>
          <section class="settings-grid">
            <div class="panel connection-card">
              <div class="section-head"><div><h2>LLM 연결</h2><p>요약과 분류에 사용할 모델 공급자입니다.</p></div></div>
              {#each modelOptions as model}
                {@const ModelIcon = model.icon}
                <div class="model-option"><ModelIcon /><div><strong>{model.name}</strong><span>{model.detail}</span></div><span class={`sentiment ${model.tone}`}>{model.state}</span></div>
              {/each}
            </div>
            <section class="panel form-panel">
              <div class="section-head"><div><h2>분석 기본값</h2><p>느린 작업과 비용이 큰 작업은 분석 실행 탭에서 명시적으로 시작합니다.</p></div></div>
              <div class="field-grid">
                <label class="field"><span>기본 요약 모델</span><input bind:value={analysisOptions.llm_provider} /></label>
                <label class="field"><span>기본 임베딩</span><input bind:value={analysisOptions.embedding_model} /></label>
                <label class="field toggle-field"><span>리포트 생성</span><input type="checkbox" bind:checked={analysisOptions.generate_ai_summary} /></label>
                <label class="field"><span>최소 클러스터 크기</span><input type="number" bind:value={analysisOptions.min_cluster_size} /></label>
              </div>
            </section>
          </section>
          <SimpleTable title="구현 메모" headers={['화면', '백엔드 역할', '기술']} rows={[
            ['데이터 갱신', 'Steam API 호출, cursor 저장, DuckDB upsert', 'FastAPI + DuckDB'],
            ['분석 실행', '임베딩/클러스터링 배치 작업과 진행률 저장', 'Python worker'],
            ['AI 리포트', '클러스터 대표 리뷰를 LLM에 보내고 결과 캐시', 'LM Studio/Claude/OpenAI'],
            ['근거 검증', '요약 문장과 원문 리뷰 연결 관계 저장', 'DuckDB']
          ]} />
        </section>
      </main>

      {#if showInspector}
      <aside class="inspector" aria-label="AI 분석 패널">
        <div class="inspector-inner">
            <section class="panel ai-panel">
              <div class="section-head"><div><h3>AI 브리프</h3><p>{dataSourceText}</p></div><span class="status">{modelOptions[0]?.name ?? 'Model'}</span></div>
              <div class="ai-summary">
                {#each aiBrief as paragraph}
                  <p>{paragraph}</p>
                {/each}
              </div>
            </section>
            <AuditPanel title="분석 신뢰도" rows={inspectorRows} compact />
            <section class="panel priority">
              <div class="section-head"><div><h3>기획 우선순위</h3><p>빈도, 심각도, 최근성을 함께 보되 인과로 단정하지 않습니다.</p></div></div>
              <ol class="priority-list">
                {#each priorityItems as item}
                  <li><span class="rank">{item[0]}</span><div><strong>{item[1]}</strong><span>{item[2]}</span></div><span class={`sentiment ${item[4]}`}>{item[3]}</span></li>
                {/each}
              </ol>
            </section>
            <section class="panel evidence">
              <div class="section-head"><div><h3>근거 리뷰</h3><p>최근 근거 문장입니다.</p></div></div>
              <div class="quote-list">
                {#each evidenceItems.slice(0, 2) as evidence}
                  <article class="quote">
                    <p>“{evidence.quote}”</p>
                    <footer><span>{evidenceTypeLabel(evidence.evidence_type)}</span><span>{clusterTitle(evidence.cluster_id)}</span></footer>
                  </article>
                {:else}
                  <div class="empty-state">근거 API 대기 중입니다.</div>
                {/each}
              </div>
            </section>
        </div>
      </aside>
      {/if}
    </div>
  </div>
</div>

{#if showGameDialog}
  <div class="modal-backdrop" role="presentation" on:click={(event) => event.target === event.currentTarget && (showGameDialog = false)}>
    <form class="modal-card" aria-label="게임 추가" on:submit|preventDefault={createGame}>
      <div class="modal-head">
        <div>
          <h2>게임 추가</h2>
          <p>Steam App ID와 표시 이름을 저장합니다. 수집과 분석은 목록에서 직접 시작합니다.</p>
        </div>
        <button class="ghost-button compact" type="button" on:click={() => (showGameDialog = false)}>닫기</button>
      </div>
      <div class="field-grid">
        <label class="field"><span>Steam App ID</span><input bind:value={gameForm.app_id} placeholder="예: 1145350" /></label>
        <label class="field"><span>게임명</span><input bind:value={gameForm.name} placeholder="예: Hades II" /></label>
        <label class="field"><span>별칭</span><input bind:value={gameForm.short_name} placeholder="예: HII" /></label>
        <label class="field"><span>태그</span><input bind:value={gameForm.tags} placeholder="패치 추적, 비교군" /></label>
      </div>
      <label class="field modal-note"><span>메모</span><input bind:value={gameForm.note} placeholder="이 게임을 왜 추적하는지 적어둡니다." /></label>
      <div class="modal-actions">
        <span>{gameFormState}</span>
        <button class="primary-button" type="submit"><Plus /><span>저장</span></button>
      </div>
    </form>
  </div>
{/if}

{#if showSettingsPanel}
  <div class="modal-backdrop align-right" role="presentation" on:click={(event) => event.target === event.currentTarget && (showSettingsPanel = false)}>
    <section class="modal-card settings-drawer" aria-label="설정 패널">
      <div class="modal-head">
        <div>
          <h2>설정</h2>
          <p>수집, 분석, 큐 기본값입니다.</p>
        </div>
        <button class="ghost-button compact" type="button" on:click={() => (showSettingsPanel = false)}>닫기</button>
      </div>
      <div class="field-grid">
        <label class="field"><span>수집 언어</span><select bind:value={refreshOptions.language}><option value="all">전체</option><option value="english">EN</option><option value="koreana">KO</option><option value="schinese">ZH</option><option value="japanese">JA</option></select></label>
        <label class="field"><span>최대 리뷰</span><input type="number" min="1" max="50000" bind:value={refreshOptions.max_reviews} /></label>
        <label class="field"><span>분석 범위</span><select bind:value={analysisOptions.scope}><option value="new">새 리뷰</option><option value="all">전체</option></select></label>
        <label class="field"><span>최소 클러스터</span><input type="number" min="1" max="1000" bind:value={analysisOptions.min_cluster_size} /></label>
        <label class="field"><span>임베딩</span><input bind:value={analysisOptions.embedding_model} /></label>
        <label class="field"><span>LLM</span><select bind:value={analysisOptions.llm_provider}><option value="lm_studio">LM Studio</option><option value="none">사용 안 함</option></select></label>
      </div>
      <div class="modal-actions">
        <span>현재 v1은 자동 큐 대신 목록 버튼으로 수동 실행합니다.</span>
        <button class="primary-button" type="button" on:click={() => (showSettingsPanel = false)}>적용</button>
      </div>
    </section>
  </div>
{/if}
