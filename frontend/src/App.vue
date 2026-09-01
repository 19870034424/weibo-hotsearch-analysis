<template>
  <div class="min-h-screen bg-canvas">
    <TopNav />
    <main class="max-w-7xl mx-auto px-md">
      <!-- 后端连接失败 -->
      <div v-if="store.error" class="py-section">
        <div class="card text-center py-2xl">
          <div class="text-display-lg font-display text-error mb-md">⚠️</div>
          <h2 class="text-title-lg font-medium text-ink mb-sm">无法连接后端服务</h2>
          <p class="text-body text-muted max-w-xl mx-auto mb-lg">{{ store.error }}</p>
          <button class="button-primary" @click="retry">重试连接</button>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-else-if="!store.loaded" class="py-section">
        <div class="card text-center py-2xl">
          <div class="text-display-lg font-display text-primary mb-md animate-pulse">…</div>
          <p class="text-body text-muted">正在加载热搜分析数据…</p>
        </div>
      </div>

      <router-view v-else />
    </main>
    <Footer />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import TopNav from './components/TopNav.vue'
import Footer from './components/Footer.vue'
import { store, loadData } from './store'

onMounted(() => {
  loadData()
  // 自动刷新：每分钟拉取一次最新数据（自动监控模式下后端会持续产出新数据）
  refreshTimer = setInterval(() => {
    if (document.visibilityState === 'visible') loadData()
  }, 60000)
})

let refreshTimer = null
onUnmounted(() => clearInterval(refreshTimer))

const retry = () => loadData()
</script>
