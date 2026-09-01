<template>
  <div class="py-section">
    <div class="mb-xl">
      <h1 class="font-display text-display-lg text-ink tracking-[-1px] mb-sm">
        聚类分析
      </h1>
      <p class="text-body">
        通过机器学习算法将相似话题自动分组，发现潜在的主题模式
      </p>
    </div>

    <!-- 顶部统计卡：动态生成（聚类数量 + 总话题 + 每个分类） -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-lg mb-xl">
      <div class="card text-center">
        <div class="text-display-lg font-display text-primary mb-sm">{{ clusterStats.length }}</div>
        <div class="text-body-sm text-muted">聚类数量</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-body-strong mb-sm">{{ clusteringResults.length }}</div>
        <div class="text-body-sm text-muted">分析话题</div>
      </div>
      <div
        v-for="(stat, index) in clusterStats"
        :key="stat.name"
        class="card text-center"
      >
        <div class="text-display-lg font-display mb-sm" :class="statColors[index % statColors.length]">
          {{ stat.count }}
        </div>
        <div class="text-body-sm text-muted">{{ stat.name }}</div>
      </div>
    </div>

    <!-- 分类卡片：动态生成所有聚类 -->
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-xl">
      <div
        v-for="(stat, index) in clusterStats"
        :key="stat.name"
        class="card"
      >
        <div class="flex items-center justify-between mb-lg">
          <h2 class="text-title-lg font-medium text-ink">{{ stat.name }}</h2>
          <span class="badge-coral">{{ stat.count }}项</span>
        </div>
        <div class="space-y-md">
          <div
            v-for="item in getClusterItems(stat.name)"
            :key="item.title"
            class="flex items-center gap-md p-sm rounded-md hover:bg-surface-soft transition-colors"
          >
            <div class="w-10 h-10 rounded-lg flex items-center justify-center" :class="iconBgClasses[index % iconBgClasses.length]">
              <svg viewBox="0 0 24 24" class="w-5 h-5" :class="iconColorClasses[index % iconColorClasses.length]" fill="none" stroke="currentColor" stroke-width="2">
                <path :d="iconPaths[index % iconPaths.length]"/>
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-body-md text-ink truncate">{{ item.title }}</div>
              <div class="text-body-sm text-muted">{{ formatHotValue(item.avg_hot) }} 平均热度</div>
            </div>
          </div>
          <div
            v-if="getClusterItems(stat.name).length === 0"
            class="text-body-sm text-muted text-center py-md"
          >
            暂无话题
          </div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-xl mt-xl">
      <div class="card">
        <h2 class="text-title-lg font-medium text-ink mb-lg">聚类热度对比</h2>
        <div class="h-64">
          <BarChart :data="clusterChartData" />
        </div>
      </div>

      <div class="card">
        <h2 class="text-title-lg font-medium text-ink mb-lg">聚类详情</h2>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-hairline">
                <th class="text-left py-sm px-md text-body-sm font-medium text-muted">话题</th>
                <th class="text-left py-sm px-md text-body-sm font-medium text-muted">类别</th>
                <th class="text-left py-sm px-md text-body-sm font-medium text-muted">峰值热度</th>
                <th class="text-left py-sm px-md text-body-sm font-medium text-muted">平均热度</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in clusteringResults"
                :key="item.title"
                class="border-b border-hairline-soft hover:bg-surface-soft transition-colors"
              >
                <td class="py-sm px-md text-body-md text-ink">{{ item.title }}</td>
                <td class="py-sm px-md">
                  <span class="badge-pill">{{ item.cluster_name }}</span>
                </td>
                <td class="py-sm px-md text-body-md text-body-strong">{{ formatHotValue(item.peak_hot) }}</td>
                <td class="py-sm px-md text-body-md text-body-strong">{{ formatHotValue(item.avg_hot) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store } from '../store'
import BarChart from '../components/charts/BarChart.vue'

// 数据来自后端 API
const clusteringResults = computed(() => store.data.clusteringResults)

// 主题色板（与 design tokens 对齐）
const statColors = [
  'text-accent-teal',
  'text-accent-amber',
  'text-primary',
  'text-error'
]

const iconBgClasses = [
  'bg-accent-teal/10',
  'bg-accent-amber/10',
  'bg-primary/10',
  'bg-error/10'
]

const iconColorClasses = [
  'text-accent-teal',
  'text-accent-amber',
  'text-primary',
  'text-error'
]

const iconPaths = [
  'M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 8l3.26 2.26A9.75 9.75 0 0 1 12 3a9 9 0 0 1 9 9',
  'M22 12h-4l-3 9L9 3l-3 9H2',
  'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
  'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z'
]

const clusterChartColors = ['#5db8a6', '#e8a55a', '#cc785c', '#c64545']

// 聚类统计：从后端数据聚合
const clusterStats = computed(() => {
  const stats = {}
  clusteringResults.value.forEach(item => {
    if (!stats[item.cluster_name]) {
      stats[item.cluster_name] = { name: item.cluster_name, count: 0 }
    }
    stats[item.cluster_name].count++
  })
  return Object.values(stats)
})

const getClusterItems = (clusterName) => {
  return clusteringResults.value.filter(item => item.cluster_name === clusterName)
}

const formatHotValue = (value) => {
  if (value >= 10000) {
    return (value / 10000).toFixed(1) + '万'
  }
  return value.toString()
}

const clusterChartData = computed(() => {
  const stats = clusterStats.value
  const labels = stats.map(s => s.name)
  const data = stats.map(s => {
    const items = getClusterItems(s.name)
    const avg = items.reduce((sum, x) => sum + x.avg_hot, 0) / items.length
    return Math.round(avg / 10000)
  })

  return {
    labels,
    datasets: [{
      label: '平均热度(万)',
      data,
      backgroundColor: labels.map((_, i) => clusterChartColors[i % clusterChartColors.length]),
      borderRadius: 6
    }]
  }
})
</script>
