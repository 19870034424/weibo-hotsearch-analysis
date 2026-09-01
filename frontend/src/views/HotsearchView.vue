<template>
  <div class="py-section">
    <!-- 页头 -->
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
          <span
            class="w-2 h-2 rounded-full inline-block"
            :class="dataFresh ? 'bg-success' : 'bg-accent-amber'"
          ></span>
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

    <!-- 统计卡行 -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-lg mb-xl">
      <div class="card text-center !py-lg">
        <div class="text-display-md font-display text-primary">{{ hotsearchRecords.length }}</div>
        <div class="text-body-sm text-muted mt-xs">当前在榜话题</div>
      </div>
      <div class="card text-center !py-lg">
        <div class="text-display-md font-display text-body-strong">{{ totalRecords }}</div>
        <div class="text-body-sm text-muted mt-xs">累计采集记录</div>
      </div>
      <div class="card text-center !py-lg">
        <div class="text-display-md font-display text-error">{{ formatHotValue(maxHot) }}</div>
        <div class="text-body-sm text-muted mt-xs">当前最高热度</div>
      </div>
      <div class="card text-center !py-lg">
        <div class="text-display-md font-display" :class="dataFresh ? 'text-success' : 'text-accent-amber'">
          {{ dataFresh ? '新鲜' : ageHours + 'h' }}
        </div>
        <div class="text-body-sm text-muted mt-xs">数据状态</div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-xl">
      <!-- ===== 左栏 ===== -->
      <div class="lg:col-span-2 space-y-xl">
        <!-- 热搜榜单 -->
        <div class="card">
          <div class="flex items-center justify-between mb-lg gap-md flex-wrap">
            <h2 class="text-title-lg font-medium text-ink">热搜榜单</h2>
            <div class="relative">
              <svg viewBox="0 0 24 24" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-soft" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/>
              </svg>
              <input
                v-model="keyword"
                type="text"
                placeholder="搜索话题关键词…"
                class="text-input !h-9 !py-0 pl-9 w-52 text-body-sm"
              />
            </div>
          </div>

          <!-- 筛选 + 排序 -->
          <div class="flex items-center justify-between mb-lg gap-md flex-wrap">
            <div class="flex items-center gap-sm flex-wrap">
              <button
                v-for="f in filters"
                :key="f.value"
                @click="activeFilter = f.value"
                class="category-tab"
                :class="{ 'category-tab-active': activeFilter === f.value }"
              >
                {{ f.label }}
                <span class="text-caption text-muted ml-xs">{{ tabCounts[f.value] || 0 }}</span>
              </button>
            </div>
            <div class="flex items-center bg-surface-soft rounded-md p-xs gap-xs">
              <button
                v-for="s in sorts"
                :key="s.value"
                @click="sortMode = s.value"
                class="px-sm py-1 rounded-md text-caption font-medium transition-colors"
                :class="sortMode === s.value ? 'bg-canvas text-ink shadow-sm' : 'text-muted hover:text-ink'"
              >
                {{ s.label }}
              </button>
            </div>
          </div>

          <!-- 榜单列表 -->
          <div class="space-y-sm">
            <div
              v-for="item in filteredData"
              :key="item.title"
              class="flex items-center gap-md p-sm rounded-md hover:bg-surface-soft transition-colors cursor-default group"
            >
              <div
                class="w-8 h-8 flex-none flex items-center justify-center rounded-md font-display text-display-sm font-medium"
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

              <div class="w-28 flex-none text-right">
                <span class="text-body-md font-medium text-body-strong">{{ formatHotValue(item.hot_value) }}</span>
                <span class="text-body-sm text-muted ml-xs">热度</span>
                <div class="h-1 mt-xs bg-surface-soft rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full bg-primary transition-all duration-500"
                    :style="{ width: hotPercent(item.hot_value) + '%' }"
                  ></div>
                </div>
              </div>
            </div>

            <div v-if="filteredData.length === 0" class="text-center py-xl text-body text-muted">
              没有匹配的话题，试试其他关键词或筛选条件
            </div>
          </div>

          <div class="mt-lg pt-md border-t border-hairline-soft text-caption text-muted flex justify-between">
            <span>显示 {{ filteredData.length }} / {{ hotsearchRecords.length }} 条</span>
            <span>榜单为最新一次爬取快照</span>
          </div>
        </div>

        <!-- TOP10 横向排行 -->
        <div class="card">
          <div class="flex items-center justify-between mb-lg">
            <h2 class="text-title-lg font-medium text-ink">TOP话题热度排行</h2>
            <span class="text-caption text-muted">热度（万）</span>
          </div>
          <div class="h-80">
            <BarChart :data="topTopicsChartData" horizontal />
          </div>
        </div>
      </div>

      <!-- ===== 右栏 ===== -->
      <div class="space-y-xl">
        <!-- 小时分布：点击柱条展开该时段TOP话题 -->
        <div class="card">
          <div class="flex items-center justify-between mb-lg">
            <h2 class="text-title-lg font-medium text-ink">热度分布（小时）</h2>
            <span class="text-caption text-muted">点击柱条查看详情</span>
          </div>
          <div class="h-52">
            <BarChart :data="hourlyChartData" @select="onSelectHour" />
          </div>
          <div
            v-if="activeHour"
            class="mt-lg bg-surface-soft rounded-lg p-md"
          >
            <div class="flex items-center justify-between mb-sm">
              <span class="text-body-sm font-medium text-ink">{{ activeHour }} 上榜热度 TOP5</span>
              <button class="text-caption text-muted hover:text-error" @click="activeHour = null">收起 ×</button>
            </div>
            <div class="space-y-xs">
              <div
                v-for="(t, i) in activeHourTopics"
                :key="t.title"
                class="flex items-center gap-sm text-body-sm"
              >
                <span class="w-4 text-caption text-muted text-right">{{ i + 1 }}</span>
                <span class="flex-1 truncate text-ink">{{ t.title }}</span>
                <span class="text-caption text-body-strong">{{ formatHotValue(t.hot_value) }}</span>
              </div>
              <div v-if="activeHourTopics.length === 0" class="text-caption text-muted py-sm text-center">
                该时段暂无上榜记录
              </div>
            </div>
          </div>
        </div>

        <!-- 标签分布：点击扇区同步筛选榜单 -->
        <div class="card">
          <div class="flex items-center justify-between mb-lg">
            <h2 class="text-title-lg font-medium text-ink">标签分布</h2>
            <span class="text-caption text-muted">点击筛选榜单</span>
          </div>
          <div class="h-56">
            <DoughnutChart :data="labelChartData" tooltip-suffix="" @select="onSelectLabel" />
          </div>
          <div v-if="activeFilter !== 'all'" class="mt-md flex items-center justify-center">
            <button
              class="badge-pill hover:bg-surface-cream-strong transition-colors"
              @click="activeFilter = 'all'"
            >
              已筛选：{{ activeFilter }} · 点击重置 ×
            </button>
          </div>
        </div>

        <!-- 聚类类别分布：点击跳转聚类分析页 -->
        <div class="card">
          <div class="flex items-center justify-between mb-lg">
            <h2 class="text-title-lg font-medium text-ink">聚类类别分布</h2>
            <span class="text-caption text-muted">点击查看详情</span>
          </div>
          <div class="h-56">
            <BarChart :data="clusterChartData" @select="goClustering" />
          </div>
          <button
            class="w-full mt-md text-caption text-primary hover:text-primary-active transition-colors"
            @click="goClustering()"
          >
            前往聚类分析页 →
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { store, loadData } from '../store'
import BarChart from '../components/charts/BarChart.vue'
import DoughnutChart from '../components/charts/DoughnutChart.vue'

