<template>
  <div class="py-section">
    <div class="mb-xl">
      <h1 class="font-display text-display-lg text-ink tracking-[-1px] mb-sm">
        趋势预测
      </h1>
      <p class="text-body">
        基于话题上榜历史预测下一时刻能否进入 TOP10 / TOP5（时间外推任务，仅展示样本外测试集结果）
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-lg mb-xl">
      <div class="card text-center">
        <div class="text-display-lg font-display text-body-strong mb-sm">{{ predictionMetrics.samples }}</div>
        <div class="text-body-sm text-muted">样本外测试样本</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-success mb-sm">{{ pct(predictionMetrics.top10_accuracy) }}%</div>
        <div class="text-body-sm text-muted">TOP10 预测准确率</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-accent-amber mb-sm">{{ pct(predictionMetrics.top5_accuracy) }}%</div>
        <div class="text-body-sm text-muted">TOP5 预测准确率</div>
      </div>
      <div class="card text-center">
        <div class="text-display-lg font-display text-primary mb-sm">{{ aucText }}</div>
        <div class="text-body-sm text-muted">最优模型 AUC ({{ predictionMetrics.model }})</div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-xl">
      <div class="card">
        <h2 class="text-title-lg font-medium text-ink mb-lg">TOP话题实测热度轨迹</h2>
        <div class="h-64">
          <LineChart :data="hotTrendChartData" />
        </div>
      </div>

      <div class="card">
        <h2 class="text-title-lg font-medium text-ink mb-lg">预测结果概览</h2>
        <div class="space-y-md">
          <div
            v-for="item in predictionResults.slice(0, 6)"
            :key="item.title + item.target_time"
            class="flex items-center gap-md p-md rounded-lg"
            :class="item.prediction_top10 ? 'bg-accent-amber/10' : 'bg-surface-soft'"
          >
            <div class="flex-1">
              <div class="flex items-center gap-sm">
                <span class="text-body-md text-ink">{{ item.title }}</span>
                <span v-if="item.prediction_top10" class="badge-pill">预计TOP10</span>
              </div>
              <div class="flex items-center gap-md mt-xs">
                <span class="text-body-sm text-muted">预测时刻排名: <strong class="text-body-strong">{{ Math.round(item.current_rank) + 1 }}</strong></span>
                <span class="text-body-sm text-muted">当前热度: <strong class="text-body-strong">{{ formatHotValue(item.current_hot) }}</strong></span>
                <span class="text-body-sm text-muted" :class="actualClass(item)">实际: {{ item.will_top10 ? 'TOP10内' : '未进TOP10' }}</span>
              </div>
            </div>
            <div class="text-right">
              <div class="text-body-md font-medium text-primary">{{ (item.probability * 100).toFixed(0) }}%</div>
              <div class="text-body-sm text-muted">预测概率</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card mt-xl">
      <h2 class="text-title-lg font-medium text-ink mb-lg">详细预测数据（预测 vs 实际）</h2>
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-hairline">
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">话题</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">预测时刻</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">当时排名</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">当时热度</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">预测TOP10</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">实际TOP10</th>
              <th class="text-left py-sm px-md text-body-sm font-medium text-muted">预测概率</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in predictionResults"
              :key="item.title + item.target_time"
              class="border-b border-hairline-soft hover:bg-surface-soft transition-colors"
            >
              <td class="py-sm px-md text-body-md text-ink">{{ item.title }}</td>
              <td class="py-sm px-md text-body-sm text-muted">{{ item.target_time }}</td>
              <td class="py-sm px-md text-body-md text-body-strong">{{ Math.round(item.current_rank) + 1 }}</td>
              <td class="py-sm px-md text-body-md text-body-strong">{{ formatHotValue(item.current_hot) }}</td>
              <td class="py-sm px-md">
                <span
                  class="badge-pill"
                  :class="item.prediction_top10 ? 'bg-success text-on-primary' : 'bg-surface-soft text-muted'"
                >
                  {{ item.prediction_top10 ? '是' : '否' }}
                </span>
              </td>
              <td class="py-sm px-md">
                <span
                  class="badge-pill"
                  :class="actualClass(item) === 'text-success' ? 'bg-success text-on-primary' : 'bg-surface-soft text-muted'"
                >
                  {{ item.will_top10 ? '是' : '否' }}
                </span>
              </td>
              <td class="py-sm px-md">
                <div class="flex items-center gap-sm">
                  <div class="w-24 h-2 bg-surface-soft rounded-full overflow-hidden">
                    <div
                      class="h-full bg-primary rounded-full transition-all duration-500"
                      :style="{ width: (item.probability * 100) + '%' }"
                    ></div>
                  </div>
                  <span class="text-body-sm text-body-strong">{{ (item.probability * 100).toFixed(0) }}%</span>
                </div>
              </td>
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
import LineChart from '../components/charts/LineChart.vue'

// 数据来自后端 API
const predictionResults = computed(() => store.data.predictionResults)
const predictionMetrics = computed(() => store.data.predictionMetrics)
const hotTrendSeries = computed(() => store.data.hotTrendSeries)

const formatHotValue = (value) => {
  if (value == null) return '—'
  if (value >= 10000) {
    return (value / 10000).toFixed(1) + '万'
  }
  return Math.round(value).toString()
}

const pct = (v) => v == null ? '—' : Math.round(v * 100)
const aucText = computed(() =>
  predictionMetrics.value.auc == null ? '—' : predictionMetrics.value.auc.toFixed(3)
)

// 预测对了显示绿色，预测错了显示红色
const actualClass = (item) => {
  return item.prediction_top10 === item.will_top10 ? 'text-success' : 'text-error'
}

const trendColors = ['#cc785c', '#5db872', '#5db8a6']

// 真实热度轨迹（热搜记录中峰值最高的3个话题）
const hotTrendChartData = computed(() => ({
  labels: hotTrendSeries.value.labels,
  datasets: hotTrendSeries.value.series.map((s, i) => ({
    label: s.title,
    data: s.data,
    borderColor: trendColors[i % trendColors.length],
    backgroundColor: trendColors[i % trendColors.length] + '1a',
    fill: false,
    tension: 0.3,
    spanGaps: true
  }))
}))
</script>
