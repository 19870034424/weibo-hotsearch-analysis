<template>
  <header class="sticky top-0 z-50 bg-canvas border-b border-hairline">
    <nav class="max-w-7xl mx-auto px-md h-16 flex items-center justify-between">
      <div class="flex items-center gap-md">
        <div class="flex items-center gap-sm">
          <div class="w-8 h-8 flex items-center justify-center">
            <svg viewBox="0 0 24 24" class="w-6 h-6 text-primary">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>
              <path d="M12 2 L12 22 M2 12 L22 12" stroke="currentColor" stroke-width="2"/>
            </svg>
          </div>
          <span class="font-display text-display-sm text-ink font-normal tracking-[-0.3px]">
            热搜分析
          </span>
        </div>
      </div>
      
      <div class="hidden md:flex items-center gap-xl">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="text-nav-link font-medium text-body-strong hover:text-primary transition-colors duration-200"
          :class="{ 'text-primary': currentPath === item.path }"
        >
          {{ item.label }}
        </router-link>
      </div>

      <div class="flex items-center gap-md">
        <button class="button-primary" @click="refreshData">刷新数据</button>
      </div>

      <button 
        class="md:hidden button-icon-circular"
        @click="mobileMenuOpen = !mobileMenuOpen"
      >
        <svg viewBox="0 0 24 24" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2">
          <path v-if="!mobileMenuOpen" d="M4 6 L20 6 M4 12 L20 12 M4 18 L20 18"/>
          <path v-else d="M6 18 L18 6 M6 6 L18 18"/>
        </svg>
      </button>
    </nav>

    <div 
      v-if="mobileMenuOpen"
      class="md:hidden bg-canvas border-b border-hairline"
    >
      <div class="px-md py-lg space-y-sm">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="block text-nav-link font-medium text-body-strong hover:text-primary transition-colors duration-200 py-sm"
          :class="{ 'text-primary': currentPath === item.path }"
          @click="mobileMenuOpen = false"
        >
          {{ item.label }}
        </router-link>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { loadData } from '../store'

const route = useRoute()
const mobileMenuOpen = ref(false)

const navItems = [
  { label: '实时热搜', path: '/' },
  { label: '情感分析', path: '/sentiment' },
  { label: '词频分析', path: '/wordcloud' },
  { label: '聚类分析', path: '/clustering' },
  { label: '趋势预测', path: '/prediction' },
  { label: '异常检测', path: '/anomaly' },
  { label: '智能问答', path: '/chat' }
]

const currentPath = computed(() => route.path)

// 从后端重新拉取最新数据
const refreshData = () => loadData()
</script>
