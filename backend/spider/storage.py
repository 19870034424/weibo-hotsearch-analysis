import os
import csv
import json
import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

import pandas as pd

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    @abstractmethod
    def save(self, items: List) -> bool:
        pass

    @abstractmethod
    def load(self, limit: int = None) -> pd.DataFrame:
        pass


class CSVStorage(BaseStorage):
    def __init__(self, config: Dict):
        self.config = config
        self.csv_path = config['storage']['csv_path']
        self.encoding = config['storage']['encoding']
        self.partition_enabled = config['storage'].get('partition_enabled', False)
        self.partition_path = config['storage'].get('partition_path', 'data/partitions')

        os.makedirs(os.path.dirname(self.csv_path) if os.path.dirname(self.csv_path) else '.', exist_ok=True)
        if self.partition_enabled:
            os.makedirs(self.partition_path, exist_ok=True)

        self.fieldnames = ['rank', 'title', 'hot_value', 'label', 'category', 'link', 'img_url', 'crawl_time']
        # 调度器在后台线程写文件，加锁避免并发追加交错
        self._write_lock = threading.Lock()

    def save(self, items: List) -> bool:
        try:
            with self._write_lock:
                file_exists = os.path.exists(self.csv_path) and os.path.getsize(self.csv_path) > 0

                with open(self.csv_path, 'a', newline='', encoding=self.encoding) as f:
                    writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                    if not file_exists:
                        writer.writeheader()
                    for item in items:
                        if hasattr(item, '__dict__'):
                            writer.writerow(item.__dict__)
                        else:
                            writer.writerow(item)

            logger.info(f"成功保存 {len(items)} 条记录到CSV: {self.csv_path}")

            if self.partition_enabled:
                self._save_partition(items)

            return True

        except Exception as e:
            logger.error(f"CSV存储失败: {e}")
            return False

    def _save_partition(self, items: List):
        if not items:
            return

        try:
            now = datetime.now()
            if self.config['storage'].get('partition_by', 'day') == 'hour':
                partition_file = os.path.join(self.partition_path, f"{now.strftime('%Y%m%d_%H')}.csv")
            else:
                partition_file = os.path.join(self.partition_path, f"{now.strftime('%Y%m%d')}.csv")

            df = pd.DataFrame([item.__dict__ if hasattr(item, '__dict__') else item for item in items])

            with self._write_lock:
                if os.path.exists(partition_file):
                    existing_df = pd.read_csv(partition_file, encoding=self.encoding)
                    df = pd.concat([existing_df, df], ignore_index=True)

                # 先写临时文件再替换，避免进程中断留下半个文件
                tmp_file = partition_file + '.tmp'
                df.to_csv(tmp_file, index=False, encoding=self.encoding)
                os.replace(tmp_file, partition_file)
            logger.debug(f"分区存储完成: {partition_file}")

        except Exception as e:
            logger.warning(f"分区存储失败: {e}")

    def load(self, limit: int = None) -> pd.DataFrame:
        try:
            if not os.path.exists(self.csv_path):
                logger.warning(f"CSV文件不存在: {self.csv_path}")
                return pd.DataFrame()

            df = pd.read_csv(self.csv_path, encoding=self.encoding)

            if 'crawl_time' in df.columns:
                df['crawl_time'] = pd.to_datetime(df['crawl_time'], errors='coerce')
                df = df.dropna(subset=['crawl_time'])
                df = df.sort_values('crawl_time')

            if limit:
                df = df.tail(limit)

            logger.info(f"从CSV加载了 {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"CSV读取失败: {e}")
            return pd.DataFrame()


def create_storage(config: Dict) -> BaseStorage:
    """当前规模下 CSV（含按天分区）完全够用；MySQL 分支因从未启用已移除"""
    return CSVStorage(config)
