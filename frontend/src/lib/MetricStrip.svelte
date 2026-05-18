<script lang="ts">
  let { items }: { items: string[][] } = $props();
</script>

<div class="metric-strip">
  {#each items as item}
    <div class="metric">
      <span>{item[0]}</span>
      <strong>{item[1]}</strong>
      <small>{item[2]}</small>
    </div>
  {/each}
</div>
