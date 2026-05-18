<script lang="ts">
  import type { Snippet } from 'svelte';

  let { title, subtitle, children }: { title: string; subtitle: string; children?: Snippet } = $props();
</script>

<div class="page-intro">
  <div>
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>
  {@render children?.()}
</div>
