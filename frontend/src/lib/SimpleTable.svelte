<script lang="ts">
  let { title, headers, rows }: { title: string; headers: string[]; rows: string[][] } = $props();
</script>

<section class="panel reviews">
  <div class="section-head">
    <div>
      <h2>{title}</h2>
      <p>현재 화면에서 필요한 백엔드 데이터 계약입니다.</p>
    </div>
  </div>
  <table class="review-table">
    <thead><tr>{#each headers as header}<th>{header}</th>{/each}</tr></thead>
    <tbody>
      {#each rows as row}
        <tr>{#each row as cell}<td>{cell}</td>{/each}</tr>
      {/each}
    </tbody>
  </table>
</section>
