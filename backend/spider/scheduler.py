import logging
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Dict

from spider.crawler import WeiboHotSearchCrawler
from spider.storage import create_storage
from spider.status_monitor import StatusMonitor

logger = logging.getLogger(__name__)


class HotSearchScheduler:
    def __init__(self, config: Dict):
        self.config = config
        self.interval_minutes = config['spider']['interval_minutes']
        self.interval_seconds = self.interval_minutes * 60

        self.crawler = WeiboHotSearchCrawler(config)
        self.storage = create_storage(config)
        self.monitor = StatusMonitor(config)

        self.is_running = False
        self.total_runs = 0
        self._stop_event = threading.Event()
        self._scheduler_thread = None

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info("收到停止信号，正在关闭调度器...")
        self.stop()
        sys.exit(0)

    def _scheduler_loop(self):
        while not self._stop_event.is_set():
            self.total_runs += 1
            logger.info(f"\n{'#' * 60}")
            logger.info(f"开始第 {self.total_runs} 次爬取任务")
            logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'#' * 60}")

            try:
                start_time = time.time()
                count, items = self.crawler.crawl()
                duration = time.time() - start_time

                if items:
                    self.storage.save(items)
                    self.monitor.record(
                        success_count=len(items),
                        fail_count=0,
                        duration=duration,
                        is_success=True
                    )
                    logger.info(f"✅ 第 {self.total_runs} 次爬取成功，获取 {len(items)} 条记录")
                else:
                    self.monitor.record(
                        success_count=0,
                        fail_count=1,
                        duration=duration,
                        is_success=False,
                        error_message="未获取到任何热搜数据"
                    )
                    logger.warning(f"⚠️ 第 {self.total_runs} 次爬取失败，未获取到数据")

            except Exception as e:
                logger.error(f"❌ 第 {self.total_runs} 次爬取异常: {e}")
                self.monitor.record(
                    success_count=0,
                    fail_count=1,
                    duration=time.time() - start_time if 'start_time' in locals() else 0,
                    is_success=False,
                    error_message=str(e)
                )

            logger.info(f"📊 当前状态: 共运行 {self.total_runs} 次 | "
                       f"总记录数 {self.monitor.get_total_records()} | "
                       f"运行天数 {self.monitor.get_run_days()}")

            self._stop_event.wait(self.interval_seconds)

    def start(self):
        if self.is_running:
            logger.warning("调度器已在运行中")
            return

        self.is_running = True
        self._stop_event.clear()

        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

        logger.info("=" * 60)
        logger.info("🎉 微博热搜爬虫调度器启动成功!")
        logger.info(f"   爬取间隔: 每 {self.interval_minutes} 分钟")
        logger.info(f"   日志路径: {self.config['monitor']['log_path']}")
        logger.info(f"   健康报告: {self.config['monitor']['report_path']}")
        logger.info("   按 Ctrl+C 停止")
        logger.info("=" * 60)

        self.monitor.print_report()

        while self._scheduler_thread.is_alive():
            time.sleep(1)

    def stop(self):
        if not self.is_running:
            return

        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)

        self.is_running = False

        logger.info("调度器已停止")
        self.monitor.print_report()

    def run_once(self):
        self.total_runs += 1
        logger.info(f"\n{'#' * 60}")
        logger.info(f"开始第 {self.total_runs} 次爬取任务 (单次模式)")
        logger.info(f"{'#' * 60}")

        try:
            start_time = time.time()
            count, items = self.crawler.crawl()
            duration = time.time() - start_time

            if items:
                self.storage.save(items)
                self.monitor.record(
                    success_count=len(items),
                    fail_count=0,
                    duration=duration,
                    is_success=True
                )
                logger.info(f"✅ 爬取成功，获取 {len(items)} 条记录")
            else:
                self.monitor.record(
                    success_count=0,
                    fail_count=1,
                    duration=duration,
                    is_success=False,
                    error_message="未获取到任何热搜数据"
                )
                logger.warning(f"⚠️ 爬取失败，未获取到数据")

        except Exception as e:
            logger.error(f"❌ 爬取异常: {e}")
            self.monitor.record(
                success_count=0,
                fail_count=1,
                duration=time.time() - start_time if 'start_time' in locals() else 0,
                is_success=False,
                error_message=str(e)
            )

        return self.monitor.get_total_records()
