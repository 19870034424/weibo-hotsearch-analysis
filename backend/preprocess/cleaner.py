import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, List

logger = logging.getLogger(__name__)


class DataCleaner:
    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self.cleaning_stats = {
            'duplicate_removed': 0,
            'null_filled': 0,
            'outlier_detected': 0,
            'anomaly_detected': 0
        }
        # 热度突变事件明细（之前被直接丢弃）
        self.hot_change_anomalies = []

    def load_csv(self, path: str) -> pd.DataFrame:
        logger.info(f"正在加载CSV: {path}")
        self.df = pd.read_csv(path, encoding='utf-8-sig')
        logger.info(f"加载了 {len(self.df)} 条记录")
        return self.df

    def remove_duplicates(self, subset: List[str] = None) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            logger.warning("DataFrame为空，跳过去重")
            return self.df

        if subset is None:
            subset = ['title', 'crawl_time']

        original_count = len(self.df)
        self.df = self.df.drop_duplicates(subset=subset, keep='first')
        self.cleaning_stats['duplicate_removed'] = original_count - len(self.df)

        if self.cleaning_stats['duplicate_removed'] > 0:
            logger.info(f"去重完成: 移除 {self.cleaning_stats['duplicate_removed']} 条重复记录")

        return self.df

    def fill_nulls(self) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return self.df

        null_counts = self.df.isnull().sum()
        if null_counts.sum() > 0:
            logger.info(f"发现空值:\n{null_counts[null_counts > 0]}")

        self.df['title'] = self.df['title'].fillna('')
        self.df['label'] = self.df['label'].fillna('')
        self.df['category'] = self.df['category'].fillna('')
        self.df['link'] = self.df['link'].fillna('')
        self.df['hot_value'] = self.df['hot_value'].fillna(0)

        self.cleaning_stats['null_filled'] = null_counts.sum()
        logger.info("空值填充完成")

        return self.df

    def detect_hot_value_anomalies(self, groupby_col: str = 'title', window_size: int = 5) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return self.df

        if 'crawl_time' not in self.df.columns:
            logger.warning("缺少 crawl_time 列，无法进行热度异常检测")
            return self.df

        self.df['crawl_time'] = pd.to_datetime(self.df['crawl_time'])
        self.df = self.df.sort_values(['title', 'crawl_time'])

        anomaly_records = []

        for title, group in self.df.groupby(groupby_col):
            if len(group) < 2:
                continue

            hot_values = group['hot_value'].values
            for i in range(1, len(hot_values)):
                if hot_values[i-1] > 0:
                    change_rate = abs(hot_values[i] - hot_values[i-1]) / hot_values[i-1]
                    if change_rate > 0.5:
                        anomaly_records.append({
                            'title': title,
                            'crawl_time': group['crawl_time'].iloc[i],
                            'previous_hot': hot_values[i-1],
                            'current_hot': hot_values[i],
                            'change_rate': change_rate
                        })

        if anomaly_records:
            logger.info(f"检测到 {len(anomaly_records)} 次热度突变事件")
            self.cleaning_stats['anomaly_detected'] = len(anomaly_records)
            self.hot_change_anomalies = anomaly_records

        return self.df

    def get_cleaning_report(self) -> dict:
        return {
            'total_records': len(self.df) if self.df is not None else 0,
            'duplicate_removed': self.cleaning_stats['duplicate_removed'],
            'null_filled': self.cleaning_stats['null_filled'],
            'outlier_detected': self.cleaning_stats['outlier_detected'],
            'anomaly_detected': self.cleaning_stats['anomaly_detected']
        }

    def clean_pipeline(self, remove_duplicates: bool = True,
                      fill_nulls: bool = True,
                      detect_anomalies: bool = True) -> pd.DataFrame:
        logger.info("=" * 50)
        logger.info("开始数据清洗流程")
        logger.info("=" * 50)

        if remove_duplicates:
            self.remove_duplicates()

        if fill_nulls:
            self.fill_nulls()

        if detect_anomalies:
            self.detect_hot_value_anomalies()

        logger.info("=" * 50)
        logger.info("数据清洗完成")
        logger.info(f"清洗报告: {self.get_cleaning_report()}")
        logger.info("=" * 50)

        return self.df
