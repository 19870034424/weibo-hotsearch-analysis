"""
微博热搜监控系统 - API 服务器（一体化常驻服务）

一个进程完成整个系统：
- 定时自动爬取热搜 → 自动重跑分析流水线（后台线程，无需人工干预）
- GET  /api/data     全量真实分析数据（供 Vue 前端渲染）
- POST /api/chat     智能问答（代理阿里云 Qwen，自动附带热搜上下文）
- GET  /api/monitor  自动监控运行状态
- GET  /api/health   健康检查
- /                  托管 frontend/dist 静态文件（也可只用 Vite 开发模式）

启动: cd backend && python api_server.py            （默认开启自动监控）
      python api_server.py --no-monitor                    （只做数据服务，不自动爬取）
"""
import os
import sys
import logging
import threading
import subprocess
from datetime import datetime
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data_service import build_payload
from chat.qwen_client import QwenClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config() -> Dict:
    with open(os.path.join(BASE_DIR, 'config.yaml'), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class AutoMonitor:
    """
    自动监控循环：爬取 -> 分析 -> 等待下一轮。

    这是系统"实时"能力的核心：爬取在进程内直接调用爬虫模块（注意不能复用
    HotSearchScheduler，其构造函数里 signal.signal 只能在主线程调用）；
    分析跑在子进程里，避免 sklearn/xgboost 等污染 API 进程。
    """

    def __init__(self, config: Dict):
        self.interval_seconds = int(config['spider']['interval_minutes']) * 60
        self._stop_event = threading.Event()
        self._thread = None
        self.state = {
            'enabled': True,
            'interval_minutes': config['spider']['interval_minutes'],
            'runs': 0,
            'last_run': None,
            'last_crawl_count': 0,
            'last_analysis_ok': None,
            'error': None,
        }

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name='auto-monitor')
        self._thread.start()
        logger.info(f"自动监控已启动：每 {self.state['interval_minutes']} 分钟爬取并分析一轮")

    def stop(self):
        self._stop_event.set()

    def _loop(self):
        # 启动后立即跑一轮，保证服务一起来数据就是新的
        while not self._stop_event.is_set():
            try:
                self._run_cycle()
            except Exception as e:
                self.state['error'] = str(e)
                logger.error(f"自动监控周期执行失败: {e}")
            self._stop_event.wait(self.interval_seconds)

    def _run_cycle(self):
        from spider.crawler import WeiboHotSearchCrawler
        from spider.storage import create_storage

        config = load_config()
        crawler = WeiboHotSearchCrawler(config)
        storage = create_storage(config)

        _, items = crawler.crawl()
        if items:
            storage.save(items)
        logger.info(f"[自动监控] 爬取完成: {len(items)} 条")

        proc = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, 'run_analysis.py'), '--method', 'all'],
            cwd=BASE_DIR, capture_output=True, text=True, timeout=900
        )
        analysis_ok = proc.returncode == 0
        if not analysis_ok:
            logger.error(f"[自动监控] 分析失败:\n{proc.stderr[-2000:]}")
        else:
            logger.info("[自动监控] 分析流水线完成")

        self.state.update(
            runs=self.state['runs'] + 1,
            last_run=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            last_crawl_count=len(items),
            last_analysis_ok=analysis_ok,
            error=None,
        )


app = FastAPI(title="微博热搜分析系统 API")

# 允许 Vite 开发服务器跨域访问（生产模式走同源静态托管，不需要 CORS）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

monitor: AutoMonitor = None


@app.on_event("startup")
def startup():
    global monitor
    if os.environ.get("AUTO_MONITOR", "1") == "1":
        monitor = AutoMonitor(load_config())
        monitor.start()
    else:
        logger.info("自动监控未启用（--no-monitor）")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/monitor")
def monitor_status():
    return monitor.state if monitor else {"enabled": False}


@app.get("/api/data")
def get_data():
    """全量分析数据。每次请求实时读取 CSV，爬虫/分析更新后前端刷新即见最新"""
    try:
        return build_payload()
    except Exception as e:
        logger.error(f"构建数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"构建数据失败: {e}")


class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post("/api/chat")
def chat(req: ChatRequest):
    """智能问答：系统上下文(最新热搜) + 最近对话历史 + 当前问题，交给 Qwen"""
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="问题不能为空")
    if len(message) > 2000:
        raise HTTPException(status_code=400, detail="问题过长（最多2000字符）")

    client = QwenClient()
    if not client.api_key:
        raise HTTPException(
            status_code=503,
            detail="未配置Qwen API密钥：请在 backend/config/api_keys.yaml 填入 api_key，"
                   "或设置环境变量 QWEN_API_KEY，然后重启 API 服务"
        )

    # 只保留最近10轮历史，避免请求过长
    history = [
        {"role": m.get("role", "user"), "content": str(m.get("content", ""))[:2000]}
        for m in req.history[-10:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]

    context = build_payload().get("chatContext", "")
    messages = []
    if context:
        messages.append({
            "role": "system",
            "content": f"你是一个微博热搜数据分析助手。以下是当前热搜数据的上下文信息：\n{context}\n\n"
                       f"请基于这些信息回答用户问题。"
        })
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    reply = client.generate_response(messages)
    if reply is None:
        raise HTTPException(status_code=502, detail="调用Qwen失败，请检查API密钥是否有效、网络是否可用")

    return {"reply": reply}


# 生产模式：托管前端构建产物（放在 API 路由之后，不影响 /api/*）
_frontend_dist = os.path.normpath(os.path.join(BASE_DIR, '..', 'frontend', 'dist'))
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
    logger.info(f"已托管前端静态文件: {_frontend_dist}")


if __name__ == '__main__':
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description='微博热搜监控系统 API 服务器')
    parser.add_argument('--no-monitor', action='store_true', help='禁用自动监控（只做数据服务）')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()

    if args.no_monitor:
        os.environ['AUTO_MONITOR'] = '0'

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
