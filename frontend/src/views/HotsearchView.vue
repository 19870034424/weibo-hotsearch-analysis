<template>
  <div class="py-section">
    <div class="flex flex-col md:flex-row md:items-end justify-between mb-xl gap-md">
      <div>
        <h1 class="font-display text-display-lg text-ink tracking-[-1px] mb-sm">
          实时热搜
        </h1>
        <p class="text-body">
          实时追踪微博热点话题，掌握最新舆论动态
        </p>
      </div>
      <div class="flex items-center gap-md">
        <div class="flex items-center gap-sm text-body-sm text-muted">
          <svg viewBox="0 0 24 24" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 20 L12 10 M18 20 L18 4 M6 20 L6 16"/>
          </svg>
          <span>数据爬取于 {{ lastCrawl }}</span>
        </div>
        <button class="button-secondary" @click="refreshData">
          <svg viewBox="0 0 24 24" class="w-4 h-4 inline mr-sm" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8l3.26 2.26A9.75 9.75 0 0 0 12 21a9 9 0 0 0 9-9"/>
            <path d="M16 3h2v7h-2"/>
            <path d="M21 16v2h-7"/>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-xl">
      <div class="lg:col-span-2">
        <div class="card">
          <div class="flex items-center justify-between mb-lg">
            <h2 class="text-title-lg font-medium text-ink">热搜榜单</h2>
            <div class="flex items-center gap-sm">
              <button
                v-for="filter in filters"
                :key="filter.value"
                @click="activeFilter = filter.value"
                class="category-tab"
                :class="{ 'category-tab-active': activeFilter === filter.value }"
              >
                {{ filter.label }}
              </button>
            </div>
          </div>

          <div class="space-y-sm">
            <div
              v-for="item in filteredData"
              :key="item.title"
              class="flex items-center gap-md p-sm rounded-md hover:bg-surface-soft transition-colors cursor-pointer group"
            >
              <div
                class="w-8 h-8 flex items-center justify-center rounded-md font-display text-display-sm font-medium"
                :class="getRankClass(item.rank)"
              >
                {{ item.rank + 1 }}
              </div>

              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-sm">
                  <span class="text-body-md text-ink truncate">{{ item.title }}</span>
                  <span v-if="item.label" class="badge-coral whitespace-nowrap">{{ item.label }}</span>
                </div>
                <span class="text-body-sm text-muted">{{ item.crawl_time }}</span>
              </div>

              <div class="flex items-center gap-md">
                <div class="text-right">
                  <span class="text-body-md font-medium text-body-strong">{{ formatHotValue(item.hot_value) }}</span>
                  <span class="text-body-sm text-muted ml-xs">热度</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="card mt-xl">
          <h2 class="text-title-lg font-medium text-ink mb-lg">TOP话题热度排行</h2>
          <div class="h-72">
            <BarChart :data="topTopicsChartData" />
          </div>
        </div>
      </div>

      <div class="space-y-xl">
        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">热度分布（小时）</h2>
          <div class="h-64">
            <BarChart :data="hourlyChartData" />
          </div>
        </div>

        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">标签分布</h2>
          <div class="h-64">
            <DoughnutChart :data="labelChartData" />
          </div>
        </div>

        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">聚类类别分布</h2>
          <div class="h-64">
            <BarChart :data="clusterChartData" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { store, loadData } from '../store'
import BarChart from '../components/charts/BarChart.vue'
import DoughnutChart from '../components/charts/DoughnutChart.vue'

// 数据来自后端 API（store.data），视图内保持原变量名，模板无需改动
const hotsearchRecords = computed(() => store.data.hotsearchRecords)
const hourlyDistribution = computed(() => store.data.hourlyDistribution)
const labelDistribution = computed(() => store.data.labelDistribution)
const clusterDistribution = computed(() => store.data.clusterDistribution)

// 爬虫最近一次真实爬取时间
const lastCrawl = computed(() => store.data.dataMeta.last_crawl || '未知')
const activeFilter = ref('all')

const filters = [
  { label: '全部', value: 'all' },
  { label: '热', value: '热' },
  { label: '新', value: '新' },
  { label: '沸', value: '沸' }
]

const filteredData = computed(() => {
  if (activeFilter.value === 'all') return hotsearchRecords.value
  return hotsearchRecords.value.filter(item => item.label === activeFilter.value)
})

const hourlyChartData = computed(() => ({
  labels: hourlyDistribution.value.map(item => item.hour),
  datasets: [{
    label: '热搜数量',
    data: hourlyDistribution.value.map(item => item.count),
    backgroundColor: '#cc785c',
    borderRadius: 6,
    barThickness: 24
  }]
}))

const labelChartData = computed(() => ({
  labels: labelDistribution.value.map(item => item.label),
  datasets: [{
    data: labelDistribution.value.map(item => item.count),
    backgroundColor: ['#c64545', '#cc785c', '#5db8a6', '#e8a55a'],
    borderWidth: 0
  }]
}))

const topTopicsChartData = computed(() => {
  const top = [...hotsearchRecords.value]
    .sort((a, b) => b.hot_value - a.hot_value)
    .slice(0, 10)
  return {
    labels: top.map(item => item.title.length > 8 ? item.title.slice(0, 8) + '…' : item.title),
    datasets: [{
      label: '热度',
      data: top.map(item => Math.round(item.hot_value / 10000)),
      backgroundColor: '#cc785c',
      borderRadius: 6
    }]
  }
})

const clusterChartData = computed(() => ({
  labels: clusterDistribution.value.map(item => item.cluster_name),
  datasets: [{
    label: '话题数',
    data: clusterDistribution.value.map(item => item.count),
    backgroundColor: ['#cc785c', '#5db8a6', '#e8a55a', '#5db872', '#c64545', '#6c6a64'],
    borderRadius: 6
  }]
}))

const getRankClass = (rank) => {
  if (rank === 0) return 'bg-primary text-on-primary'
  if (rank === 1) return 'bg-accent-amber text-ink'
  if (rank === 2) return 'bg-accent-teal text-ink'
  return 'bg-surface-soft text-muted'
}

const formatHotValue = (value) => {
  if (value >= 10000) {
    return (value / 10000).toFixed(1) + '万'
  }
  return value.toString()
}

const refreshData = () => {
  // 重新从后端拉取最新数据（爬虫/分析更新后即可看到）
  loadData()
}
</script>
