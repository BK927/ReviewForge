<script lang="ts">
  let { title, rows, compact = false }: { title: string; rows: string[][]; compact?: boolean } = $props();
</script>

<section class="panel priority">
  <div class="section-head">
    <div>
      <h2>{title}</h2>
      {#if !compact}<p>품질 신호를 함께 확인합니다.</p>{/if}
    </div>
  </div>
  <div class="audit-list">
    {#each rows as row}
      <div class="audit-row">
        <div><strong>{row[0]}</strong><span>{row[1]}</span></div>
        <span class={`sentiment ${row[3]}`}>{row[2]}</span>
      </div>
    {/each}
  </div>
</section>
