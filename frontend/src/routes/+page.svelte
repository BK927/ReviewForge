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
    | 'workbench'
    | 'insights'
    | 'axes'
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
  type PlanningLaneId = 'fix' | 'preserve' | 'expand' | 'communicate';
  type ClusterId = string;
  type LibraryFilter = 'all' | 'ready' | 'needs-analysis' | 'needs-sync' | 'watch';
  type IssueStatusFilter = 'all' | 'confirmed' | 'needs_review' | 'strength' | 'diagnostic';
  type IssueEvidenceFilter = 'match' | 'partial' | 'reject' | 'unverified' | 'all';

  type ApiDashboard = {
    total_reviews: number;
    positive_reviews: number;
    negative_reviews: number;
    positive_ratio: number;
    languages: number;
    clusters: number;
    evidence_items: number;
    issues?: number;
    confirmed_issues?: number;
    issue_evidence_items?: number;
    issue_coverage?: number | null;
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
    positive_ratio?: number | null;
    top_keywords?: string[] | null;
    keyword_method?: string | null;
    quality_warning?: string | null;
    label_source?: string | null;
    label_confidence?: string | null;
    label_warnings?: string[] | null;
    matched_theme_key?: string | null;
    matched_terms?: string[] | null;
    insight?: {
      title?: string | null;
      summary?: string | null;
      praise?: string | null;
      pain_point?: string | null;
      planner_action?: string | null;
      marketing_angle?: string | null;
      confidence?: number | null;
      warnings?: string[] | null;
      source?: string | null;
      model?: string | null;
    } | null;
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
    quality_score?: number | null;
    quality_flags?: string[] | null;
    duplicate_count?: number | null;
    steam_created_at?: string | null;
  };

  type ApiEvidence = {
    id: number;
    claim_id?: number | null;
    review_id: string;
    cluster_id: number | null;
    quote: string;
    evidence_type: string;
    evidence_role?: string | null;
    note: string | null;
    quality_score?: number | null;
    claim_text?: string | null;
    claim_type?: string | null;
    created_at: string;
  };

  type ApiClaim = {
    id: number;
    analysis_run_id?: number | null;
    cluster_id?: number | null;
    claim_type: string;
    claim_text: string;
    confidence: number;
    created_at: string;
  };

  type ApiIssue = {
    id: number;
    analysis_run_id: number;
    app_id?: string | null;
    title: string;
    summary: string;
    intent: string;
    aspect: string;
    status: string;
    confidence_band: string;
    confidence: number;
    priority_score: number;
    review_count: number;
    unique_review_count: number;
    unit_count: number;
    complaint_count: number;
    praise_count: number;
    request_count: number;
    bug_count: number;
    positive_ratio?: number | null;
    language_counts?: Record<string, number>;
    top_terms?: string[];
    why_it_matters?: string | null;
    recommended_action?: string | null;
    warnings?: string[];
    evidence_count?: number;
    match_evidence_count?: number;
    partial_evidence_count?: number;
    reject_evidence_count?: number;
    unverified_evidence_count?: number;
    source?: string | null;
    model?: string | null;
    created_at: string;
  };

  type ApiIssueEvidence = {
    id: number;
    issue_id: number;
    unit_id?: number | null;
    analysis_run_id: number;
    app_id?: string | null;
    review_id: string;
    quote: string;
    evidence_role: string;
    language?: string | null;
    voted_up?: boolean | null;
    quality_score?: number | null;
    verifier_verdict?: string | null;
    summary_ko?: string | null;
    subissue?: string | null;
    verifier_reason?: string | null;
    review_text?: string | null;
    playtime_at_review?: number | null;
    steam_created_at?: string | null;
    created_at: string;
  };

  type ApiIssueSummary = {
    issues: number;
    confirmed_issues: number;
    needs_review_issues: number;
    strength_issues: number;
    diagnostic_issues: number;
    issue_evidence_items: number;
    issue_units: number;
    quarantined_units: number;
    issue_coverage?: number | null;
  };

  type ApiAxis = {
    id: number;
    key: string;
    label: string;
    description: string;
    pattern: string;
    recommended_action: string;
    scope: string;
    app_id?: string | null;
    genre?: string | null;
    status: string;
    source: string;
    created_at: string;
    updated_at: string;
  };

  type ApiAxisSuggestion = {
    id: number;
    analysis_run_id: number;
    app_id?: string | null;
    label: string;
    rationale: string;
    suggested_pattern: string;
    evidence_count: number;
    language_counts?: Record<string, number>;
    example_review_ids?: string[];
    kind?: string;
    canonical_label_ko?: string | null;
    definition?: string | null;
    include_criteria?: string[];
    exclude_criteria?: string[];
    evidence_claim_ids?: string[];
    why_actionable?: string | null;
    quality_gate?: string;
    failure_reason?: string | null;
    status: string;
    target_axis_id?: number | null;
    created_at: string;
    updated_at: string;
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
    issue_count?: number;
    confirmed_issue_count?: number;
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
    issues_created?: number;
    issue_evidence_created?: number;
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
    positiveRatio: number | null;
    keywords: string[];
    keywordMethod: string | null;
    qualityWarning: string | null;
    labelSource?: string | null;
    labelConfidence?: string | null;
    labelWarnings?: string[];
    matchedThemeKey?: string | null;
    matchedTerms?: string[];
    insightSource: string | null;
    insightModel: string | null;
    insight: NonNullable<ApiCluster['insight']> | null;
  };

  type ReviewSample = {
    language: string;
    playtime: string;
    reaction: string;
    reactionTone: Tone;
    text: string;
    score: string;
    quality: string;
    flags: string[];
    duplicateCount: number;
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

  type PlanningDecision = {
    id: PlanningLaneId;
    label: string;
    verb: string;
    detail: string;
    tone: Tone;
  };

  type PlanningLaneView = {
    id: PlanningLaneId;
    label: string;
    count: number;
    title: string;
    detail: string;
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
    issues: number;
    confirmedIssues: number;
    lastSync: string | null;
    lastAnalysis: string | null;
    queue: string;
    note: string;
    tags: string[];
    nextAction: 'sync' | 'analyze' | 'open';
  };

  const tabs: Array<{ id: TabId; label: string; group: 'Project' | 'Analysis'; icon: IconComponent }> = [
    { id: 'library', label: '게임 라이브러리', group: 'Project', icon: Library },
    { id: 'workbench', label: '분석 작업대', group: 'Project', icon: LayoutDashboard },
    { id: 'insights', label: '인사이트 보드', group: 'Analysis', icon: MessagesSquare },
    { id: 'evidence', label: '근거 확인', group: 'Analysis', icon: ScanSearch },
    { id: 'axes', label: '평가축 관리', group: 'Analysis', icon: SlidersHorizontal },
    { id: 'report', label: '리포트', group: 'Analysis', icon: FileText },
    { id: 'settings', label: '실행/설정', group: 'Analysis', icon: Activity }
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

  const issueStatusOptions: Array<{ id: IssueStatusFilter; label: string }> = [
    { id: 'all', label: '전체' },
    { id: 'confirmed', label: '근거 충분' },
    { id: 'needs_review', label: '검토 필요' },
    { id: 'strength', label: '활용 포인트' },
    { id: 'diagnostic', label: '진단' }
  ];

  const issueEvidenceFilterOptions: Array<{ id: IssueEvidenceFilter; label: string }> = [
    { id: 'match', label: '검증 통과' },
    { id: 'partial', label: '부분 관련' },
    { id: 'reject', label: '제외 근거' },
    { id: 'unverified', label: '미검증' },
    { id: 'all', label: '전체' }
  ];

  const emptyDashboard: ApiDashboard = {
    total_reviews: 0,
    positive_reviews: 0,
    negative_reviews: 0,
    positive_ratio: 0,
    languages: 0,
    clusters: 0,
    evidence_items: 0,
    issues: 0,
    confirmed_issues: 0,
    issue_evidence_items: 0,
    issue_coverage: null,
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
    issues: 9,
    confirmed_issues: 4,
    issue_evidence_items: 42,
    issue_coverage: 0.37,
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
      positiveRatio: 0.42,
      keywords: ['반복', '보상', '후반'],
      keywordMethod: 'sample',
      qualityWarning: null,
      insightSource: null,
      insightModel: null,
      insight: null,
      samples: [
        {
          language: 'EN',
          playtime: '62.4h',
          reaction: '비추천',
          reactionTone: 'bad',
          text: 'The combat is still great, but every run after the credits feels like chasing tiny upgrades.',
          score: '94%',
          quality: '92%',
          flags: [],
          duplicateCount: 1
        },
        {
          language: 'KO',
          playtime: '48.9h',
          reaction: '혼합',
          reactionTone: 'mixed',
          text: '초반은 정말 좋은데, 어느 순간부터 보상 변화가 작아서 계속할 이유가 약해진다.',
          score: '88%',
          quality: '90%',
          flags: [],
          duplicateCount: 1
        }
      ]
    },
    {
      id: 'sample-combat',
      title: '캐릭터와 장면 매력',
      count: '8,441',
      countValue: 8441,
      tone: 'good',
      description: '샘플 데이터입니다. 캐릭터 매력, 장면 연출, 기억에 남는 대사가 강점으로 반복 언급됩니다.',
      tags: ['샘플', '전체 언어', '추천 연결 높음'],
      backend: false,
      positiveRatio: 0.91,
      keywords: ['캐릭터', '연출', '대사'],
      keywordMethod: 'sample',
      qualityWarning: null,
      insightSource: null,
      insightModel: null,
      insight: null,
      samples: [
        {
          language: 'EN',
          playtime: '14.2h',
          reaction: '추천',
          reactionTone: 'good',
          text: 'The characters stay memorable, and several scenes keep coming back to me after finishing it.',
          score: '91%',
          quality: '89%',
          flags: [],
          duplicateCount: 1
        },
        {
          language: 'KO',
          playtime: '12.1h',
          reaction: '추천',
          reactionTone: 'good',
          text: '캐릭터가 오래 기억에 남고, 몇몇 장면은 엔딩을 본 뒤에도 계속 떠오른다.',
          score: '87%',
          quality: '88%',
          flags: [],
          duplicateCount: 1
        }
      ]
    }
  ];

  const sampleGameProjects: GameProject[] = [
    {
      id: '3101040',
      name: 'Magical Girl Witch Trials',
      appId: '3101040',
      shortName: 'MGW',
      status: '백엔드 연결 필요',
      statusTone: 'mixed',
      reviewCount: 0,
      languages: 0,
      positiveRatio: 0,
      clusters: 0,
      evidenceItems: 0,
      issues: 0,
      confirmedIssues: 0,
      lastSync: null,
      lastAnalysis: null,
      queue: '백엔드 연결 후 저장된 분석을 불러옵니다.',
      note: '사용자가 직접 결과를 검토할 테스트 게임입니다.',
      tags: ['사용자 테스트', '추리/비주얼 노벨'],
      nextAction: 'sync'
    },
    {
      id: '1456820',
      name: 'Marfusha: Sentinel Girls',
      appId: '1456820',
      shortName: 'MSG',
      status: '백엔드 연결 필요',
      statusTone: 'mixed',
      reviewCount: 0,
      languages: 0,
      positiveRatio: 0,
      clusters: 0,
      evidenceItems: 0,
      issues: 0,
      confirmedIssues: 0,
      lastSync: null,
      lastAnalysis: null,
      queue: '백엔드 연결 후 저장된 분석을 불러옵니다.',
      note: '사용자가 직접 결과를 검토할 테스트 게임입니다.',
      tags: ['사용자 테스트', '방어/카드'],
      nextAction: 'sync'
    },
    {
      id: '1859910',
      name: 'Legend of Mortal',
      appId: '1859910',
      shortName: 'LOM',
      status: '백엔드 연결 필요',
      statusTone: 'mixed',
      reviewCount: 0,
      languages: 0,
      positiveRatio: 0,
      clusters: 0,
      evidenceItems: 0,
      issues: 0,
      confirmedIssues: 0,
      lastSync: null,
      lastAnalysis: null,
      queue: '백엔드 연결 후 저장된 분석을 불러옵니다.',
      note: '사용자가 직접 결과를 검토할 테스트 게임입니다.',
      tags: ['사용자 테스트', '무협 RPG'],
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
  let claims: ApiClaim[] = [];
  let issues: ApiIssue[] = [];
  let axes: ApiAxis[] = [];
  let axisSuggestions: ApiAxisSuggestion[] = [];
  let axisState = '분석 실행 후 평가축 후보가 표시됩니다.';
  let issueSummary: ApiIssueSummary = {
    issues: 0,
    confirmed_issues: 0,
    needs_review_issues: 0,
    strength_issues: 0,
    diagnostic_issues: 0,
    issue_evidence_items: 0,
    issue_units: 0,
    quarantined_units: 0,
    issue_coverage: null
  };
  let activeIssue = '';
  let issueEvidenceItems: ApiIssueEvidence[] = [];
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
    llm_provider: 'lm_studio',
    llm_model: 'supergemma4-e4b-abliterated',
    min_quality_score: 0.25,
    exclude_duplicate_evidence: true,
    use_lmstudio_labels: true,
    max_clusters: 60,
    evidence_per_claim: 3
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
  let issueQuery = '';
  let issueStatusFilter: IssueStatusFilter = 'all';
  let issueEvidenceFilter: IssueEvidenceFilter = 'match';
  let issueEvidenceQuery = '';
  let showRawAxisSuggestions = false;
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
  $: showInspector = activeTab === 'report';
  $: latestAnalysisRun = analysisRuns[0] ?? null;
  $: analysisRunSummary = buildAnalysisRunSummary(latestAnalysisRun);
  $: analysisRunRows = buildAnalysisRunRows(analysisRuns);
  $: positiveRatio = Math.round(safeRatio(dashboard.positive_ratio) * 100);
  $: projectReviewCount = formatCount(dashboard.total_reviews);
  $: projectLanguageCount = formatCount(dashboard.languages);
  $: selectedIssue = issues.find((issue) => String(issue.id) === activeIssue) ?? issues[0] ?? null;
  $: latestReport = reports[0] ?? null;
  $: kpis = buildKpis(dashboard, clusterSourceText);
  $: metrics = buildDataMetrics(dashboard, refreshJob, dataSourceText);
  $: chartRows = buildChartRows(timelineRows, dashboard);
  $: negativeTopics = buildTopicRows('bad');
  $: positiveTopics = buildTopicRows('good');
  $: languageMetrics = buildLanguageMetrics(languages, dataSourceText);
  $: languageRows = buildLanguageRows(languages);
  $: claimRows = buildClaimRows(claims, evidenceItems);
  $: evidenceTableRows = buildEvidenceTableRows(evidenceItems);
  $: reportBlocks = buildReportBlocks(latestReport, dashboard, issues, clusters, issueEvidenceItems.length || evidenceItems.length);
  $: marketingBriefRows = buildMarketingBriefRows(issues, issueEvidenceItems);
  $: analysisMetrics = buildAnalysisMetrics(dashboard, clusters, evidenceItems, reports, analysisJob, clusterSourceText);
  $: inspectorRows = buildInspectorRows(dashboard, evidenceItems.length);
  $: priorityItems = buildPriorityItems();
  $: aiBrief = buildAiBrief(latestReport, issues, dashboard);
  $: selectedGame = gameProjects.find((game) => game.id === selectedGameId) ?? gameProjects[0] ?? sampleGameProjects[0];
  $: selectedAppId = selectedGame?.appId ?? DEFAULT_APP_ID;
  $: libraryMetrics = buildLibraryMetrics(gameProjects);
  $: selectedGameFacts = buildSelectedGameFacts(selectedGame);
  $: selectedGameSteps = buildSelectedGameSteps(selectedGame);
  $: gameComparisonRows = buildGameComparisonRows(gameProjects);
  $: filteredLibraryGames = filterLibraryGames(gameProjects, libraryQuery, libraryFilter);
  $: filteredIssues = filterIssues(issues, issueQuery, issueStatusFilter);
  $: issueEvidenceStats = buildIssueEvidenceStats(issueEvidenceItems);
  $: issueEvidenceSubissues = buildIssueEvidenceSubissues(issueEvidenceItems);
  $: filteredIssueEvidenceItems = filterIssueEvidence(issueEvidenceItems, issueEvidenceFilter, issueEvidenceQuery);
  $: issueMetrics = buildIssueMetrics(issueSummary, dashboard);
  $: issueAuditRows = buildIssueAuditRows(issueSummary, dashboard);
  $: planningLanes = buildPlanningLanes(issues);
  $: activeAxes = axes.filter((axis) => axis.status === 'active');
  $: pendingAxisSuggestions = axisSuggestions.filter(
    (suggestion) => suggestion.status === 'pending' && (showRawAxisSuggestions || suggestion.quality_gate !== 'fail')
  );
  $: visibleAxisSuggestions = axisSuggestions.filter((suggestion) => showRawAxisSuggestions || suggestion.quality_gate !== 'fail');
  $: axisMetrics = buildAxisMetrics(activeAxes, pendingAxisSuggestions, issues);
  $: roleReadinessRows = buildRoleReadinessRows(dashboard, evidenceItems, languages, analysisRuns, events, reports);
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
      title: '의견 묶기',
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
    const axisSuggestionQuery = `${appQuery}${showRawAxisSuggestions ? '&include_raw=true' : ''}`;

    const [
      dashboardResult,
      languagesResult,
      eventsResult,
      timelineResult,
      clustersResult,
      evidenceResult,
      claimsResult,
      issuesResult,
      axesResult,
      axisSuggestionsResult,
      issueSummaryResult,
      reportsResult,
      analysisRunsResult,
      modelsResult
    ] = await Promise.all([
      get<ApiDashboard>(`/dashboard?${appQuery}`, '대시보드'),
      get<ApiLanguage[]>(`/languages?${appQuery}`, '언어'),
      get<ApiEvent[]>(`/events?${appQuery}`, '이벤트'),
      get<unknown>(`/timeline?${appQuery}&bucket=month`, '타임라인'),
      get<ApiCluster[]>(`/clusters?${appQuery}`, '자동 묶음'),
      get<ApiEvidence[]>(`/evidence?${appQuery}`, '근거'),
      get<ApiClaim[]>(`/claims?${appQuery}`, '주장'),
      get<ApiIssue[]>(`/issues?${appQuery}`, '이슈'),
      get<ApiAxis[]>(`/axes?${appQuery}`, '평가축'),
      get<ApiAxisSuggestion[]>(`/axis-suggestions?${axisSuggestionQuery}`, '평가축 후보'),
      get<ApiIssueSummary>(`/issues/summary?${appQuery}`, '이슈 요약'),
      get<ApiReport[]>(`/reports?${appQuery}`, '리포트'),
      get<ApiAnalysisRun[]>(`/analysis-runs?${appQuery}`, '분석 이력'),
      loadModelOptions(warnings)
    ]);

    dashboard = dashboardResult ?? emptyDashboard;
    languages = Array.isArray(languagesResult) ? languagesResult : [];
    events = Array.isArray(eventsResult) ? eventsResult : [];
    timelineRows = normalizeTimeline(timelineResult);
    evidenceItems = Array.isArray(evidenceResult) ? evidenceResult : [];
    claims = Array.isArray(claimsResult) ? claimsResult : [];
    issues = Array.isArray(issuesResult) ? issuesResult : [];
    axes = Array.isArray(axesResult) ? axesResult : [];
    axisSuggestions = Array.isArray(axisSuggestionsResult) ? axisSuggestionsResult : [];
    issueSummary = issueSummaryResult ?? {
      issues: 0,
      confirmed_issues: 0,
      needs_review_issues: 0,
      strength_issues: 0,
      diagnostic_issues: 0,
      issue_evidence_items: 0,
      issue_units: 0,
      quarantined_units: 0,
      issue_coverage: null
    };
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

    if (issues.length > 0) {
      if (!issues.some((issue) => String(issue.id) === activeIssue)) {
        activeIssue = String(issues[0].id);
      }
      await loadIssueEvidence(activeIssue);
    } else {
      activeIssue = '';
      issueEvidenceItems = [];
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
    claims = [];
    issues = [];
    axes = [];
    axisSuggestions = [];
    axisState = '백엔드 연결 후 평가축을 관리할 수 있습니다.';
    issueSummary = {
      issues: 0,
      confirmed_issues: 0,
      needs_review_issues: 0,
      strength_issues: 0,
      diagnostic_issues: 0,
      issue_evidence_items: 0,
      issue_units: 0,
      quarantined_units: 0,
      issue_coverage: null
    };
    activeIssue = '';
    issueEvidenceItems = [];
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
          llm_provider: analysisOptions.llm_provider,
          llm_model: analysisOptions.llm_model,
          min_quality_score: Number(analysisOptions.min_quality_score),
          exclude_duplicate_evidence: analysisOptions.exclude_duplicate_evidence,
          use_lmstudio_labels: analysisOptions.use_lmstudio_labels,
          max_clusters: Number(analysisOptions.max_clusters),
          evidence_per_claim: Number(analysisOptions.evidence_per_claim)
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
      analysisState = '/api/analysis-runs가 아직 응답하지 않습니다. 현재 화면은 기존 자동 묶음과 근거를 표시합니다.';
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
      const sampleTypes = cluster.tone === 'bad' ? ['complaint', 'representative', 'recent'] : cluster.tone === 'good' ? ['praise', 'complaint', 'recent'] : ['representative', 'complaint', 'praise'];
      const batches = await Promise.all(
        sampleTypes.map((sample) =>
          requestJson<ApiReview[]>(`/clusters/${clusterId}/reviews?sample=${sample}&limit=5`).catch(() => [])
        )
      );
      const seen = new Set<string>();
      const reviews = batches
        .flat()
        .filter((review) => {
          const key = normalizeVisibleText(review.review);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .slice(0, 10);
      selectedReviews = reviews.map(mapApiReview);
      clusters = clusters.map((item) => (item.id === clusterId ? { ...item, samples: selectedReviews } : item));
    } catch {
      selectedReviews = [];
    }
  }

  async function loadIssueEvidence(issueId: string | number) {
    activeIssue = String(issueId);
    issueEvidenceItems = [];
    issueEvidenceFilter = 'match';
    issueEvidenceQuery = '';
    if (!issueId) return;
    try {
      issueEvidenceItems = await requestJson<ApiIssueEvidence[]>(`/issues/${issueId}/evidence?limit=24`);
      const stats = buildIssueEvidenceStats(issueEvidenceItems);
      issueEvidenceFilter =
        stats.match > 0 ? 'match' : stats.unverified > 0 ? 'unverified' : stats.partial > 0 ? 'partial' : stats.reject > 0 ? 'reject' : 'all';
    } catch {
      issueEvidenceItems = [];
    }
  }

  async function approveAxisSuggestion(suggestionId: number) {
    axisState = '평가축 후보 승인 중';
    try {
      await requestJson<ApiAxisSuggestion>(`/axis-suggestions/${suggestionId}/approve`, { method: 'POST' });
      axisState = '평가축으로 승인했습니다. 다음 분석부터 적용됩니다.';
      await loadApiData(selectedAppId);
    } catch {
      axisState = '평가축 후보 승인에 실패했습니다.';
    }
  }

  async function ignoreAxisSuggestion(suggestionId: number) {
    axisState = '평가축 후보 제외 중';
    try {
      await requestJson<ApiAxisSuggestion>(`/axis-suggestions/${suggestionId}/ignore`, { method: 'POST' });
      axisState = '후보를 제외했습니다.';
      await loadApiData(selectedAppId);
    } catch {
      axisState = '평가축 후보 제외에 실패했습니다.';
    }
  }

  async function mergeAxisSuggestion(suggestion: ApiAxisSuggestion) {
    if (!suggestion.target_axis_id) return;
    axisState = '기존 평가축에 병합 중';
    try {
      await requestJson<ApiAxisSuggestion>(`/axis-suggestions/${suggestion.id}/merge?target_axis_id=${suggestion.target_axis_id}`, {
        method: 'POST'
      });
      axisState = '기존 평가축에 병합했습니다. 다음 분석에서 같은 축으로 더 안정적으로 묶입니다.';
      await loadApiData(selectedAppId);
    } catch {
      axisState = '평가축 병합에 실패했습니다.';
    }
  }

  async function keepAxisSuggestion(suggestionId: number) {
    axisState = '일회성 인사이트로 보관 중';
    try {
      await requestJson<ApiAxisSuggestion>(`/axis-suggestions/${suggestionId}/keep`, { method: 'POST' });
      axisState = '평가축으로 늘리지는 않고 일회성 인사이트로 보관했습니다.';
      await loadApiData(selectedAppId);
    } catch {
      axisState = '일회성 보관에 실패했습니다.';
    }
  }

  async function toggleRawAxisSuggestions() {
    showRawAxisSuggestions = !showRawAxisSuggestions;
    axisState = showRawAxisSuggestions ? '진단용 원시 후보까지 불러오는 중' : '품질 통과 후보만 불러오는 중';
    await loadApiData(selectedAppId);
  }

  async function toggleAxis(axis: ApiAxis) {
    const nextStatus = axis.status === 'active' ? 'disabled' : 'active';
    axisState = `${axis.label} 상태 변경 중`;
    try {
      await requestJson<ApiAxis>(`/axes/${axis.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus })
      });
      axisState = nextStatus === 'active' ? '평가축을 활성화했습니다.' : '평가축을 비활성화했습니다.';
      await loadApiData(selectedAppId);
    } catch {
      axisState = '평가축 상태 변경에 실패했습니다.';
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
          summary: buildGeneratedSummary(dashboard, issues, issueEvidenceItems.length || evidenceItems.length, clusters),
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
    window.requestAnimationFrame(() => {
      document.querySelector('.content')?.scrollTo({ top: 0, behavior: 'auto' });
    });
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
      issues: numberFrom(game.issue_count),
      confirmedIssues: numberFrom(game.confirmed_issue_count),
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

  function filterIssues(issueItems: ApiIssue[], queryValue: string, statusFilter: IssueStatusFilter) {
    const q = queryValue.trim().toLowerCase();
    return issueItems
      .filter((issue) => {
        const text = `${issue.title} ${issue.summary} ${issue.aspect} ${issue.intent} ${(issue.top_terms ?? []).join(' ')}`.toLowerCase();
        const statusMatch = statusFilter === 'all' || issue.status === statusFilter;
        return statusMatch && (!q || text.includes(q));
      })
      .sort((a, b) => issuePriorityScore(b) - issuePriorityScore(a));
  }

  function filterIssueEvidence(items: ApiIssueEvidence[], verdictFilter: IssueEvidenceFilter, queryValue: string) {
    const q = normalizeVisibleText(queryValue);
    return items.filter((item) => {
      const verdict = issueEvidenceVerdict(item.verifier_verdict);
      const verdictMatch = verdictFilter === 'all' || verdictFilter === verdict;
      const haystack = normalizeVisibleText(
        `${item.summary_ko ?? ''} ${item.subissue ?? ''} ${item.quote} ${item.review_text ?? ''} ${item.language ?? ''} ${item.evidence_role}`
      );
      return verdictMatch && (!q || haystack.includes(q));
    });
  }

  function issueEvidenceVerdict(value?: string | null): IssueEvidenceFilter {
    if (value === 'match' || value === 'partial' || value === 'reject') return value;
    return 'unverified';
  }

  function buildIssueEvidenceStats(items: ApiIssueEvidence[]) {
    const stats = {
      all: items.length,
      match: 0,
      partial: 0,
      reject: 0,
      unverified: 0,
      verified: 0,
      uniqueReviews: new Set<string>(),
      recommended: 0,
      notRecommended: 0,
      languageCounts: new Map<string, number>()
    };
    for (const item of items) {
      const verdict = issueEvidenceVerdict(item.verifier_verdict);
      if (verdict === 'match') stats.match += 1;
      if (verdict === 'partial') stats.partial += 1;
      if (verdict === 'reject') stats.reject += 1;
      if (verdict === 'unverified') stats.unverified += 1;
      if (verdict !== 'unverified') stats.verified += 1;
      if (item.review_id) stats.uniqueReviews.add(item.review_id);
      if (item.voted_up === true) stats.recommended += 1;
      if (item.voted_up === false) stats.notRecommended += 1;
      const language = item.language ?? 'unknown';
      stats.languageCounts.set(language, (stats.languageCounts.get(language) ?? 0) + 1);
    }
    const dominant = [...stats.languageCounts.entries()].sort((a, b) => b[1] - a[1])[0] ?? null;
    return {
      all: stats.all,
      match: stats.match,
      partial: stats.partial,
      reject: stats.reject,
      unverified: stats.unverified,
      verified: stats.verified,
      uniqueReviews: stats.uniqueReviews.size,
      recommended: stats.recommended,
      notRecommended: stats.notRecommended,
      matchRate: stats.verified ? stats.match / stats.verified : null,
      languageCount: stats.languageCounts.size,
      dominantLanguage: dominant?.[0] ?? null,
      dominantLanguageCount: dominant?.[1] ?? 0,
      dominantLanguageShare: dominant && stats.all ? dominant[1] / stats.all : null
    };
  }

  function buildIssueEvidenceSubissues(items: ApiIssueEvidence[]) {
    const rows = new Map<string, { label: string; count: number; match: number; partial: number; reject: number; sample: string }>();
    for (const item of items) {
      const rawLabel = displayEvidenceSubissue(item) || item.summary_ko || trimText(item.quote, 48);
      const label = trimText(rawLabel, 64);
      const current = rows.get(label) ?? { label, count: 0, match: 0, partial: 0, reject: 0, sample: item.summary_ko || item.quote };
      current.count += 1;
      const verdict = issueEvidenceVerdict(item.verifier_verdict);
      if (verdict === 'match') current.match += 1;
      if (verdict === 'partial') current.partial += 1;
      if (verdict === 'reject') current.reject += 1;
      rows.set(label, current);
    }
    return [...rows.values()].sort((a, b) => b.count - a.count).slice(0, 6);
  }

  function displayEvidenceSubissue(item: ApiIssueEvidence) {
    const value = (item.subissue ?? '').trim();
    const summary = (item.summary_ko ?? '').trim();
    const safeSummary = summary && summary.length <= 42 && !summary.includes('[') ? summary : '';
    if (!value) return safeSummary || `${steamLanguageLabel(item.language ?? 'unknown')} 원문 의견`;
    const lowerValue = value.toLowerCase();
    const looksLikeRawQuote = value.length > 42 || lowerValue.includes('[spoiler') || value.includes('[');
    if (looksLikeRawQuote) return safeSummary || `${steamLanguageLabel(item.language ?? 'unknown')} 원문 의견`;
    return value;
  }

  function issueEvidenceFilterCount(filter: IssueEvidenceFilter, stats: ReturnType<typeof buildIssueEvidenceStats>) {
    if (filter === 'match') return stats.match;
    if (filter === 'partial') return stats.partial;
    if (filter === 'reject') return stats.reject;
    if (filter === 'unverified') return stats.unverified;
    return stats.all;
  }

  function issueEvidenceStrengthLabel(stats: ReturnType<typeof buildIssueEvidenceStats>) {
    if (stats.match >= 5 && (stats.matchRate ?? 0) >= 0.7) return '높음';
    if (stats.match >= 2 || stats.partial >= 3) return '중간';
    if (stats.all > 0) return '낮음';
    return '대기';
  }

  function issueStrengthLabel(issue: ApiIssue) {
    const matchEvidence = issue.match_evidence_count ?? 0;
    const connectedEvidence = issue.evidence_count ?? 0;
    if (matchEvidence >= 5) return '높음';
    if (matchEvidence >= 2) return '중간';
    if (connectedEvidence >= 3) return '미검증';
    return '낮음';
  }

  function issueEvidenceLabel(issue: ApiIssue) {
    const total = issue.evidence_count ?? 0;
    const match = issue.match_evidence_count ?? 0;
    const partial = issue.partial_evidence_count ?? 0;
    const reject = issue.reject_evidence_count ?? 0;
    const unverified = issue.unverified_evidence_count ?? Math.max(0, total - match - partial - reject);
    if (match > 0) {
      const audit = partial + reject ? ` · 부분/제외 ${formatCount(partial + reject)}` : '';
      return `검증 통과 ${formatCount(match)} / 연결 ${formatCount(total)}${audit}`;
    }
    if (unverified > 0) return `미검증 연결 ${formatCount(unverified)} / 전체 ${formatCount(total)}`;
    return `연결 근거 ${formatCount(total)}`;
  }

  function plannerActionLabel(issue: ApiIssue) {
    if (issue.intent === 'praise') return '유지/확장/홍보 후보';
    if (issue.intent === 'request') return '수요와 범위 검토';
    if (issue.intent === 'bug') return '재현과 수정 검토';
    if (issue.intent === 'complaint') return '수정/완화 검토';
    return '관찰 후보';
  }

  function planningDecision(issue: ApiIssue): PlanningDecision {
    if (issue.intent === 'bug') {
      return {
        id: 'fix',
        label: '고칠 것',
        verb: '재현/수정',
        detail: '버그 근거를 재현 조건, 영향 범위, 수정 우선순위로 좁힙니다.',
        tone: 'bad'
      };
    }
    if (issue.intent === 'complaint') {
      return {
        id: 'fix',
        label: '고칠 것',
        verb: '수정/완화',
        detail: '불만 근거를 패치 후보와 완화 메시지로 나눠 검토합니다.',
        tone: 'bad'
      };
    }
    if (issue.intent === 'request') {
      return {
        id: 'expand',
        label: '확장할 것',
        verb: '수요/범위 검토',
        detail: '반복 요청이 실제 기능 범위나 후속 콘텐츠로 이어질지 확인합니다.',
        tone: 'mixed'
      };
    }
    if (issue.intent === 'praise' || issue.status === 'strength') {
      return {
        id: 'preserve',
        label: '유지할 것',
        verb: '보존/확장/홍보',
        detail: '강점 근거를 유지할 재미, 확장 축, 스토어 문구 후보로 분리합니다.',
        tone: 'good'
      };
    }
    return {
      id: 'communicate',
      label: '소통할 것',
      verb: '메시지 정리',
      detail: '확신이 낮은 신호는 근거를 더 확인한 뒤 외부 문구로 옮깁니다.',
      tone: 'mixed'
    };
  }

  function buildPlanningLanes(issueItems: ApiIssue[]): PlanningLaneView[] {
    const sorted = [...issueItems].sort((a, b) => issuePriorityScore(b) - issuePriorityScore(a));
    const buckets = new Map<PlanningLaneId, ApiIssue[]>([
      ['fix', []],
      ['preserve', []],
      ['expand', []],
      ['communicate', []]
    ]);
    for (const issue of sorted) {
      const decision = planningDecision(issue);
      buckets.get(decision.id)?.push(issue);
      if (issue.intent === 'praise' || issue.status === 'strength') {
        buckets.get('communicate')?.push(issue);
      }
    }

    const laneDefs: Array<Pick<PlanningLaneView, 'id' | 'label' | 'tone'> & { empty: string; hint: string }> = [
      { id: 'fix', label: '고칠 것', tone: 'bad', empty: '수정 후보 대기', hint: '불만/버그 카드가 들어오면 표시됩니다.' },
      { id: 'preserve', label: '유지할 것', tone: 'good', empty: '강점 후보 대기', hint: '추천 리뷰의 강점 카드가 들어오면 표시됩니다.' },
      { id: 'expand', label: '확장할 것', tone: 'mixed', empty: '확장 요청 대기', hint: '요청 카드나 확장 후보가 들어오면 표시됩니다.' },
      { id: 'communicate', label: '소통할 것', tone: 'good', empty: '문구 소재 대기', hint: '강점 카드에서 마케팅/공지 소재를 고릅니다.' }
    ];

    return laneDefs.map((lane) => {
      const items = buckets.get(lane.id) ?? [];
      const topIssue = items[0];
      const topDecision = topIssue ? planningDecision(topIssue) : null;
      return {
        id: lane.id,
        label: lane.label,
        tone: lane.tone,
        count: items.length,
        title: topIssue?.title ?? lane.empty,
        detail: topIssue
          ? `${formatCount(topIssue.unique_review_count)}개 리뷰 · ${issueEvidenceLabel(topIssue)}`
          : lane.hint
      };
    });
  }

  function languageDominanceLabel(stats: ReturnType<typeof buildIssueEvidenceStats>) {
    if (!stats.dominantLanguage || !stats.dominantLanguageShare) return '언어 근거 없음';
    const label = `${steamLanguageLabel(stats.dominantLanguage)} ${formatPercent(stats.dominantLanguageShare)}`;
    return stats.dominantLanguageShare >= 0.7 ? `${label} 편중` : label;
  }

  function issuePriorityScore(issue: ApiIssue) {
    const statusWeight =
      issue.status === 'confirmed' ? 4 : issue.status === 'strength' ? 3 : issue.status === 'needs_review' ? 2 : 1;
    return statusWeight * 1_000_000 + issue.priority_score * 1000 + issue.unique_review_count;
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
    setTab('workbench');
  }

  async function openGame(game: GameProject) {
    selectedGameId = game.id;
    await loadApiData(game.appId);
    setTab('workbench');
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
    if (action === 'analyze') return '수집된 리뷰를 분석하세요.';
    return '분석 작업대에서 최신 반응을 검토하세요.';
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
    const keywords = Array.isArray(cluster.top_keywords) ? cluster.top_keywords : [];
    const matchedTerms = Array.isArray(cluster.matched_terms) ? cluster.matched_terms : [];
    const labelWarnings = Array.isArray(cluster.label_warnings) ? cluster.label_warnings : [];
    const insight = cluster.insight ?? null;
    const keywordMethod = cluster.keyword_method ?? null;
    const insightSource = insight?.source ?? null;
    const insightModel = insight?.model ?? null;
    return {
      id: String(cluster.id),
      title: cluster.label || insight?.title || `Cluster ${cluster.id}`,
      count: formatCount(cluster.review_count),
      countValue: cluster.review_count,
      tone,
      description: cluster.summary || insight?.summary || '아직 요약이 없습니다.',
      tags: [
        cluster.language ? steamLanguageLabel(cluster.language) : '전체 언어',
        sentimentLabel(cluster.sentiment),
        `추천율 ${formatPercent(cluster.positive_ratio ?? 0)}`,
        clusterLabelSourceLabel(cluster.label_source ?? null)
      ].concat(matchedTerms.slice(0, 2), keywords.slice(0, 2)),
      backend: true,
      samples: [],
      positiveRatio: ratioMaybe(cluster.positive_ratio) ?? null,
      keywords,
      keywordMethod,
      qualityWarning: cluster.quality_warning ?? null,
      labelSource: cluster.label_source ?? null,
      labelConfidence: cluster.label_confidence ?? null,
      labelWarnings,
      matchedThemeKey: cluster.matched_theme_key ?? null,
      matchedTerms,
      insightSource,
      insightModel,
      insight
    };
  }

  function clusterLabelSourceLabel(source: string | null | undefined) {
    if (source === 'game_theme') return '게임별 테마';
    if (source === 'common_theme') return '공통 테마';
    if (source === 'keyword') return '키워드 진단';
    if (source === 'fallback') return '보수적 fallback';
    return '출처 미상';
  }

  function insightSourceLabel(source: string | null) {
    if (source === 'lm_studio') return 'LM Studio';
    if (source === 'lm_studio_issue_verifier') return 'LM Studio 근거 확인';
    if (source === 'deterministic') return '규칙 기반';
    if (source === 'deterministic_issue_rules') return '이슈 규칙';
    return '미상';
  }

  function issueStatusLabel(status: string) {
    if (status === 'confirmed') return '근거 충분';
    if (status === 'needs_review') return '검토';
    if (status === 'strength') return '활용 포인트';
    if (status === 'diagnostic') return '진단';
    return status || '미상';
  }

  function issueIntentLabel(intent: string) {
    if (intent === 'complaint') return '불만';
    if (intent === 'request') return '요청';
    if (intent === 'bug') return '버그';
    if (intent === 'praise') return '강점';
    return '기타';
  }

  function issueTone(issue: ApiIssue): Tone {
    if (issue.status === 'confirmed' || issue.intent === 'bug' || issue.intent === 'complaint') return 'bad';
    if (issue.status === 'strength' || issue.intent === 'praise') return 'good';
    return 'mixed';
  }

  function issueAspectLabel(value: string) {
    const labels: Record<string, string> = {
      performance: '성능/안정성',
      balance: '밸런스/RNG',
      progression: '난이도/진척',
      content_repetition: '반복성/콘텐츠',
      ui_onboarding: 'UI/온보딩',
      content_missing: '누락/비교',
      cheating: '치터/안티치트',
      matchmaking: '매치메이킹',
      server_netcode: '서버/히트레지',
      csgo_regression: 'CS:GO 비교',
      toxicity: '팀원/소통/독성',
      deck_synergy: '조커/덱 시너지',
      rng_luck: 'RNG/운',
      stakes_progression: '스테이크/앤티',
      mobile_platform: '플랫폼/휴대성',
      gambling_framing: '중독/도박 프레이밍',
      story_logic: '스토리/세계관/엔딩',
      content_volume: '분량/완성도',
      localization_readability: '번역/가독성',
      update_completion: '업데이트/완성도',
      route_guidance: '분기/공략 의존',
      martial_story: '무협 서사',
      mystery_logic: '추리/재판/마법 규칙',
      chapter_replay: '챕터/회차 편의',
      character_voice: '캐릭터/연출',
      short_content: '짧은 분량',
      weapon_card_rng: '무기/카드 RNG',
      bleak_ending_tone: '엔딩 톤'
    };
    return labels[value] ?? value;
  }

  function axisScopeLabel(value: string) {
    if (value === 'common') return '공통';
    if (value === 'genre') return '장르';
    if (value === 'game') return '게임별';
    return value || '미상';
  }

  function axisStatusLabel(value: string) {
    if (value === 'active') return '활성';
    if (value === 'disabled') return '비활성';
    if (value === 'candidate') return '후보';
    if (value === 'pending') return '검토 대기';
    if (value === 'approved') return '승인됨';
    if (value === 'merged') return '병합됨';
    if (value === 'ignored') return '무시됨';
    if (value === 'kept') return '보관됨';
    return value || '미상';
  }

  function axisSuggestionKindLabel(value?: string) {
    if (value === 'merge_candidate') return '기존 축 병합 후보';
    if (value === 'axis_candidate') return '새 게임별 축 후보';
    if (value === 'one_off_insight') return '일회성 인사이트';
    if (value === 'raw_signal') return '진단용 원시 신호';
    return '미분류 주장';
  }

  function axisSuggestionGateLabel(value?: string) {
    if (value === 'pass') return '품질 통과';
    if (value === 'fail') return '숨김 권장';
    return '검토 필요';
  }

  function axisSuggestionTargetLabel(suggestion: ApiAxisSuggestion) {
    const axis = axes.find((item) => item.id === suggestion.target_axis_id);
    return axis ? axis.label : '기존 평가축';
  }

  function languageCountLabel(value?: Record<string, number>) {
    if (!value || Object.keys(value).length === 0) return '언어 정보 없음';
    return Object.entries(value)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([language, count]) => `${steamLanguageLabel(language)} ${formatCount(count)}`)
      .join(' · ');
  }

  function verifierLabel(value?: string | null) {
    if (value === 'match') return '검증 통과';
    if (value === 'partial') return '부분 관련';
    if (value === 'reject') return '제외 근거';
    if (value === 'missing') return '검증 누락';
    return '자동 근거';
  }

  function verifierTone(value?: string | null): Tone {
    if (value === 'match') return 'good';
    if (value === 'reject') return 'bad';
    return 'mixed';
  }

  function mapApiReview(review: ApiReview): ReviewSample {
    return {
      language: steamLanguageLabel(review.language),
      playtime: formatPlaytime(review.playtime_at_review),
      reaction: review.voted_up ? '추천' : '비추천',
      reactionTone: review.voted_up ? 'good' : 'bad',
      text: review.review,
      score: formatPercent(review.cluster_score ?? review.weighted_vote_score),
      quality: review.quality_score === null || review.quality_score === undefined ? '미상' : formatPercent(review.quality_score),
      flags: Array.isArray(review.quality_flags) ? review.quality_flags : [],
      duplicateCount: numberFrom(review.duplicate_count)
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
      ['근거 충분', formatCount(summary.confirmed_issues ?? 0), summary.issues ? `전체 ${formatCount(summary.issues)}개` : '분석 대기'],
      ['근거 문장', formatCount(summary.issue_evidence_items ?? summary.evidence_items), summary.issue_evidence_items ? '인사이트 근거' : sourceLabel]
    ];
  }

  function buildLibraryMetrics(projects: GameProject[]): string[][] {
    const reviewTotal = projects.reduce((total, game) => total + game.reviewCount, 0);
    const analyzed = projects.filter((game) => game.lastAnalysis).length;
    const waiting = projects.filter((game) => !game.lastAnalysis).length;
    return [
      ['관리 게임', formatCount(projects.length), '로컬 라이브러리'],
      ['저장 리뷰', formatCount(reviewTotal), '게임별 app_id 기준'],
      ['분석 완료', formatCount(analyzed), `${formatCount(waiting)}개 대기`],
      ['근거 충분', formatCount(projects.reduce((total, game) => total + game.confirmedIssues, 0)), '게임별 최신 분석']
    ];
  }

  function buildSelectedGameFacts(game: GameProject): string[][] {
    return [
      ['Steam App ID', game.appId, '수집 키'],
      ['리뷰 수', formatCount(game.reviewCount), game.lastSync ? latestLabel(game.lastSync) : '수집 전'],
      ['추천율', formatPercent(game.positiveRatio), `${formatCount(game.languages)}개 언어`],
      ['인사이트 보드', formatCount(game.issues), game.confirmedIssues ? `${formatCount(game.confirmedIssues)}개 근거 충분` : '근거 충분 카드 없음']
    ];
  }

  function buildSelectedGameSteps(game: GameProject): string[][] {
    return [
      ['1', '게임 등록', `Steam app/${game.appId} · ${game.name}`, 'good'],
      ['2', '리뷰 수집', game.lastSync ? latestLabel(game.lastSync) : '아직 수집하지 않음', game.lastSync ? 'good' : 'mixed'],
      ['3', '분석 실행', game.lastAnalysis ? latestLabel(game.lastAnalysis) : '분석 대기', game.lastAnalysis ? 'good' : 'mixed'],
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

  function buildIssueMetrics(summary: ApiIssueSummary, dashboardSummary: ApiDashboard): string[][] {
    const coverage = summary.issue_coverage ?? dashboardSummary.issue_coverage ?? null;
    return [
      ['근거 충분', formatCount(summary.confirmed_issues), summary.confirmed_issues ? '메인 보드' : '근거 부족'],
      ['검토 필요', formatCount(summary.needs_review_issues), '사람 확인 필요'],
      ['근거 문장', formatCount(summary.issue_evidence_items || dashboardSummary.issue_evidence_items || 0), '중복 제거 후'],
      ['불만 커버리지', coverage === null ? '미상' : formatPercent(coverage), coverage !== null && coverage < 0.6 ? '부분 분석' : '분석 범위']
    ];
  }

  function buildAxisMetrics(axisItems: ApiAxis[], suggestions: ApiAxisSuggestion[], issueItems: ApiIssue[]): string[][] {
    const gameAxes = axisItems.filter((axis) => axis.scope === 'game');
    const commonAxes = axisItems.filter((axis) => axis.scope !== 'game');
    const usedAspects = new Set(issueItems.map((issue) => issue.aspect));
    const usedAxes = axisItems.filter((axis) => usedAspects.has(axis.key));
    return [
      ['활성 평가축', formatCount(axisItems.length), `공통 ${formatCount(commonAxes.length)} · 게임별 ${formatCount(gameAxes.length)}`],
      ['이번 분석 사용', formatCount(usedAxes.length), usedAxes.length ? usedAxes.slice(0, 3).map((axis) => axis.label).join(' · ') : '분석 대기'],
      ['미분류 주장', formatCount(suggestions.length), suggestions.length ? '병합/보관 필요' : '대기열 없음'],
      ['하드코딩 탈피', axisItems.length ? 'DB 관리 중' : '초기화 필요', axisItems.length ? '준비' : '대기']
    ];
  }

  function buildIssueAuditRows(summary: ApiIssueSummary, dashboardSummary: ApiDashboard): string[][] {
    const coverage = summary.issue_coverage ?? dashboardSummary.issue_coverage ?? null;
    const noiseRatio = summary.issue_units ? summary.quarantined_units / summary.issue_units : null;
    return [
      [
        '표본 크기',
        `${formatCount(dashboardSummary.total_reviews)}개 리뷰`,
        dashboardSummary.total_reviews >= 1000 ? '충분' : '탐색',
        dashboardSummary.total_reviews >= 1000 ? 'good' : 'mixed'
      ],
      [
        '이슈 커버리지',
        coverage === null ? '비추천 리뷰가 없거나 미계산입니다.' : `비추천 리뷰 중 ${formatPercent(coverage)}가 이슈 후보에 연결됨`,
        coverage !== null && coverage >= 0.6 ? '넓음' : '부분',
        coverage !== null && coverage >= 0.6 ? 'good' : 'mixed'
      ],
      [
        '노이즈 격리',
        noiseRatio === null ? '문장 단위 분석 전입니다.' : `${formatPercent(noiseRatio)} 문장을 저정보/밈/중복 후보로 격리`,
        noiseRatio === null ? '대기' : '확인',
        noiseRatio === null ? 'mixed' : 'good'
      ]
    ];
  }

  function buildRoleReadinessRows(
    summary: ApiDashboard,
    evidence: ApiEvidence[],
    languageItems: ApiLanguage[],
    runs: ApiAnalysisRun[],
    eventItems: ApiEvent[],
    reportItems: ApiReport[]
  ): string[][] {
    const latestRun = runs[0] ?? null;
    return [
      [
        '데이터 사이언티스트',
        `${formatCount(summary.total_reviews)}개 리뷰, ${formatCount(languageItems.length || summary.languages)}개 언어, ${latestRun ? analysisMethodLabel(latestRun) : '분석 이력 없음'}`,
        summary.total_reviews >= 1000 && latestRun ? '사용 가능' : '보강',
        summary.total_reviews >= 1000 && latestRun ? 'good' : 'mixed'
      ],
      [
        '기획자',
        `${formatCount(summary.confirmed_issues ?? 0)}개 근거 충분 카드와 ${formatCount(summary.issue_evidence_items ?? evidence.length)}개 근거 문장을 우선 검토할 수 있습니다.`,
        (summary.confirmed_issues ?? 0) && (summary.issue_evidence_items ?? evidence.length) ? '사용 가능' : '보강',
        (summary.confirmed_issues ?? 0) && (summary.issue_evidence_items ?? evidence.length) ? 'good' : 'mixed'
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
      ['리뷰 묶음', formatCount(clusterItems.length), sourceLabel],
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
    return [['데이터 대기', '자동 묶음 결과가 들어오면 표시됩니다.', '대기', 'flat']];
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

  function buildClaimRows(claimItems: ApiClaim[], evidence: ApiEvidence[]): string[][] {
    const evidenceByClaim = new Map<number, number>();
    for (const item of evidence) {
      if (item.claim_id === null || item.claim_id === undefined) continue;
      evidenceByClaim.set(item.claim_id, (evidenceByClaim.get(item.claim_id) ?? 0) + 1);
    }
    const rows = claimItems.slice(0, 8).map((claim) => [
      claimTypeLabel(claim.claim_type),
      claim.claim_text,
      `${formatPercent(claim.confidence)} 신뢰 · 근거 ${formatCount(evidenceByClaim.get(claim.id) ?? 0)}개`,
      claim.claim_type === 'complaint' ? 'bad' : claim.claim_type === 'praise' ? 'good' : 'mixed'
    ]);
    if (rows.length > 0) return rows;
    return [['주장 대기', '분석 실행 후 주장-근거 구조가 표시됩니다.', '대기', 'mixed']];
  }

  function buildEvidenceTableRows(items: ApiEvidence[]): string[][] {
    return items.slice(0, 8).map((item) => [
      evidenceTypeLabel(item.evidence_type),
      trimText(item.quote, 88),
      item.claim_text ? trimText(item.claim_text, 54) : item.cluster_id ? clusterTitle(item.cluster_id) : '미연결',
      item.quality_score === null || item.quality_score === undefined ? '품질 미상' : formatPercent(item.quality_score)
    ]);
  }

  function buildReportBlocks(
    report: ApiReport | null,
    summary: ApiDashboard,
    issueItems: ApiIssue[],
    clusterItems: ClusterView[],
    evidenceCount: number
  ): string[][] {
    if (report) {
      return [
        ['최근 리포트', report.summary],
        ['생성 시각', `${formatDateTime(report.created_at)} · ${report.title}`],
        ['필터', Object.keys(report.filters ?? {}).length ? JSON.stringify(report.filters) : '필터 없음']
      ];
    }
    const topIssue = issueItems.find((issue) => issue.status === 'confirmed') ?? issueItems.find((issue) => issue.status === 'needs_review');
    const topStrength = issueItems.find((issue) => issue.status === 'strength');
    const topBad = clusterItems.find((cluster) => cluster.tone === 'bad');
    return [
      ['요약', buildGeneratedSummary(summary, issueItems, evidenceCount, clusterItems)],
      ['활용 포인트', topStrength ? `${topStrength.title}: ${topStrength.summary}` : '검증된 강점이 아직 없습니다.'],
      ['불만', topIssue ? `${topIssue.title}: ${topIssue.summary}` : topBad ? `${topBad.title}: ${topBad.description}` : '비추천 연결 이슈가 아직 없습니다.'],
      ['다음 액션', evidenceCount ? '근거 문장을 확인한 뒤 리포트 문구를 확정하세요.' : '인사이트 보드와 근거 API가 준비되면 액션 항목을 구체화합니다.']
    ];
  }

  function buildGeneratedSummary(
    summary: ApiDashboard,
    issueItems: ApiIssue[],
    evidenceCount: number,
    clusterItems: ClusterView[] = []
  ) {
    const topIssue = issueItems.find((issue) => issue.status === 'confirmed') ?? issueItems.find((issue) => issue.status === 'needs_review');
    const topStrength = issueItems.find((issue) => issue.status === 'strength');
    const fallbackBad = clusterItems.find((cluster) => cluster.tone === 'bad');
    const signalText = issueItems.length
      ? `${topStrength ? `강점 신호는 "${topStrength.title}"이고, ` : ''}${
          topIssue ? `먼저 볼 이슈는 "${topIssue.title}"입니다. ` : '근거 충분 이슈는 아직 충분하지 않습니다. '
        }`
      : `${fallbackBad ? `기존 자동 묶음 기준 검토 신호는 "${fallbackBad.title}"입니다. ` : '이슈 보드 결과는 아직 없습니다. '}`;
    return `현재 ${formatCount(summary.total_reviews)}개 리뷰 기준 추천율은 ${formatPercent(summary.positive_ratio)}입니다. ${
      signalText
    }${evidenceCount ? `근거 ${formatCount(evidenceCount)}개가 연결되어 있습니다.` : '근거 API 데이터는 아직 없습니다.'}`;
  }

  function buildMarketingBriefRows(issueItems: ApiIssue[], selectedEvidence: ApiIssueEvidence[]): string[][] {
    const strengths = issueItems
      .filter((issue) => issue.intent === 'praise' || issue.status === 'strength')
      .sort((a, b) => issuePriorityScore(b) - issuePriorityScore(a));
    const topStrength = strengths[0];
    const reusableQuote = selectedEvidence.find(
      (item) => item.voted_up === true && issueEvidenceVerdict(item.verifier_verdict) !== 'reject'
    );
    const riskText = selectedEvidence.some((item) => issueEvidenceVerdict(item.verifier_verdict) === 'reject')
      ? '제외 근거가 섞여 있으므로 외부 문구로 쓰기 전 원문을 다시 확인하세요.'
      : '검증 통과 근거와 전체 원문을 확인한 뒤 외부 문구로 옮기세요.';

    return [
      [
        '유지할 재미',
        topStrength ? `${topStrength.title}: ${trimText(topStrength.summary, 86)}` : '강점 카드가 아직 없습니다.',
        topStrength ? issueEvidenceLabel(topStrength) : '분석 대기'
      ],
      [
        '홍보 소재',
        topStrength
          ? trimText(topStrength.recommended_action ?? '강점 evidence에서 스토어/패치노트 문구 후보를 고르세요.', 96)
          : '추천 리뷰 기반 활용 포인트가 생기면 표시됩니다.',
        topStrength ? plannerActionLabel(topStrength) : '대기'
      ],
      [
        '유저 표현 후보',
        reusableQuote ? trimText(reusableQuote.summary_ko || reusableQuote.quote, 96) : '인사이트 보드에서 강점 카드를 선택하면 후보 문장이 표시됩니다.',
        reusableQuote ? verifierLabel(reusableQuote.verifier_verdict) : '선택 필요'
      ],
      ['과장 주의', riskText, '원문 대조']
    ];
  }

  function buildInspectorRows(summary: ApiDashboard, evidenceCount: number): string[][] {
    return [
      ['데이터 최신성', latestLabel(summary.latest_review_at), summary.latest_review_at ? '확인' : '대기', summary.latest_review_at ? 'good' : 'mixed'],
      ['표본 크기', `${formatCount(summary.total_reviews)}개 리뷰`, summary.total_reviews > 0 ? '사용 가능' : '대기', summary.total_reviews > 0 ? 'good' : 'mixed'],
      ['근거 확인', `${formatCount(evidenceCount)}개 근거`, evidenceCount ? '진행' : '대기', evidenceCount ? 'good' : 'mixed']
    ];
  }

  function buildPriorityItems(): string[][] {
    const rows = [...issues]
      .sort((a, b) => issuePriorityScore(b) - issuePriorityScore(a))
      .slice(0, 3)
      .map((issue, index) => [
        String(index + 1),
        issue.title,
        `${formatCount(issue.unique_review_count)}개 리뷰 · ${issueEvidenceLabel(issue)}`,
        plannerActionLabel(issue),
        issueTone(issue)
      ]);
    return rows.length
      ? rows
      : [['1', '인사이트 대기', '분석 실행 후 표시', '대기', 'mixed']];
  }

  function buildAiBrief(report: ApiReport | null, issueItems: ApiIssue[], summary: ApiDashboard) {
    if (report) return [report.summary];
    const sortedIssues = [...issueItems].sort((a, b) => issuePriorityScore(b) - issuePriorityScore(a));
    const topIssue = sortedIssues[0];
    return [
      `${formatCount(summary.total_reviews)}개 리뷰 기준 추천율은 ${formatPercent(summary.positive_ratio)}입니다.`,
      topIssue
        ? `가장 먼저 볼 인사이트는 "${topIssue.title}"입니다. 실제 리뷰 근거를 확인한 뒤 수정, 유지, 확장, 홍보 중 어떤 판단으로 이어갈지 정합니다.`
        : '인사이트 보드가 준비되면 AI 브리프가 더 구체화됩니다.'
    ];
  }

  function clusterTitle(clusterId: number | null) {
    if (clusterId === null) return '';
    return clusters.find((cluster) => cluster.id === String(clusterId))?.title ?? `Cluster ${clusterId}`;
  }

  function clusterSourceLabel(source: typeof clusterSource) {
    if (source === 'backend') return '백엔드 자동 묶음';
    if (source === 'sample') return '샘플 자동 묶음';
    return '자동 묶음 없음';
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
    if (value === 'pain_point') return '불만 근거';
    if (value === 'representative') return '대표 근거';
    if (value === 'mixed') return '혼합 근거';
    return value || '근거';
  }

  function claimTypeLabel(value: string) {
    if (value === 'complaint') return '불만 주장';
    if (value === 'praise') return '호평 주장';
    if (value === 'representative') return '대표 주장';
    return value || '주장';
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

  function normalizeVisibleText(value: string) {
    return value.toLowerCase().replace(/\s+/g, ' ').trim();
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

        <section class:active={activeTab === 'workbench'} class="tab-view" aria-label="분석 작업대">
          <section class="overview">
            <div class="panel game-summary">
              <div class="game-title">
                <div class="section-head">
                  <div>
                    <h1>{selectedGame.name} 리뷰 반응</h1>
                    <p>{buildGeneratedSummary(dashboard, issues, issueEvidenceItems.length || evidenceItems.length, clusters)}</p>
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
              <TopicPanel title="불만 토픽" subtitle="비추천 리뷰와 함께 나타나는 반복 의견입니다." topics={negativeTopics} />
              <TopicPanel title="호평 토픽" subtitle="추천 리뷰에서 반복적으로 나타난 강점입니다." topics={positiveTopics} />
            </div>
          </section>

          <section class="panel reviews">
            <div class="section-head">
              <div>
                <h2>최근 근거와 대표 리뷰</h2>
                <p>인사이트 근거와 최근 대표 리뷰를 함께 확인합니다.</p>
              </div>
            </div>
            <div class="quote-list">
              {#each issueEvidenceItems.slice(0, 3) as evidence}
                <article class="quote">
                  <p>{evidence.summary_ko || `“${evidence.quote}”`}</p>
                  <footer><span>{issueIntentLabel(evidence.evidence_role)}</span><span>{steamLanguageLabel(evidence.language ?? 'unknown')}</span><span>{verifierLabel(evidence.verifier_verdict)}</span></footer>
                </article>
              {:else}
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
                    <div class="empty-state">대표 리뷰가 없습니다. 인사이트를 선택하거나 리뷰를 갱신하세요.</div>
                  {/each}
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
            ['playtime_at_review', '플레이타임 구간 분석', '자동 묶음 샘플']
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
          <PageIntro title="분석 실행" subtitle="리뷰 묶기, 근거 연결, 이슈 카드 생성, AI 요약을 백엔드 작업으로 실행합니다.">
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
                <label class="field"><span>최소 반복 리뷰 수</span><input type="number" min="2" max="500" bind:value={analysisOptions.min_cluster_size} /></label>
                <label class="field"><span>LLM 공급자</span><select bind:value={analysisOptions.llm_provider}><option value="lm_studio">LM Studio</option><option value="openai">OpenAI</option><option value="claude">Claude</option><option value="none">사용 안 함</option></select></label>
                <label class="field"><span>LLM 모델</span><input bind:value={analysisOptions.llm_model} /></label>
                <label class="field"><span>품질 컷</span><input type="number" min="0" max="1" step="0.05" bind:value={analysisOptions.min_quality_score} /></label>
                <label class="field"><span>최대 의견 묶음</span><input type="number" min="1" max="120" bind:value={analysisOptions.max_clusters} /></label>
                <label class="field"><span>주장별 근거</span><input type="number" min="1" max="10" bind:value={analysisOptions.evidence_per_claim} /></label>
                <label class="field toggle-field"><span>AI 요약 생성</span><input type="checkbox" bind:checked={analysisOptions.generate_ai_summary} /></label>
                <label class="field toggle-field"><span>LM Studio 라벨</span><input type="checkbox" bind:checked={analysisOptions.use_lmstudio_labels} /></label>
                <label class="field toggle-field"><span>중복 근거 제외</span><input type="checkbox" bind:checked={analysisOptions.exclude_duplicate_evidence} /></label>
              </div>
            </section>
          </section>
          <AuditPanel title="분석 품질" rows={[
            ['자동 묶음', clusterSource === 'backend' ? '백엔드 분석 결과를 사용 중입니다.' : '분석 결과가 없거나 샘플 표시 중입니다.', clusterSource === 'backend' ? '확인' : '대기', clusterSource === 'backend' ? 'good' : 'mixed'],
            ['잡음 리뷰', '짧은 문장, 반복 문구, 오프토픽 처리는 백엔드 분석 정책에 따릅니다.', '정책', 'mixed'],
            ['사람 확인', `${formatCount(evidenceItems.length)}개 근거를 근거 확인 탭에서 확인할 수 있습니다.`, evidenceItems.length ? '진행' : '대기', evidenceItems.length ? 'good' : 'mixed']
          ]} />
          <SimpleTable
            title="최근 분석 이력"
            headers={['Run', '상태', '방식', '완료 시각']}
            rows={analysisRunRows.length ? analysisRunRows : [['대기', '분석 이력이 없습니다.', '분석 시작 후 표시', '대기']]}
          />
        </section>

        <section class:active={activeTab === 'insights'} class="tab-view" aria-label="인사이트 보드">
          <PageIntro title="인사이트 보드" subtitle="원문 근거가 붙은 문제, 요청, 유지할 강점을 함께 봅니다.">
            <span class="status">인사이트 {formatCount(filteredIssues.length)}/{formatCount(issues.length)}개</span>
          </PageIntro>
          <MetricStrip items={issueMetrics} />
          <AuditPanel title="인사이트 보드 신뢰도" rows={issueAuditRows} />
          <section class="planning-lanes" aria-label="기획 판단 요약">
            {#each planningLanes as lane}
              <article class={`planning-lane ${lane.tone}`}>
                <span>{lane.label}</span>
                <strong>{formatCount(lane.count)}</strong>
                <p>{lane.title}</p>
                <small>{lane.detail}</small>
              </article>
            {/each}
          </section>
          {#if issues.length === 0}
            <div class="empty-state">인사이트 보드가 없습니다. 분석 실행을 다시 시작하면 검증된 문제와 강점이 생성됩니다.</div>
          {:else}
            <section class="cluster-tools" aria-label="이슈 필터">
              <label class="library-search">
                <Search />
                <input bind:value={issueQuery} placeholder="이슈명, 요약, 측면, 키워드 검색" />
              </label>
              <div class="library-filters">
                {#each issueStatusOptions as filter}
                  <button
                    class="segment"
                    class:active={issueStatusFilter === filter.id}
                    type="button"
                    on:click={() => (issueStatusFilter = filter.id)}
                  >
                    {filter.label}
                  </button>
                {/each}
              </div>
            </section>
            <section class="issue-grid">
              {#each filteredIssues as issue}
                {@const decision = planningDecision(issue)}
                <button class="issue-card" class:active={activeIssue === String(issue.id)} type="button" on:click={() => loadIssueEvidence(issue.id)}>
                  <div class="issue-decision">
                    <span class={`decision-label ${decision.tone}`}>{decision.label}</span>
                    <span>{decision.verb}</span>
                  </div>
                  <header>
                    <div>
                      <h3>{issue.title}</h3>
                      <small>{issueAspectLabel(issue.aspect)} · {issueIntentLabel(issue.intent)}</small>
                    </div>
                    <span class={`sentiment ${issueTone(issue)}`}>{issueStatusLabel(issue.status)}</span>
                  </header>
                  <p>{issue.summary}</p>
                  <div class="issue-stats">
                    <span>{formatCount(issue.unique_review_count)}개 리뷰</span>
                    <span>{issueEvidenceLabel(issue)}</span>
                    <span>근거 강도 {issueStrengthLabel(issue)}</span>
                  </div>
                  <div class="cluster-tags">
                    {#each (issue.top_terms ?? []).slice(0, 4) as term}
                      <span class="cluster-tag">{term}</span>
                    {/each}
                  </div>
                  <span class="issue-card-action">세부 분석 열기</span>
                </button>
              {:else}
                <div class="empty-state">조건에 맞는 이슈가 없습니다.</div>
              {/each}
            </section>
            {#if selectedIssue}
              {@const selectedDecision = planningDecision(selectedIssue)}
              <section class="panel issue-detail">
                <div class="detail-head">
                  <div>
                    <h2>{selectedIssue.title}</h2>
                    <p>{selectedIssue.why_it_matters ?? selectedIssue.summary}</p>
                  </div>
                  <span class={`sentiment ${issueTone(selectedIssue)}`}>{issueStatusLabel(selectedIssue.status)}</span>
                </div>
                <div class="cluster-insight-grid">
                  <div><strong>영향 영역</strong><span>{issueAspectLabel(selectedIssue.aspect)}</span></div>
                  <div><strong>신호 유형</strong><span>{issueIntentLabel(selectedIssue.intent)}</span></div>
                  <div><strong>근거 강도</strong><span>{issueEvidenceStrengthLabel(issueEvidenceStats)}</span></div>
                  <div><strong>추천율</strong><span>{selectedIssue.positive_ratio === null || selectedIssue.positive_ratio === undefined ? '미상' : formatPercent(selectedIssue.positive_ratio)}</span></div>
                  <div><strong>검증 통과</strong><span>{formatCount(issueEvidenceStats.match)}개 · 일치율 {issueEvidenceStats.matchRate === null ? '미상' : formatPercent(issueEvidenceStats.matchRate)}</span></div>
                  <div><strong>언어 분포</strong><span>{languageDominanceLabel(issueEvidenceStats)}</span></div>
                  <div><strong>분석 방식</strong><span>{insightSourceLabel(selectedIssue.source ?? null)}{selectedIssue.model ? ` · ${selectedIssue.model}` : ''}</span></div>
                </div>
                <div class="method-note">
                  <Info />
                  <div>
                    <strong>{selectedDecision.label} · {selectedDecision.verb}</strong>
                    <span>{selectedIssue.recommended_action ?? selectedDecision.detail}</span>
                  </div>
                </div>
                <section class="evidence-brief" aria-label="인사이트 근거 탐색 요약">
                  <div>
                    <strong>하위 의견</strong>
                    <p>같은 카드 안에서 반복되는 세부 표현입니다. 칩을 보고 이 인사이트가 너무 넓게 묶였는지 판단합니다.</p>
                    <div class="subissue-list">
                      {#each issueEvidenceSubissues as row}
                        <span>{row.label} <b>{formatCount(row.count)}</b></span>
                      {:else}
                        <span>하위 의견 대기</span>
                      {/each}
                    </div>
                  </div>
                  <div>
                    <strong>검증 분포</strong>
                    <p>AI/규칙 요약이 원문과 맞는지 보는 감사 신호입니다. 기본 목록은 검증 통과만 보여줍니다.</p>
                    <div class="verdict-strip">
                      <span class="good">통과 {formatCount(issueEvidenceStats.match)}</span>
                      <span class="mixed">부분 {formatCount(issueEvidenceStats.partial)}</span>
                      <span class="bad">제외 {formatCount(issueEvidenceStats.reject)}</span>
                      <span>미검증 {formatCount(issueEvidenceStats.unverified)}</span>
                    </div>
                  </div>
                </section>
                {#if selectedIssue.warnings?.length}
                  <div class="warning-list">
                    {#each selectedIssue.warnings as warning}
                      <span>{warning}</span>
                    {/each}
                  </div>
                {/if}
                <div class="evidence-toolbar">
                  <div class="library-filters">
                    {#each issueEvidenceFilterOptions as filter}
                      <button
                        class="segment"
                        class:active={issueEvidenceFilter === filter.id}
                        type="button"
                        on:click={() => (issueEvidenceFilter = filter.id)}
                      >
                        {filter.label} {formatCount(issueEvidenceFilterCount(filter.id, issueEvidenceStats))}
                      </button>
                    {/each}
                  </div>
                  <label class="library-search compact-search">
                    <Search />
                    <input bind:value={issueEvidenceQuery} placeholder="근거 요약, 원문, 하위 의견 검색" />
                  </label>
                </div>
                <div class="review-samples">
                  {#each filteredIssueEvidenceItems as evidence}
                    <article class="review-sample">
                      <div class="sample-meta">
                        <strong>{steamLanguageLabel(evidence.language ?? 'unknown')}</strong>
                        <span class={`sentiment ${evidence.voted_up ? 'good' : 'bad'}`}>{evidence.voted_up ? '추천' : '비추천'}</span>
                        <span class={`sentiment ${verifierTone(evidence.verifier_verdict)}`}>{verifierLabel(evidence.verifier_verdict)}</span>
                        <span>{issueIntentLabel(evidence.evidence_role)}</span>
                        {#if displayEvidenceSubissue(evidence)}
                          <span>{displayEvidenceSubissue(evidence)}</span>
                        {/if}
                      </div>
                      {#if evidence.summary_ko}
                        <p>{evidence.summary_ko}</p>
                        <blockquote>“{trimText(evidence.quote, 180)}”</blockquote>
                      {:else}
                        <p>“{evidence.quote}”</p>
                      {/if}
                      <small>
                        품질 {evidence.quality_score === null || evidence.quality_score === undefined ? '미상' : formatPercent(evidence.quality_score)}
                        {#if evidence.playtime_at_review}
                          · {formatPlaytime(evidence.playtime_at_review)}
                        {/if}
                      </small>
                      {#if evidence.verifier_reason}
                        <div class="evidence-note">{evidence.verifier_reason}</div>
                      {/if}
                      {#if evidence.review_text}
                        <details class="review-original">
                          <summary>전체 원문 리뷰 보기</summary>
                          <p>{evidence.review_text}</p>
                        </details>
                      {/if}
                    </article>
                  {:else}
                    <div class="empty-state">현재 필터에 맞는 근거가 없습니다. 부분 관련/전체 탭이나 검색어를 바꿔보세요.</div>
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

        <section class:active={activeTab === 'evidence'} class="tab-view" aria-label="근거 확인">
          <PageIntro title="근거 확인" subtitle="AI가 만든 인사이트를 믿어도 되는지, 한국어 요약과 실제 원문을 대조하는 화면입니다.">
            <span class="status">인사이트 근거 {formatCount(issueEvidenceItems.length)}개 · 참고 근거 {formatCount(evidenceItems.length)}개</span>
          </PageIntro>
          <div class="method-note">
            <ScanSearch />
            <div>
              <strong>어떻게 쓰나요?</strong>
              <span>인사이트 보드에서 카드를 고른 뒤, 여기서 검증 통과 근거와 부분 관련/제외 근거를 나눠 보며 요약이 과장됐는지 확인합니다.</span>
            </div>
          </div>
          <section class="control-grid evidence-review-grid">
            <div class="panel form-panel">
              <div class="section-head"><div><h2>선택한 인사이트의 검증 근거</h2><p>{selectedIssue ? selectedIssue.title : '인사이트 보드에서 카드를 선택하세요.'}</p></div></div>
              <div class="truth-list">
                {#each issueEvidenceItems.slice(0, 8) as evidence}
                  <article class="truth-item evidence-truth">
                    <div>
                      <h3>{evidence.summary_ko || evidence.subissue || trimText(evidence.quote, 60)}</h3>
                      <p>{trimText(evidence.quote, 180)}</p>
                      {#if evidence.review_text}
                        <details class="review-original">
                          <summary>전체 원문 리뷰 보기</summary>
                          <p>{evidence.review_text}</p>
                        </details>
                      {/if}
                    </div>
                    <span class={`claim ${verifierTone(evidence.verifier_verdict)}`}>{verifierLabel(evidence.verifier_verdict)}</span>
                  </article>
                {:else}
                  {#each claimRows as claim}
                    <article class="truth-item"><div><h3>{claim[0]}</h3><p>{claim[1]}</p></div><span class={`claim ${claim[3]}`}>{claim[2]}</span></article>
                  {:else}
                    <div class="empty-state">아직 선택된 근거가 없습니다.</div>
                  {/each}
                {/each}
              </div>
            </div>
            <section class="panel evidence">
              <div class="section-head"><div><h3>자동 묶음 참고자료</h3><p>선택 인사이트와 별개로, 자동 묶음에서 추출한 참고 문장입니다.</p></div></div>
              <div class="quote-list">
                {#each evidenceItems.slice(0, 5) as evidence}
                  <article class="quote">
                    <p>“{evidence.quote}”</p>
                    <footer><span>{evidenceTypeLabel(evidence.evidence_type)}</span><span>{evidence.claim_text ? trimText(evidence.claim_text, 42) : clusterTitle(evidence.cluster_id)}</span><span>품질 {evidence.quality_score === null || evidence.quality_score === undefined ? '미상' : formatPercent(evidence.quality_score)}</span></footer>
                  </article>
                {:else}
                  <div class="empty-state">근거 리뷰가 없습니다. 분석 실행 후 다시 확인하세요.</div>
                {/each}
              </div>
            </section>
          </section>
          <SimpleTable title="요약-원문 대조표" headers={['유형', '문장', '연결 주장', '품질']} rows={evidenceTableRows.length ? evidenceTableRows : [['대기', '근거 데이터가 아직 없습니다.', '미연결', '대기']]} />
        </section>

        <section class:active={activeTab === 'axes'} class="tab-view" aria-label="평가축 관리">
          <PageIntro title="평가축 관리" subtitle="AI가 리뷰를 어떤 기준으로 읽고 있는지 확인하고, 게임별 기준을 승인하거나 끕니다.">
            <span class="status">{axisState}</span>
          </PageIntro>
          <MetricStrip items={axisMetrics} />
          <section class="detail-grid axis-management-grid">
            <section class="panel">
              <div class="section-head">
                <div>
                  <h2>활성 평가축</h2>
                  <p>공통 축은 모든 게임에, 게임별 축은 선택한 게임에만 적용됩니다.</p>
                </div>
                <span class="status">{formatCount(activeAxes.length)}개 활성</span>
              </div>
              <div class="axis-list">
                {#each axes as axis}
                  <article class="axis-item" class:disabled={axis.status !== 'active'}>
                    <div>
                      <header>
                        <strong>{axis.label}</strong>
                        <span class="cluster-tag">{axisScopeLabel(axis.scope)}</span>
                        <span class={`sentiment ${axis.status === 'active' ? 'good' : 'mixed'}`}>{axisStatusLabel(axis.status)}</span>
                      </header>
                      <p>{axis.description}</p>
                      <small>{axis.recommended_action}</small>
                    </div>
                    <button class="ghost-button compact" type="button" on:click={() => toggleAxis(axis)}>
                      {axis.status === 'active' ? '끄기' : '켜기'}
                    </button>
                  </article>
                {:else}
                  <div class="empty-state">평가축이 아직 없습니다. 백엔드 초기화 후 다시 확인하세요.</div>
                {/each}
              </div>
            </section>

            <section class="panel">
              <div class="section-head">
                <div>
                  <h2>미분류 주장 큐</h2>
                  <p>자동 분석이 평가축으로 확정하지 못한 반복 주장입니다. 통과 후보만 기본 표시하고, 원시 토큰은 진단용으로 숨깁니다.</p>
                </div>
                <div class="head-actions">
                  <span class="status">{formatCount(pendingAxisSuggestions.length)}개 대기</span>
                  <button class="ghost-button compact" type="button" on:click={toggleRawAxisSuggestions}>
                    {showRawAxisSuggestions ? '원시 숨김' : '원시 보기'}
                  </button>
                </div>
              </div>
              <div class="axis-list">
                {#each visibleAxisSuggestions as suggestion}
                  <article class="axis-item">
                    <div>
                      <header>
                        <strong>{suggestion.canonical_label_ko ?? suggestion.label}</strong>
                        <span class="cluster-tag">{axisSuggestionKindLabel(suggestion.kind)}</span>
                        <span class={`sentiment ${suggestion.quality_gate === 'pass' ? 'good' : 'mixed'}`}>{axisSuggestionGateLabel(suggestion.quality_gate)}</span>
                        <span class={`sentiment ${suggestion.status === 'pending' ? 'mixed' : 'good'}`}>{axisStatusLabel(suggestion.status)}</span>
                      </header>
                      <p>{suggestion.definition ?? suggestion.rationale}</p>
                      {#if suggestion.why_actionable}
                        <small>{suggestion.why_actionable}</small>
                      {/if}
                      {#if suggestion.include_criteria?.length}
                        <div class="mini-list">
                          {#each suggestion.include_criteria.slice(0, 3) as item}
                            <span>{item}</span>
                          {/each}
                        </div>
                      {/if}
                      {#if suggestion.failure_reason}
                        <small>숨김 사유: {suggestion.failure_reason}</small>
                      {/if}
                      <small>{formatCount(suggestion.evidence_count)}개 리뷰 · {languageCountLabel(suggestion.language_counts)}</small>
                    </div>
                    {#if suggestion.status === 'pending'}
                      <div class="axis-actions">
                        {#if suggestion.kind === 'merge_candidate' && suggestion.target_axis_id}
                          <button class="primary-button compact" type="button" on:click={() => mergeAxisSuggestion(suggestion)}>
                            {axisSuggestionTargetLabel(suggestion)}에 병합
                          </button>
                        {/if}
                        {#if suggestion.kind === 'axis_candidate' && suggestion.quality_gate === 'pass'}
                          <button class="primary-button compact" type="button" on:click={() => approveAxisSuggestion(suggestion.id)}>게임별 축 승인</button>
                        {/if}
                        {#if suggestion.quality_gate === 'pass'}
                          <button class="ghost-button compact" type="button" on:click={() => keepAxisSuggestion(suggestion.id)}>일회성 보관</button>
                        {/if}
                        <button class="ghost-button compact" type="button" on:click={() => ignoreAxisSuggestion(suggestion.id)}>
                          {suggestion.quality_gate === 'fail' ? '잡음 차단' : '무시'}
                        </button>
                      </div>
                    {/if}
                  </article>
                {:else}
                  <div class="empty-state">품질 기준을 통과한 미분류 주장이 없습니다. 이 상태가 정상일 수 있습니다. 이미 이슈 보드가 잘 설명하고 있거나, 후보가 잡음으로 걸러진 것입니다.</div>
                {/each}
              </div>
            </section>
          </section>
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
          <SimpleTable title="강점 활용 메모" headers={['용도', '후보', '검증']} rows={marketingBriefRows} />
        </section>

        <section class:active={activeTab === 'settings'} class="tab-view" aria-label="실행/설정">
          <PageIntro title="실행/설정" subtitle="/api/settings/models 기준으로 로컬 모델 상태와 분석 기본값을 확인합니다.">
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
                <label class="field"><span>LM Studio 모델</span><input bind:value={analysisOptions.llm_model} /></label>
                <label class="field"><span>기본 임베딩</span><input bind:value={analysisOptions.embedding_model} /></label>
                <label class="field toggle-field"><span>리포트 생성</span><input type="checkbox" bind:checked={analysisOptions.generate_ai_summary} /></label>
                <label class="field"><span>최소 반복 리뷰 수</span><input type="number" bind:value={analysisOptions.min_cluster_size} /></label>
                <label class="field"><span>품질 컷</span><input type="number" min="0" max="1" step="0.05" bind:value={analysisOptions.min_quality_score} /></label>
                <label class="field toggle-field"><span>중복 근거 제외</span><input type="checkbox" bind:checked={analysisOptions.exclude_duplicate_evidence} /></label>
              </div>
            </section>
          </section>
          <SimpleTable title="구현 메모" headers={['화면', '백엔드 역할', '기술']} rows={[
            ['데이터 갱신', 'Steam API 호출, cursor 저장, DuckDB upsert', 'FastAPI + DuckDB'],
            ['분석 실행', '리뷰 자동 묶기, 근거 연결, 진행률 저장', 'Python worker'],
            ['AI 리포트', '대표 리뷰와 인사이트 근거를 LLM에 보내고 결과 캐시', 'LM Studio/Claude/OpenAI'],
            ['근거 확인', '요약 문장과 원문 리뷰 연결 관계 저장', 'DuckDB']
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
        <label class="field"><span>게임명</span><input bind:value={gameForm.name} placeholder="예: Magical Girl Witch Trials" /></label>
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
        <label class="field"><span>최소 반복 리뷰 수</span><input type="number" min="1" max="1000" bind:value={analysisOptions.min_cluster_size} /></label>
        <label class="field"><span>품질 컷</span><input type="number" min="0" max="1" step="0.05" bind:value={analysisOptions.min_quality_score} /></label>
        <label class="field"><span>최대 의견 묶음</span><input type="number" min="1" max="120" bind:value={analysisOptions.max_clusters} /></label>
        <label class="field"><span>임베딩</span><input bind:value={analysisOptions.embedding_model} /></label>
        <label class="field"><span>LLM</span><select bind:value={analysisOptions.llm_provider}><option value="lm_studio">LM Studio</option><option value="none">사용 안 함</option></select></label>
        <label class="field"><span>LLM 모델</span><input bind:value={analysisOptions.llm_model} /></label>
        <label class="field toggle-field"><span>중복 근거 제외</span><input type="checkbox" bind:checked={analysisOptions.exclude_duplicate_evidence} /></label>
      </div>
      <div class="modal-actions">
        <span>현재 v1은 자동 큐 대신 목록 버튼으로 수동 실행합니다.</span>
        <button class="primary-button" type="button" on:click={() => (showSettingsPanel = false)}>적용</button>
      </div>
    </section>
  </div>
{/if}
