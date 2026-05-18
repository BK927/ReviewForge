<script lang="ts">
  import { Check, Clock, Languages, Network, ScanText, Sparkles } from 'lucide-svelte';

  let { pipeline = false }: { pipeline?: boolean } = $props();

  const refreshRows = [
    { icon: Check, title: 'Steam API 페이지 수집', detail: 'cursor 기반 증분 수집 완료', state: '완료', tone: 'good' },
    { icon: Check, title: '원본 리뷰 저장', detail: 'review_id 기준 중복 제거', state: '완료', tone: 'good' },
    { icon: Clock, title: '분석 인덱스 갱신', detail: '새 리뷰 1,284개 대기', state: '필요', tone: 'mixed' }
  ];

  const pipelineRows = [
    { icon: Languages, title: '언어 정규화', detail: 'Steam 언어값과 감지 언어 비교', state: '완료', tone: 'good' },
    { icon: ScanText, title: '임베딩 생성', detail: '다국어 문장 의미 벡터 생성', state: '진행', tone: 'mixed' },
    { icon: Network, title: '클러스터링', detail: '비슷한 리뷰 묶음과 대표 리뷰 선택', state: '대기', tone: 'mixed' },
    { icon: Sparkles, title: 'AI 요약', detail: '클러스터 단위로만 LLM 호출', state: '대기', tone: 'mixed' }
  ];
</script>

<div class="panel">
  <div class="section-head">
    <div>
      <h2>{pipeline ? '파이프라인' : '갱신 상태'}</h2>
      <p>{pipeline ? '느린 작업은 백엔드에서 돌리고 화면은 진행률만 받습니다.' : '실패한 단계가 있으면 여기서 다시 실행합니다.'}</p>
    </div>
  </div>
  <div class="run-list">
    {#each (pipeline ? pipelineRows : refreshRows) as row}
      {@const RowIcon = row.icon}
      <div class="run-row">
        <span class="run-icon"><RowIcon /></span>
        <div><strong>{row.title}</strong><span>{row.detail}</span></div>
        <span class={`sentiment ${row.tone}`}>{row.state}</span>
      </div>
    {/each}
  </div>
</div>
