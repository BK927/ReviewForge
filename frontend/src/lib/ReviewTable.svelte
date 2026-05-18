<script lang="ts">
  import { Download } from 'lucide-svelte';

  type Review = {
    language: string;
    reaction: 'good' | 'bad' | 'mixed';
    playtime: string;
    topic: string;
    summary: string;
  };

  let { title, subtitle }: { title: string; subtitle: string } = $props();

  const reviews: Review[] = [
    { language: 'EN', reaction: 'bad', playtime: '38.4h', topic: '후반 반복성', summary: '초반 전투는 훌륭하지만 30시간 이후 목표와 보상이 반복적으로 느껴진다는 반응입니다.' },
    { language: 'KO', reaction: 'good', playtime: '12.1h', topic: '전투 손맛', summary: '무기별 리듬과 보스전 긴장감이 좋고, 전작 팬에게 기대한 재미를 준다는 반응입니다.' },
    { language: 'ZH', reaction: 'mixed', playtime: '22.7h', topic: '밸런스', summary: '업데이트 후 특정 빌드 효율이 과도하게 낮아졌고 선택지가 줄었다는 의견입니다.' }
  ];

  function reactionLabel(reaction: Review['reaction']) {
    return reaction === 'good' ? '추천' : reaction === 'bad' ? '비추천' : '혼합';
  }
</script>

<section class="panel reviews">
  <div class="section-head">
    <div>
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </div>
    <button class="ghost-button" type="button"><Download /><span>내보내기</span></button>
  </div>
  <table class="review-table">
    <thead><tr><th>언어</th><th>반응</th><th>플레이타임</th><th>토픽</th><th>리뷰 요약</th></tr></thead>
    <tbody>
      {#each reviews as review}
        <tr>
          <td>{review.language}</td>
          <td><span class={`sentiment ${review.reaction}`}>{reactionLabel(review.reaction)}</span></td>
          <td>{review.playtime}</td>
          <td>{review.topic}</td>
          <td class="review-copy">{review.summary}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</section>
