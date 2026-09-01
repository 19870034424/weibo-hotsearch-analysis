import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    proxy: {
      // 开发模式下把 /api 请求转发到 FastAPI 后端
      '/api': 'http://127.0.0.1:8000'
    }
  }
})
