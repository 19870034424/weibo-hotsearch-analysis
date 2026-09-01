<template>
  <div class="py-section">
    <div class="mb-xl">
      <h1 class="font-display text-display-lg text-ink tracking-[-1px] mb-sm">
        异常检测
      </h1>
      <p class="text-body">
        基于统计方法与孤立森林模型，自动识别热搜数据中的异常波动和突发热点
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-lg mb-xl">
      <div class="card text-center">
        <div class="text-display-lg font-display text-error mb-sm">{{ anomalyStats.total }}</div>
        <div class="text-body-sm text-muted">异常事件</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-primary mb-sm">{{ typeCount('extremely_high') }}</div>
        <div class="text-body-sm text-muted">极高热度异常</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-accent-amber mb-sm">{{ typeCount('viral_topic') }}</div>
        <div class="text-body-sm text-muted">爆款话题</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-success mb-sm">{{ anomalyStats.involved_topics }}</div>
        <div class="text-body-sm text-muted">涉及话题数</div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-xl">
      <div class="lg:col-span-2 card">
        <h2 class="text-title-lg font-medium text-ink mb-lg">异常事件列表</h2>
        <div class="space-y-md">
          <div
            v-for="item in anomalyResults"
            :key="item.title + item.anomaly_category"
            class="flex items-center gap-md p-md rounded-lg"
            :class="getAnomalyClass(item.anomaly_type)"
          >
            <div class="w-12 h-12 rounded-lg flex items-center justify-center" :class="getAnomalyIconBg(item.anomaly_type)">
              <svg v-if="item.anomaly_type === 'extremely_high' || item.anomaly_type === 'viral_topic'" viewBox="0 0 24 24" class="w-6 h-6" :class="getAnomalyIconColor(item.anomaly_type)" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 9v2m0 4h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" class="w-6 h-6" :class="getAnomalyIconColor(item.anomaly_type)" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/>
              </svg>
            </div>
            <div class="flex-1">
              <div class="flex items-center gap-sm">
                <span class="text-body-md text-ink">{{ item.title }}</span>
                <span
                  class="badge-coral"
                  :class="item.anomaly_type === 'extremely_high' || item.anomaly_type === 'viral_topic' ? '' : 'bg-accent-amber text-ink'"
                >
                  {{ getAnomalyLabel(item.anomaly_type) }}
                </span>
              </div>
              <div class="flex items-center gap-md mt-xs">
                <span class="text-body-sm text-muted">热度: <strong class="text-body-strong">{{ formatHotValue(item.hot_value) }}</strong></span>
                <span class="text-body-sm text-muted">{{ item.crawl_time || '—' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="space-y-xl">
        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">异常类型分布</h2>
          <div class="h-48 flex items-center justify-center">
            <DoughnutChart :data="anomalyTypeChartData" />
          </div>
        </div>

        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">最高热度异常</h2>
          <div class="space-y-md">
            <div 
              v-for="(item, index) in topAnomalies" 
              :key="item.title"
              class="flex items-center gap-md"
            >
              <span class="w-8 text-body-sm font-medium" :class="getRankClass(index)">{{ index + 1 }}</span>
              <span class="flex-1 text-body-md text-ink truncate">{{ item.title }}</span>
              <span class="text-body-sm text-body-strong">{{ formatHotValue(item.hot_value) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card mt-xl">
      <h2 class="text-title-lg font-medium text-ink mb-lg">监控状态</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-lg">
        <div class="flex items-center gap-md p-md bg-surface-soft rounded-lg">
          <div class="w-10 h-10 rounded-full flex items-center justify-center" :class="dataStatus.fresh ? 'bg-success/10' : 'bg-accent-amber/10'">
            <svg viewBox="0 0 24 24" class="w-5 h-5" :class="dataStatus.fresh ? 'text-success' : 'text-accent-amber'" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <div>
            <div class="text-body-md text-ink">数据采集</div>
            <div class="text-body-sm" :class="dataStatus.fresh ? 'text-success' : 'text-accent-amber'">
              {{ dataStatus.last_crawl ? `最后爬取 ${dataStatus.age_hours}小时前` : '暂无爬取记录' }}
            </div>
          </div>
        </div>
        <div class="flex items-center gap-md p-md bg-surface-soft rounded-lg">
          <div class="w-10 h-10 bg-success/10 rounded-full flex items-center justify-center">
            <svg viewBox="0 0 24 24" class="w-5 h-5 text-success" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <div>
            <div class="text-body-md text-ink">分析流水线</div>
            <div class="text-body-sm text-success">生成于 {{ dataStatus.analysis_generated_at }}</div>
          </div>
        </div>
        <div class="flex items-center gap-md p-md bg-surface-soft rounded-lg">
          <div class="w-10 h-10 bg-success/10 rounded-full flex items-center justify-center">
            <svg viewBox="0 0 24 24" class="w-5 h-5 text-success" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <div>
            <div class="text-body-md text-ink">异常检测规模</div>
            <div class="text-body-sm text-success">{{ anomalyStats.total }} 项异常 / {{ anomalyStats.involved_topics }} 个话题</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store } from '../store'
import DoughnutChart from '../components/charts/DoughnutChart.vue'

// 数据来自后端 API
const anomalyResults = computed(() => store.data.anomalyResults)
const anomalyStats = computed(() => store.data.anomalyStats)
const dataStatus = computed(() => store.data.dataStatus)

const formatHotValue = (value) => {
  if (value == null) return '—'
  if (value >= 10000) {
    return (value / 10000).toFixed(1) + '万'
  }
  return Math.round(value).toString()
}

const anomalyLabels = {
  extremely_high: '极高热度',
  extremely_low: '极低热度',
  sudden_rise: '排名飙升',
  sudden_drop: '排名骤降',
  viral_topic: '爆款话题',
  disappeared: '话题消失',
  new_emerging: '新晋话题',
  isolation_forest: '孤立森林异常'
}

const typeCount = (type) => anomalyStats.value.by_type?.[type] || 0

const getAnomalyClass = (type) => {
  if (type === 'extremely_high' || type === 'viral_topic') return 'bg-error/5'
  if (type === 'sudden_rise' || type === 'new_emerging') return 'bg-accent-amber/5'
  return 'bg-surface-soft'
}

const getAnomalyIconBg = (type) => {
  if (type === 'extremely_high' || type === 'viral_topic') return 'bg-error/10'
  if (type === 'sudden_rise' || type === 'new_emerging') return 'bg-accent-amber/10'
  return 'bg-surface-cream-strong'
}

const getAnomalyIconColor = (type) => {
  if (type === 'extremely_high' || type === 'viral_topic') return 'text-error'
  if (type === 'sudden_rise' || type === 'new_emerging') return 'text-accent-amber'
  return 'text-muted'
}

const getAnomalyLabel = (type) => anomalyLabels[type] || '其他异常'

const getRankClass = (index) => {
  if (index === 0) return 'text-error font-bold'
  if (index === 1) return 'text-accent-amber font-bold'
  if (index === 2) return 'text-accent-teal font-bold'
  return 'text-muted'
}

const topAnomalies = computed(() => {
  return [...anomalyResults.value]
    .filter(item => item.hot_value != null)
    .sort((a, b) => b.hot_value - a.hot_value)
    .slice(0, 5)
})

const anomalyTypeChartData = computed(() => {
  const entries = Object.entries(anomalyStats.value.by_type || {})
  return {
    labels: entries.map(([type]) => anomalyLabels[type] || type),
    datasets: [{
      data: entries.map(([, count]) => count),
      backgroundColor: ['#c64545', '#e8a55a', '#5db8a6', '#6c6a64', '#cc785c', '#5db872', '#a9583e', '#d4a017'],
      borderWidth: 0
    }]
  }
})
</script>
