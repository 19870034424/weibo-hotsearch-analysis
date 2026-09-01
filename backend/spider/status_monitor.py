import json
import logging
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CrawlStatus:
    timestamp: str
    success_count: int
    fail_count: int
    duration: float
    is_success: bool
    error_message: str = ""


class StatusMonitor:
    def __init__(self, config: Dict):
        self.config = config
        self.log_path = config['monitor']['log_path']
        self.report_path = config['monitor']['report_path']
        self.max_fail_rate = config['monitor']['max_fail_rate']
        self.slow_request_threshold = config['monitor']['slow_request_threshold']

        self.status_history: List[CrawlStatus] = []
        self.daily_stats = defaultdict(lambda: {
            'total_crawls': 0,
            'success_crawls': 0,
            'fail_crawls': 0,
            'total_duration': 0,
            'total_records': 0
        })

        self._ensure_log_dir()
        self._load_history()

    def _ensure_log_dir(self):
        import os
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    def _load_history(self):
        """从 JSONL 日志恢复历史统计，进程重启后报告不再清零"""
        import os
        if not os.path.exists(self.log_path):
            return

        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue  # 跳过被截断的半行

                    self.status_history.append(CrawlStatus(
                        timestamp=entry.get('timestamp', ''),
                        success_count=entry.get('success_count', 0),
                        fail_count=entry.get('fail_count', 0),
                        duration=entry.get('duration', 0.0),
                        is_success=entry.get('is_success', False),
                        error_message=entry.get('error_message', '')
                    ))

                    day = entry.get('timestamp', '')[:10]
                    if not day:
                        continue
                    self.daily_stats[day]['total_crawls'] += 1
                    self.daily_stats[day]['total_duration'] += entry.get('duration', 0.0)
                    if entry.get('is_success') and entry.get('success_count', 0) > 0:
                        self.daily_stats[day]['success_crawls'] += 1
                        self.daily_stats[day]['total_records'] += entry['success_count']
                    else:
                        self.daily_stats[day]['fail_crawls'] += 1

            if self.status_history:
                logger.info(f"从状态日志恢复了 {len(self.status_history)} 条历史记录")
        except Exception as e:
            logger.warning(f"读取状态日志失败（将从空白统计开始）: {e}")

    def record(self, success_count: int, fail_count: int, duration: float, is_success: bool = True, error_message: str = ""):
        status = CrawlStatus(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            success_count=success_count,
            fail_count=fail_count,
            duration=duration,
            is_success=is_success,
            error_message=error_message
        )

        self.status_history.append(status)

        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_stats[today]['total_crawls'] += 1
        self.daily_stats[today]['total_duration'] += duration

        if is_success and success_count > 0:
            self.daily_stats[today]['success_crawls'] += 1
            self.daily_stats[today]['total_records'] += success_count
        else:
            self.daily_stats[today]['fail_crawls'] += 1

        self._write_to_log(status)

        if duration > self.slow_request_threshold:
            logger.warning(f"慢请求警告: 本次爬取耗时 {duration:.2f}秒，超过阈值 {self.slow_request_threshold}秒")

        fail_rate = fail_count / (success_count + fail_count) if (success_count + fail_count) > 0 else 0
        if fail_rate > self.max_fail_rate:
            logger.warning(f"高失败率警告: 当前失败率 {fail_rate:.1%}，超过阈值 {self.max_fail_rate:.1%}")

    def _write_to_log(self, status: CrawlStatus):
        log_entry = json.dumps(asdict(status), ensure_ascii=False)

        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            logger.error(f"状态日志写入失败: {e}")

    def generate_report(self) -> Dict:
        today = datetime.now().strftime('%Y-%m-%d')
        stats = self.daily_stats[today]

        if stats['total_crawls'] == 0:
            return {
                'date': today,
                'status': 'no_data',
                'message': '今日暂无爬取记录'
            }

        avg_duration = stats['total_duration'] / stats['total_crawls'] if stats['total_crawls'] > 0 else 0
        success_rate = stats['success_crawls'] / stats['total_crawls'] if stats['total_crawls'] > 0 else 0
        fail_rate = stats['fail_crawls'] / stats['total_crawls'] if stats['total_crawls'] > 0 else 0
        avg_records = stats['total_records'] / stats['success_crawls'] if stats['success_crawls'] > 0 else 0

        recent_statuses = self.status_history[-10:] if len(self.status_history) >= 10 else self.status_history
        recent_success = sum(1 for s in recent_statuses if s.is_success and s.success_count > 0)
        recent_fail = sum(1 for s in recent_statuses if not s.is_success or s.success_count == 0)

        health_status = "healthy"
        if fail_rate > self.max_fail_rate or recent_fail > recent_success:
            health_status = "warning"
        if fail_rate > 0.5 or recent_fail > recent_success * 2:
            health_status = "critical"

        report = {
            'date': today,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'health_status': health_status,
            'today_stats': {
                'total_crawls': stats['total_crawls'],
                'success_crawls': stats['success_crawls'],
                'fail_crawls': stats['fail_crawls'],
                'success_rate': f"{success_rate:.1%}",
                'fail_rate': f"{fail_rate:.1%}",
                'total_records': stats['total_records'],
                'avg_records_per_crawl': f"{avg_records:.1f}",
                'avg_duration': f"{avg_duration:.2f}秒"
            },
            'recent_health': {
                'last_10_crawls_success': recent_success,
                'last_10_crawls_fail': recent_fail
            },
            'alerts': []
        }

        if health_status == "warning":
            report['alerts'].append({
                'level': 'warning',
                'message': f"失败率偏高 ({fail_rate:.1%})，建议检查网络或代理设置"
            })
        elif health_status == "critical":
            report['alerts'].append({
                'level': 'critical',
                'message': f"失败率过高 ({fail_rate:.1%})，爬虫可能已被封禁，请立即检查"
            })

        if avg_duration > self.slow_request_threshold:
            report['alerts'].append({
                'level': 'info',
                'message': f"平均响应时间较长 ({avg_duration:.2f}秒)，可能存在网络问题"
            })

        try:
            with open(self.report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"健康报告已生成: {self.report_path}")
        except Exception as e:
            logger.error(f"健康报告生成失败: {e}")

        return report

    def print_report(self):
        report = self.generate_report()

        print("\n" + "=" * 60)
        print(f"📊 微博热搜爬虫健康报告 - {report['date']}")
        print("=" * 60)

        health_status = report.get('health_status', 'no_data')

        health_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '🚨',
            'no_data': '❓'
        }

        health_text = {
            'healthy': '健康',
            'warning': '警告',
            'critical': '危险',
            'no_data': '无数据'
        }

        print(f"\n{health_emoji.get(health_status, '❓')} 运行状态: {health_text.get(health_status, '未知')}")

        if health_status != 'no_data':
            stats = report['today_stats']
            print(f"\n📈 今日统计:")
            print(f"   总爬取次数: {stats['total_crawls']}")
            print(f"   成功次数: {stats['success_crawls']} | 失败次数: {stats['fail_crawls']}")
            print(f"   成功率: {stats['success_rate']} | 失败率: {stats['fail_rate']}")
            print(f"   总记录数: {stats['total_records']}")
            print(f"   平均每次记录: {stats['avg_records_per_crawl']}")
            print(f"   平均耗时: {stats['avg_duration']}")

            recent = report['recent_health']
            print(f"\n🔍 最近10次健康状况:")
            print(f"   成功: {recent['last_10_crawls_success']} | 失败: {recent['last_10_crawls_fail']}")

            if report['alerts']:
                print(f"\n🚨 告警信息:")
                for alert in report['alerts']:
                    print(f"   [{alert['level'].upper()}] {alert['message']}")

            print(f"\n📝 生成时间: {report['generated_at']}")
        else:
            print(f"\n📝 生成时间: {report.get('generated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")

        print("=" * 60 + "\n")

    def get_total_records(self) -> int:
        return sum(stats['total_records'] for stats in self.daily_stats.values())

    def get_run_days(self) -> int:
        return len(self.daily_stats)
