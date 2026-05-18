<script lang="ts">
  let { cluster = false }: { cluster?: boolean } = $props();
  const dashboardLabels = ['기간', '언어', '플레이타임', '추천 여부'];
  const clusterLabels = ['클러스터 유형', '강도', '대표 언어', '플레이타임'];
</script>

<section class="filters" aria-label={cluster ? '클러스터 필터' : '분석 필터'}>
  {#each (cluster ? clusterLabels : dashboardLabels) as label, index}
    <label class="filter">
      <span>{label}</span>
      <select aria-label={label}>
        <option>{index === 0 ? '전체' : '전체 범위'}</option>
        <option>최근 30일</option>
        <option>패치 1.2 이후</option>
      </select>
    </label>
  {/each}
</section>
