import os
import sys
import logging
import argparse
from datetime import datetime

import yaml

from spider.scheduler import HotSearchScheduler


def setup_logging():
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(
                f'logs/spider_{datetime.now().strftime("%Y%m%d")}.log',
                encoding='utf-8'
            ),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def load_config(config_path: str = 'config.yaml') -> dict:
    if not os.path.exists(config_path):
        logging.error(f"配置文件不存在: {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def run_once(config: dict):
    logging.info("=" * 60)
    logging.info("🔄 单次运行模式")
    logging.info("=" * 60)

    scheduler = HotSearchScheduler(config)
    total_records = scheduler.run_once()

    logging.info(f"单次运行完成，总记录数: {total_records}")
    scheduler.monitor.print_report()


def run_continuous(config: dict):
    logging.info("=" * 60)
    logging.info("🔄 持续运行模式 (定时调度)")
    logging.info("=" * 60)

    scheduler = HotSearchScheduler(config)

    try:
        scheduler.start()

        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("\n用户手动停止")
        scheduler.stop()


def show_status(config: dict):
    from spider.status_monitor import StatusMonitor
    from spider.storage import create_storage

    logging.info("=" * 60)
    logging.info("📊 爬虫状态查询")
    logging.info("=" * 60)

    monitor = StatusMonitor(config)
    monitor.print_report()

    storage = create_storage(config)
    df = storage.load(limit=100)

    if not df.empty:
        logging.info(f"\n最近 {len(df)} 条记录:")
        logging.info(df[['rank', 'title', 'hot_value', 'crawl_time']].to_string())
    else:
        logging.info("\n暂无数据，请先运行爬虫")


def main():
    parser = argparse.ArgumentParser(description='微博热搜爬虫')
    parser.add_argument('--config', '-c', default='config.yaml', help='配置文件路径')
    parser.add_argument('--mode', '-m', choices=['once', 'continuous', 'status'],
                        default='once', help='运行模式: once(单次) / continuous(持续) / status(状态)')
    parser.add_argument('--interval', '-i', type=int, help='爬取间隔(分钟)，默认从配置文件读取')

    args = parser.parse_args()

    config = load_config(args.config)

    if args.interval:
        config['spider']['interval_minutes'] = args.interval

    setup_logging()

    if args.mode == 'once':
        run_once(config)
    elif args.mode == 'continuous':
        run_continuous(config)
    elif args.mode == 'status':
        show_status(config)


if __name__ == '__main__':
    main()
