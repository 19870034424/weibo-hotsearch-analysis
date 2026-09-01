<template>
  <div class="py-section">
    <div class="mb-xl">
      <h1 class="font-display text-display-lg text-ink tracking-[-1px] mb-sm">
        智能问答
      </h1>
      <p class="text-body">
        基于阿里云 Qwen 大模型，结合当前真实热搜数据回答你的问题
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-xl">
      <!-- 对话主区域 -->
      <div class="lg:col-span-2 card flex flex-col" style="height: 560px">
        <!-- 消息列表 -->
        <div ref="messagesEl" class="flex-1 overflow-y-auto space-y-md p-lg">
          <div v-if="messages.length === 0" class="text-center py-2xl">
            <div class="text-display-lg font-display text-primary mb-md">🤖</div>
            <p class="text-body-md text-ink mb-sm">你好，我是热搜数据分析助手</p>
            <p class="text-body-sm text-muted">可以问我当前的热搜话题、情感倾向、异常波动等，试试下面的推荐问题</p>
          </div>

          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[80%] px-md py-sm rounded-lg text-body-md"
              :class="msg.role === 'user'
                ? 'bg-primary text-on-primary'
                : msg.isError
                  ? 'bg-error/10 text-error'
                  : 'bg-surface-soft text-ink'"
            >
              <span class="whitespace-pre-wrap">{{ msg.content }}</span>
            </div>
          </div>

          <div v-if="loading" class="flex justify-start">
            <div class="bg-surface-soft px-md py-sm rounded-lg text-body-md text-muted">
              正在思考…
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="border-t border-hairline p-md">
          <div class="flex items-center gap-sm">
            <input
              v-model="input"
              type="text"
              class="flex-1 px-md py-sm rounded-lg bg-surface-soft border border-hairline text-body-md text-ink outline-none focus:border-primary transition-colors"
              placeholder="输入你的问题，例如：现在有什么爆款话题？"
              :disabled="loading"
              @keydown.enter="send"
            />
            <button class="button-primary" :disabled="loading || !input.trim()" @click="send">
              发送
            </button>
          </div>
        </div>
      </div>

      <!-- 侧栏：推荐问题 + 数据概要 -->
      <div class="space-y-xl">
        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">推荐问题</h2>
          <div class="space-y-sm">
            <button
              v-for="q in suggestions"
              :key="q"
              class="w-full text-left px-md py-sm rounded-lg bg-surface-soft hover:bg-surface-soft/70 transition-colors text-body-sm text-ink"
              :disabled="loading"
              @click="ask(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>

        <div class="card">
          <h2 class="text-title-lg font-medium text-ink mb-lg">数据上下文</h2>
          <div class="space-y-md">
            <div class="flex justify-between items-center">
              <span class="text-body-sm text-muted">数据爬取于</span>
              <span class="text-body-sm font-medium text-ink">{{ lastCrawl }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-body-sm text-muted">总记录数</span>
              <span class="text-body-sm font-medium text-ink">{{ totalRecords }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-body-sm text-muted">独立话题</span>
              <span class="text-body-sm font-medium text-ink">{{ uniqueTopics }}</span>
            </div>
          </div>
          <p class="text-caption text-muted mt-lg">
            回答基于以上真实爬取数据；模型为通义千问（qwen-plus）
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { store } from '../store'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const messagesEl = ref(null)

const suggestions = [
  '现在最火的话题是什么？',
  '总结一下当前热搜榜单',
  '有哪些话题可能正在爆发？',
  '帮我分析一下今天的情感倾向'
]

const lastCrawl = computed(() => store.data.dataMeta.last_crawl || '—')
const totalRecords = computed(() => store.data.dataMeta.total_records ?? '—')
const uniqueTopics = computed(() => store.data.dataMeta.unique_topics ?? '—')

const scrollToBottom = async () => {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

const send = async () => {
  const text = input.value.trim()
  if (!text || loading.value) return
  await ask(text)
  input.value = ''
}

const ask = async (text) => {
  if (!text || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  scrollToBottom()

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: messages.value
          .filter(m => !m.isError)
          .slice(-10)
          .map(({ role, content }) => ({ role, content }))
      })
    })
    const body = await res.json().catch(() => ({}))

    if (!res.ok) {
      messages.value.push({
        role: 'assistant',
        content: body.detail || `请求失败（${res.status}）`,
        isError: true
      })
    } else {
      messages.value.push({ role: 'assistant', content: body.reply })
    }
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '网络错误：无法连接后端服务，请确认 API 服务器已启动',
      isError: true
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>
