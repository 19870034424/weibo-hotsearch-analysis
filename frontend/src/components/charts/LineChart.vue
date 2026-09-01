<template>
  <div ref="containerRef" class="relative w-full h-full min-h-[1px]">
    <canvas ref="chartCanvas" class="block w-full h-full"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue'
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

Chart.register(
  LineController,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps({
  data: {
    type: Object,
    required: true
  }
})

const containerRef = ref(null)
const chartCanvas = ref(null)
let chartInstance = null
let resizeObserver = null

const createChart = () => {
  if (!chartCanvas.value || !containerRef.value) return

  const canvas = chartCanvas.value
  const container = containerRef.value
  const rect = container.getBoundingClientRect()

  if (rect.width < 1 || rect.height < 1) return

  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }

  chartInstance = new Chart(canvas, {
    type: 'line',
    data: props.data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#3d3d3a',
            padding: 20,
            usePointStyle: true,
            font: { size: 13 }
          }
        },
        tooltip: {
          backgroundColor: '#181715',
          titleColor: '#faf9f5',
          bodyColor: '#a09d96',
          padding: 12,
          cornerRadius: 8
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#6c6a64', font: { size: 12 } }
        },
        y: {
          grid: { color: '#ebe6df' },
          ticks: { color: '#6c6a64', font: { size: 12 } }
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    }
  })
}

onMounted(() => {
  nextTick(() => {
    createChart()
  })

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
