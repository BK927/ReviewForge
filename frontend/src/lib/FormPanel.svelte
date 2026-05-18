<script lang="ts">
  import { Plus } from 'lucide-svelte';

  let { title, subtitle, fields, action = '' }: { title: string; subtitle: string; fields: string[]; action?: string } = $props();
</script>

<section class="panel form-panel">
  <div class="section-head">
    <div>
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
    {#if action}
      <button class="ghost-button" type="button"><Plus /><span>{action}</span></button>
    {/if}
  </div>
  <div class="field-grid">
    {#each fields as field, index}
      <label class="field">
        <span>{field}</span>
        {#if index === 0 && field.includes('App')}
          <input value="1145350" aria-label={field} />
        {:else}
          <select aria-label={field}>
            <option>{field} 기본값</option>
            <option>직접 설정</option>
          </select>
        {/if}
      </label>
    {/each}
  </div>
</section>
