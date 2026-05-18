<script lang="ts">
  let { title, subtitle, topics }: { title: string; subtitle: string; topics: string[][] } = $props();
</script>

<div class="panel topic-panel">
  <div class="section-head">
    <div>
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
  </div>
  <div class="topic-list">
    {#each topics as topic}
      <div class="topic-item">
        <div><strong>{topic[0]}</strong><span>{topic[1]}</span></div>
        <span class={`trend ${topic[3]}`}>{topic[2]}</span>
      </div>
    {/each}
  </div>
</div>
