<template>
  <div class="py-section">
    <div class="mb-xl">
      <h1 class="font-display text-display-lg text-ink tracking-[-1px] mb-sm">
        情感分析
      </h1>
      <p class="text-body">
        基于话题标题文本的情感打分（SnowNLP 模型），反映话题措辞色彩，不等同于网友评论情绪
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-lg mb-xl">
      <div class="card text-center">
        <div class="text-display-lg font-display text-success mb-sm">{{ positivePct }}%</div>
        <div class="text-body-sm text-muted">正面情感</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-error mb-sm">{{ negativePct }}%</div>
        <div class="text-body-sm text-muted">负面情感</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-body-strong mb-sm">{{ neutralPct }}%</div>
        <div class="text-body-sm text-muted">中性情感</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-primary mb-sm">{{ sentimentResults.length }}</div>
        <div class="text-body-sm text-muted">分析话题数</div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-xl">
      <div class="card">
        <h2 class="text-title-lg font-medium text-ink mb-lg">情感分布</h2>
        <div class="h-64 flex items-center justify-center">
          <DoughnutChart :data="sentimentChartData" />
        </div>
      </div>

      <div class="card">
        <h2 class="text-title-lg font-medium text-ink mb-lg">情感趋势</h2>
        <div class="h-64">
          <LineChart :data="sentimentTrendData" />
        </div>
      </div>
    </div>

    <div class="card mt-xl">
      <h2 class="text-title-lg font-medium text-ink mb-lg">详细分析结果</h2>
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-hairline">
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">话题</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">情感分数</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">主导情感</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">出现次数</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">情感类型</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="item in sentimentResults" 
              :key="item.title"
              class="border-b border-hairline-soft hover:bg-surface-soft transition-colors"
            >
              <td class="py-sm px-md text-body-md text-ink">{{ item.title }}</td>
              <td class="py-sm px-md">
                <div class="flex items-center gap-sm">
                  <div class="w-24 h-2 bg-surface-soft rounded-full overflow-hidden">
                    <div 
                      class="h-full rounded-full transition-all duration-500"
                      :class="getSentimentBarClass(item.avg_sentiment)"
                      :style="{ width: (item.avg_sentiment * 100) + '%' }"
                    ></div>
                  </div>
                  <span class="text-body-sm text-body-strong">{{ (item.avg_sentiment * 100).toFixed(0) }}</span>
                </div>
              </td>
              <td class="py-sm px-md">
                <span 
                  class="badge-pill"
                  :class="getSentimentClass(item.dominant_sentiment)"
                >
                  {{ getSentimentLabel(item.dominant_sentiment) }}
                </span>
              </td>
              <td class="py-sm px-md text-body-md text-body-strong">{{ item.appear_count }}</td>
              <td class="py-sm px-md text-body-sm text-muted">{{ item.emotion_type }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store } from '../store'
import DoughnutChart from '../components/charts/DoughnutChart.vue'
import LineChart from '../components/charts/LineChart.vue'

// 数据来自后端 API
const sentimentResults = computed(() => store.data.sentimentResults)
const sentimentTrend = computed(() => store.data.sentimentTrend)

// 真实情感极性占比（由 sentiment_results.csv 计算）
const positivePct = computed(() => {
  if (!sentimentResults.value.length) return 0
  return Math.round(sentimentResults.value.filter(i => i.dominant_sentiment === 'positive').length / sentimentResults.value.length * 100)
})
const negativePct = computed(() => {
  if (!sentimentResults.value.length) return 0
  return Math.round(sentimentResults.value.filter(i => i.dominant_sentiment === 'negative').length / sentimentResults.value.length * 100)
})
const neutralPct = computed(() => 100 - positivePct.value - negativePct.value)

const sentimentChartData = computed(() => ({
  labels: ['正面', '负面', '中性'],
  datasets: [{
    data: [positivePct.value, negativePct.value, neutralPct.value],
    backgroundColor: ['#5db872', '#c64545', '#6c6a64'],
    borderWidth: 0
  }]
}))

// 每小时上榜话题的真实情感极性占比（%）
const sentimentTrendData = computed(() => ({
  labels: sentimentTrend.value.map(item => item.hour),
  datasets: [
    {
      label: '正面',
      data: sentimentTrend.value.map(item => item.positive),
      borderColor: '#5db872',
      backgroundColor: 'rgba(93, 184, 114, 0.1)',
      fill: true,
      tension: 0.4
    },
    {
      label: '负面',
      data: sentimentTrend.value.map(item => item.negative),
      borderColor: '#c64545',
      backgroundColor: 'rgba(198, 69, 69, 0.1)',
      fill: true,
      tension: 0.4
    },
    {
      label: '中性',
      data: sentimentTrend.value.map(item => item.neutral),
      borderColor: '#6c6a64',
      backgroundColor: 'rgba(108, 106, 100, 0.1)',
      fill: true,
      tension: 0.4
    }
  ]
}))

const getSentimentClass = (sentiment) => {
  switch (sentiment) {
    case 'positive': return 'bg-success text-on-primary'
    case 'negative': return 'bg-error text-on-primary'
    default: return 'bg-muted text-on-dark'
  }
}

const getSentimentLabel = (sentiment) => {
  switch (sentiment) {
    case 'positive': return '正面'
    case 'negative': return '负面'
    default: return '中性'
  }
}

const getSentimentBarClass = (score) => {
  if (score >= 0.6) return 'bg-success'
  if (score <= 0.4) return 'bg-error'
  return 'bg-muted'
}
</script>