const router = useRouter()

// ===== 数据源 =====
const hotsearchRecords = computed(() => store.data.hotsearchRecords)
const hourlyDistribution = computed(() => store.data.hourlyDistribution)
const labelDistribution = computed(() => store.data.labelDistribution)
const clusterDistribution = computed(() => store.data.clusterDistribution)
const hourlyTopics = computed(() => store.data.hourlyTopics || [])

const lastCrawl = computed(() => store.data.dataMeta.last_crawl || '未知')
const totalRecords = computed(() => store.data.dataMeta.total_records ?? 0)
const dataFresh = computed(() => store.data.dataStatus.fresh)
const ageHours = computed(() => store.data.dataStatus.age_hours ?? '—')

// ===== 交互状态 =====
const activeFilter = ref('all')   // all / 热 / 新 / 沸 / 无
const keyword = ref('')
const sortMode = ref('rank')      // rank=榜单排名 / hot=热度优先
const activeHour = ref(null)      // '14:00' / null

const filters = [
  { label: '全部', value: 'all' },
  { label: '热', value: '热' },
  { label: '新', value: '新' },
  { label: '沸', value: '沸' },
  { label: '无', value: '无' }
]

const sorts = [
  { label: '榜单排名', value: 'rank' },
  { label: '热度优先', value: 'hot' }
]

