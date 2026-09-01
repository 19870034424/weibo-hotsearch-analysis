<template>
  <div class="py-section">
    <div class="mb-xl">
      <h1 class="font-display text-display-lg text-ink tracking-[-1px] mb-sm">
        词频分析
      </h1>
      <p class="text-body">
        分析热搜话题中的关键词，挖掘热点背后的核心主题
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-xl">
      <div class="lg:col-span-2 card">
        <h2 class="text-title-lg font-medium text-ink mb-lg">词云展示</h2>
        <div class="min-h-[400px] flex items-center justify-center bg-surface-soft rounded-lg">
          <div class="flex flex-wrap justify-center items-center gap-md p-lg">
            <span 
              v-for="(item, index) in wordFrequency" 
              :key="item.word"
              class="transition-all duration-300 hover:scale-110 cursor-pointer"
              :style="{ 
                fontSize: getFontSize(item.frequency) + 'px',
                color: getColor(index),
                fontWeight: getFontWeight(item.frequency)
              }"
            >
              {{ item.word }}
            </span>
          </div>
        </div>
      </div>

      <div class="space-y-xl">
        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">高频词汇TOP20</h2>
          <div class="space-y-sm">
            <div 
              v-for="(item, index) in wordFrequency.slice(0, 10)" 
              :key="item.word"
              class="flex items-center gap-md"
            >
              <span class="w-6 text-body-sm text-muted text-right">{{ index + 1 }}</span>
              <span class="flex-1 text-body-md text-ink">{{ item.word }}</span>
              <span class="text-body-sm text-body-strong">{{ item.frequency }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">统计概览</h2>
          <div class="space-y-md">
            <div class="flex justify-between items-center">
              <span class="text-body-sm text-muted">总词数</span>
              <span class="text-body-md font-medium text-ink">{{ wordFrequency.length }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-body-sm text-muted">最高频率</span>
              <span class="text-body-md font-medium text-ink">{{ maxFreq }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-body-sm text-muted">平均频率</span>
              <span class="text-body-md font-medium text-ink">{{ avgFreq }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-body-sm text-muted">最低频率</span>
              <span class="text-body-md font-medium text-ink">{{ minFreq }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card mt-xl">
      <h2 class="text-title-lg font-medium text-ink mb-lg">词频分布图表</h2>
      <div class="h-64">
        <BarChart :data="wordFrequencyChartData" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store } from '../store'
import BarChart from '../components/charts/BarChart.vue'

// 数据来自后端 API
const wordFrequency = computed(() => store.data.wordFrequency)

const colors = [
  '#cc785c', '#a9583e', '#5db8a6', '#5db872', '#e8a55a',
  '#c64545', '#6c6a64', '#252523', '#141413', '#d4a017'
]

const maxFreq = computed(() => wordFrequency.value.length ? Math.max(...wordFrequency.value.map(w => w.frequency)) : 0)
const minFreq = computed(() => wordFrequency.value.length ? Math.min(...wordFrequency.value.map(w => w.frequency)) : 0)
const avgFreq = computed(() => wordFrequency.value.length
  ? Math.round(wordFrequency.value.reduce((s, w) => s + w.frequency, 0) / wordFrequency.value.length)
  : 0)

const getFontSize = (frequency) => {
  const min = minFreq.value
  const max = maxFreq.value
  const normalized = (frequency - min) / (max - min || 1)
  return 16 + normalized * 40
}

const getFontWeight = (frequency) => {
  if (frequency >= 60) return '600'
  if (frequency >= 40) return '500'
  return '400'
}

const getColor = (index) => {
  return colors[index % colors.length]
}

// 词太多时柱状图只展示TOP15
const wordFrequencyChartData = computed(() => ({
  labels: wordFrequency.value.slice(0, 15).map(item => item.word),
  datasets: [{
    label: '词频',
    data: wordFrequency.value.slice(0, 15).map(item => item.frequency),
    backgroundColor: '#cc785c',
    borderRadius: 6
  }]
}))
</script>
