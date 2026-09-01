import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Hotsearch',
    component: () => import('../views/HotsearchView.vue')
  },
  {
    path: '/sentiment',
    name: 'Sentiment',
    component: () => import('../views/SentimentView.vue')
  },
  {
    path: '/wordcloud',
    name: 'Wordcloud',
    component: () => import('../views/WordcloudView.vue')
  },
  {
    path: '/clustering',
    name: 'Clustering',
    component: () => import('../views/ClusteringView.vue')
  },
  {
    path: '/prediction',
    name: 'Prediction',
    component: () => import('../views/PredictionView.vue')
  },
  {
    path: '/anomaly',
    name: 'Anomaly',
    component: () => import('../views/AnomalyView.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/ChatView.vue')
  },
  // 未匹配的路由一律回到首页
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