const tabCounts = computed(() => {
  const counts = { all: hotsearchRecords.value.length }
  hotsearchRecords.value.forEach(item => {
    const label = item.label || '无'
    counts[label] = (counts[label] || 0) + 1
  })
  return counts
})

const filteredData = computed(() => {
  let list = hotsearchRecords.value
  if (activeFilter.value !== 'all') {
    list = list.filter(item => (item.label || '无') === activeFilter.value)
  }
  const kw = keyword.value.trim()
  if (kw) {
    list = list.filter(item => item.title.includes(kw))
  }
  return [...list].sort((a, b) =>
    sortMode.value === 'hot' ? b.hot_value - a.hot_value : a.rank - b.rank
  )
})

const maxHot = computed(() =>
  Math.max(...hotsearchRecords.value.map(i => i.hot_value), 1)
)

const hotPercent = (value) => Math.round((value / maxHot.value) * 100)

// ===== 图表数据 =====
const topTopicsChartData = computed(() => {
  const top = [...hotsearchRecords.value]
    .sort((a, b) => b.hot_value - a.hot_value)
    .slice(0, 10)
  return {
    labels: top.map(item => item.title.length > 12 ? item.title.slice(0, 12) + '…' : item.title),
    datasets: [{
      label: '热度',
      data: top.map(item => Math.round(item.hot_value / 10000)),
      backgroundColor: '#cc785c',
      borderRadius: 6
    }]
  }
})

const hourlyChartData = computed(() => ({
  labels: hourlyDistribution.value.map(item => item.hour),
  datasets: [{
    label: '上榜次数',
    data: hourlyDistribution.value.map(item => item.count),
    backgroundColor: hourlyDistribution.value.map(item =>
      item.hour === activeHour.value ? '#a9583e' : '#cc785c'
    ),
    borderRadius: 6,
    barThickness: 14
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

const clusterChartData = computed(() => ({
  labels: clusterDistribution.value.map(item => item.cluster_name),
  datasets: [{
    label: '话题数',
    data: clusterDistribution.value.map(item => item.count),
    backgroundColor: ['#cc785c', '#5db8a6', '#e8a55a', '#5db872', '#c64545', '#6c6a64'],
    borderRadius: 6
  }]
}))

const activeHourTopics = computed(() =>
  hourlyTopics.value.find(h => h.hour === activeHour.value)?.topics || []
)

// ===== 交互处理 =====
// 点击小时柱：展开/收起该时段上榜TOP5
const onSelectHour = ({ label }) => {
  activeHour.value = activeHour.value === label ? null : label
}

// 点击标签扇区：同步左侧榜单筛选（与 tab 联动）
const onSelectLabel = ({ label }) => {
  const value = ['热', '新', '沸', '无'].includes(label) ? label : 'all'
  activeFilter.value = activeFilter.value === value ? 'all' : value
}

// 点击聚类分布 / 底部链接：前往聚类分析页
const goClustering = () => router.push('/clustering')

const getRankClass = (rank) => {
  if (rank === 0) return 'bg-primary text-on-primary'
  if (rank === 1) return 'bg-accent-amber text-ink'
  if (rank === 2) return 'bg-accent-teal text-ink'
  return 'bg-surface-soft text-muted'
}

const formatHotValue = (value) => {
  if (value == null) return '—'
  if (value >= 10000) {
    return (value / 10000).toFixed(1) + '万'
  }
  return Math.round(value).toString()
}

const refreshData = () => loadData()
</script>
