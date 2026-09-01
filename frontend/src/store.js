import { reactive } from 'vue'

// 全局数据仓库：启动时从后端 /api/data 拉取真实分析结果
export const store = reactive({
  loaded: false,
  error: null,
  data: {
    dataMeta: {},
    dataStatus: {},
    hotsearchRecords: [],
    hourlyDistribution: [],
    labelDistribution: [],
    clusterDistribution: [],
    sentimentResults: [],
    sentimentTrend: [],
    clusteringResults: [],
    predictionResults: [],
    predictionMetrics: {},
    anomalyResults: [],
    anomalyStats: { total: 0, display_count: 0, involved_topics: 0, by_type: {} },
    hotTrendSeries: { labels: [], series: [] },
    wordFrequency: []
  }
})

export async function loadData() {
  try {
    const res = await fetch('/api/data')
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${res.status}`)
    }
    store.data = await res.json()
    store.loaded = true
    store.error = null
  } catch (e) {
    // 首次加载失败才展示错误页；已有数据时静默保留旧数据，等待下次自动刷新
    if (!store.loaded) {
      store.error = '无法连接后端服务，请先启动 API 服务器：打开终端，进入 backend 目录，运行 python api_server.py'
    }
  }
}
