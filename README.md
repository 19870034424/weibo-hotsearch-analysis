# 微博热搜实时监控系统

基于微博热搜 API 的实时采集、分析与可视化系统。一个常驻服务自动完成「爬取 → 分析 → 服务」全流程，Vue 前端实时呈现分析结果，并支持基于大模型的智能问答。

## 架构

```
爬虫(scheduler/crawler) ──→ CSV 存储 ──→ 分析流水线(聚类/预测/情感/词云/异常)
        ↑                                        │
        └──── AutoMonitor 循环（每15分钟）←───────┘
                          │
                    api_server.py (FastAPI)
                          │  /api/data  /api/chat
                    Vue 3 前端（唯一界面）
```

- **自动监控**：API 服务内置后台线程，定时爬取热搜并自动重跑分析流水线，全程无需人工干预
- **单一数据出口**：`data_service.py` 统一定义所有数据口径，API 实时读取分析产物

## 功能

| 页面 | 内容 |
|------|------|
| 实时热搜 | 最新榜单、小时分布、标签分布、聚类类别分布 |
| 情感分析 | 话题标题情感打分（SnowNLP）、极性占比与小时趋势 |
| 词频分析 | jieba 分词词频、词云展示 |
| 聚类分析 | K-Means 生命周期聚类（轮廓系数自动寻优 K） |
| 趋势预测 | 时间外推任务：用历史上榜记录预测下一时刻能否进入 TOP10/TOP5 |
| 异常检测 | 热度异常、排名突变、爆款话题、新晋/消失话题（统计法 + 孤立森林） |
| 智能问答 | 基于当前热搜数据的 Qwen 大模型问答 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r backend/requirements.txt
cd frontend && npm install

# 2. 配置（可选）
#    - 微博 Cookie: backend/config.yaml 的 spider.cookie（不填可能被反爬拦截）
#    - Qwen 密钥:   backend/config/api_keys.yaml（智能问答用）

# 3. 启动一体化服务（自动爬取 + 自动分析 + API + 前端托管）
cd backend && python api_server.py

# 4. 打开界面（二选一）
#    http://localhost:8000        ← 生产模式，单服务即可
#    cd frontend && npm run dev   ← 开发模式，http://localhost:5173
```

## 诚实边界

- **情感分析对象是话题标题**而非网友评论，反映话题措辞色彩，不等同于公众情绪；SnowNLP 训练语料为电商评论，对新闻类标题仅供参考
- **预测任务在数据积累初期指标偏高**（相邻快照排名变化小），随数据跨度和密度增长趋于真实水平
- 热搜数据来源于微博公开接口，仅用于学习研究

## 技术栈

Python（FastAPI / pandas / scikit-learn / XGBoost / jieba / SnowNLP）· Vue 3（Vite / Tailwind / Chart.js）
