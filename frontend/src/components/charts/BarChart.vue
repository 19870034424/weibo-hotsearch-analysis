<template>
  <div ref="containerRef" class="relative w-full h-full min-h-[1px]">
    <canvas ref="chartCanvas" class="block w-full h-full"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue'
import {
  Chart,
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

Chart.register(
  BarController,
  BarElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend
)

const props = defineProps({
  data: {
    type: Object,
    required: true
  },
  // 横向条形图（适合较长的中文类目标签）
  horizontal: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select'])

const containerRef = ref(null)
const chartCanvas = ref(null)
let chartInstance = null
let resizeObserver = null

const createChart = () => {
  if (!chartCanvas.value || !containerRef.value) return

  const canvas = chartCanvas.value
  const container = containerRef.value
  const rect = container.getBoundingClientRect()

  // 确保容器有非零尺寸，否则不创建
  if (rect.width < 1 || rect.height < 1) return

  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }

  chartInstance = new Chart(canvas, {
    type: 'bar',
    data: props.data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      indexAxis: props.horizontal ? 'y' : 'x',
      // 容差命中：细柱条不必精确点中，点附近即可触发（nearest 模式）
      interaction: { mode: 'nearest', intersect: false },
      onHover: (e, elements) => {
        e.native.target.style.cursor = elements.length ? 'pointer' : 'default'
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: '#181715',
          titleColor: '#faf9f5',
          bodyColor: '#a09d96',
          padding: 12,
          cornerRadius: 8,
          displayColors: false
        }
      },
      // 点击柱条时向父组件抛出选中的类目
      onClick: (e, elements, chart) => {
        if (!elements || !elements.length) return
        const el = elements[0]
        emit('select', {
          index: el.index,
          label: chart.data.labels[el.index],
          value: chart.data.datasets[el.datasetIndex]?.data?.[el.index]
        })
      },
      scales: props.horizontal
        ? {
            x: {
              grid: { color: '#ebe6df' },
              ticks: { color: '#6c6a64', font: { size: 12 } }
            },
            y: {
              grid: { display: false },
              ticks: { color: '#6c6a64', font: { size: 12 } }
            }
          }
        : {
            x: {
              grid: { display: false },
              ticks: { color: '#6c6a64', font: { size: 12 } }
            },
            y: {
              grid: { color: '#ebe6df' },
              ticks: { color: '#6c6a64', font: { size: 12 } }
            }
          }
    }
  })
}

onMounted(() => {
  // 等待 DOM 完成一轮 layout
  nextTick(() => {
    createChart()
  })

  // ResizeObserver 监听容器尺寸变化，等容器有尺寸后再创建
  if (containerRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          createChart()
          break
        }
      }
    })
    resizeObserver.observe(containerRef.value)
  } else {
    // 兜底：定时重试
    let tries = 0
    const timer = setInterval(() => {
      tries++
      if (chartInstance || tries > 10) {
        clearInterval(timer)
        return
      }
      createChart()
    }, 100)
  }
})

watch(() => props.data, () => {
  createChart()
}, { deep: true })

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>
