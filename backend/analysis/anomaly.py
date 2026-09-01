import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self.scaler = StandardScaler()
        self.isolation_forest = None
        self.anomalies = []

    def load_data(self, path: str) -> pd.DataFrame:
        logger.info(f"正在加载数据: {path}")
        self.df = pd.read_csv(path, encoding='utf-8-sig')

        if 'crawl_time' in self.df.columns:
            self.df['crawl_time'] = pd.to_datetime(self.df['crawl_time'])

        logger.info(f"加载了 {len(self.df)} 条记录")
        return self.df

    def detect_hot_value_anomalies(self, threshold_std: float = 3.0) -> pd.DataFrame:
        if self.df is None or 'hot_value' not in self.df.columns:
            logger.warning("缺少hot_value列")
            return pd.DataFrame()

        logger.info("正在检测热度异常值...")

        mean = self.df['hot_value'].mean()
        std = self.df['hot_value'].std()

        upper_bound = mean + threshold_std * std
        lower_bound = mean - threshold_std * std

        anomalies = self.df[
            (self.df['hot_value'] > upper_bound) |
            (self.df['hot_value'] < lower_bound)
        ].copy()

        anomalies['anomaly_type'] = anomalies['hot_value'].apply(
            lambda x: 'extremely_high' if x > upper_bound else 'extremely_low'
        )

        logger.info(f"检测到 {len(anomalies)} 个热度异常值")
        return anomalies

    def detect_rank_anomalies(self, threshold: int = 5) -> pd.DataFrame:
        if self.df is None or 'title' not in self.df.columns or 'rank' not in self.df.columns:
            logger.warning("缺少必要列")
            return pd.DataFrame()

        logger.info("正在检测排名突变...")

        self.df = self.df.sort_values(['title', 'crawl_time'])

        self.df['rank_change'] = self.df.groupby('title')['rank'].diff()

        sudden_rise = self.df[self.df['rank_change'] < -threshold].copy()
        sudden_rise['anomaly_type'] = 'sudden_rise'

        sudden_drop = self.df[self.df['rank_change'] > threshold].copy()
        sudden_drop['anomaly_type'] = 'sudden_drop'

        anomalies = pd.concat([sudden_rise, sudden_drop])
        logger.info(f"检测到 {len(anomalies)} 个排名突变")

        return anomalies

    def detect_isolation_forest(self, contamination: float = 0.1) -> pd.DataFrame:
        if self.df is None:
            logger.warning("DataFrame为空")
            return pd.DataFrame()

        feature_cols = ['hot_value', 'rank']
        available_cols = [c for c in feature_cols if c in self.df.columns]

        if not available_cols:
            logger.warning("没有可用特征")
            return pd.DataFrame()

        logger.info("正在使用Isolation Forest检测异常...")

        X = self.df[available_cols].fillna(0).values
        X_scaled = self.scaler.fit_transform(X)

        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )

        predictions = self.isolation_forest.fit_predict(X_scaled)

        self.df['is_anomaly'] = predictions == -1

        anomalies = self.df[self.df['is_anomaly']].copy()
        anomalies['anomaly_type'] = 'isolation_forest'

        logger.info(f"Isolation Forest检测到 {len(anomalies)} 个异常")
        return anomalies

    def detect_viral_topics(self, min_hot_ratio: float = 2.0,
                           min_appear_count: int = 3) -> pd.DataFrame:
        if self.df is None or 'title' not in self.df.columns:
            logger.warning("缺少必要列")
            return pd.DataFrame()

        logger.info("正在检测爆款话题...")

        topic_stats = self.df.groupby('title').agg({
            'hot_value': ['max', 'mean', 'std'],
            'rank': 'min',
            'crawl_time': 'count'
        }).reset_index()

        topic_stats.columns = ['title', 'max_hot', 'avg_hot', 'std_hot', 'best_rank', 'appear_count']

        overall_avg = self.df['hot_value'].mean()

        viral = topic_stats[
            (topic_stats['max_hot'] > overall_avg * min_hot_ratio) &
            (topic_stats['appear_count'] >= min_appear_count)
        ].copy()

        viral['viral_score'] = (
            viral['max_hot'] / overall_avg +
            (50 - viral['best_rank']) / 50 +
            viral['appear_count'] / 10
        )

        viral = viral.sort_values('viral_score', ascending=False)
        viral['anomaly_type'] = 'viral_topic'

        logger.info(f"检测到 {len(viral)} 个爆款话题")
        return viral

    def detect_disappeared_topics(self, hours: int = 2) -> pd.DataFrame:
        if self.df is None or 'crawl_time' not in self.df.columns:
            logger.warning("缺少必要列")
            return pd.DataFrame()

        logger.info("正在检测消失话题...")

        latest_time = self.df['crawl_time'].max()
        cutoff_time = latest_time - timedelta(hours=hours)

        recent_topics = set(
            self.df[self.df['crawl_time'] > cutoff_time]['title'].unique()
        )

        earlier_topics = set(
            self.df[self.df['crawl_time'] <= cutoff_time]['title'].unique()
        )

        disappeared = earlier_topics - recent_topics

        if not disappeared:
            logger.info("没有检测到消失话题")
            return pd.DataFrame()

        disappeared_data = self.df[
            self.df['title'].isin(disappeared)
        ].groupby('title').agg({
            'hot_value': 'max',
            'rank': 'min',
            'crawl_time': 'max'
        }).reset_index()

        disappeared_data['hours_since_seen'] = (
            latest_time - disappeared_data['crawl_time']
        ).dt.total_seconds() / 3600

        disappeared_data['anomaly_type'] = 'disappeared'
        logger.info(f"检测到 {len(disappeared_data)} 个消失话题")

        return disappeared_data

    def detect_new_emerging(self, window_hours: int = 1) -> pd.DataFrame:
        if self.df is None or 'crawl_time' not in self.df.columns:
            logger.warning("缺少必要列")
            return pd.DataFrame()

        logger.info("正在检测新晋话题...")

        latest_time = self.df['crawl_time'].max()
        window_start = latest_time - timedelta(hours=window_hours)

        recent_data = self.df[self.df['crawl_time'] > window_start]
        earlier_data = self.df[self.df['crawl_time'] <= window_start]

        recent_topics = set(recent_data['title'].unique())
        earlier_topics = set(earlier_data['title'].unique())

        new_topics = recent_topics - earlier_topics

        if not new_topics:
            logger.info("没有检测到新晋话题")
            return pd.DataFrame()

        new_data = recent_data[recent_data['title'].isin(new_topics)].copy()
        new_data['anomaly_type'] = 'new_emerging'

        logger.info(f"检测到 {len(new_data)} 个新晋话题")
        return new_data

    def get_anomaly_summary(self) -> Dict:
        results = {
            'hot_value_anomalies': self.detect_hot_value_anomalies(),
            'rank_anomalies': self.detect_rank_anomalies(),
            'viral_topics': self.detect_viral_topics(),
            'disappeared_topics': self.detect_disappeared_topics(),
            'new_emerging': self.detect_new_emerging()
        }

        summary = {
            'total_anomalies': sum(len(v) for v in results.values() if isinstance(v, pd.DataFrame)),
            'by_type': {k: len(v) for k, v in results.items() if isinstance(v, pd.DataFrame)}
        }

        return results, summary

    def run_pipeline(self, data_path: str = None, output_path: str = None) -> Dict:
        logger.info("=" * 60)
        logger.info("热搜异常检测")
        logger.info("=" * 60)

        if data_path:
            self.load_data(data_path)

        if self.df is None or self.df.empty:
            logger.error("没有数据")
            return {}

        results, summary = self.get_anomaly_summary()

        logger.info(f"\n📊 异常检测摘要:")
        for anomaly_type, count in summary['by_type'].items():
            logger.info(f"   {anomaly_type}: {count}")

        all_anomalies = []
        for name, df in results.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df['anomaly_category'] = name
                all_anomalies.append(df)

        if all_anomalies:
            combined = pd.concat(all_anomalies, ignore_index=True)

            if output_path:
                combined.to_csv(output_path, index=False, encoding='utf-8-sig')
                logger.info(f"异常检测结果已保存: {output_path}")

        logger.info("=" * 60)
        logger.info("异常检测完成")
        logger.info("=" * 60)

        return {
            'results': results,
            'summary': summary
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    detector = AnomalyDetector()
    results = detector.run_pipeline(
        data_path='data/processed_features_20260511.csv',
        output_path='data/anomaly_results.csv'
    )

    print("\n爆款话题:")
    viral = results['results']['viral_topics']
    if not viral.empty:
        print(viral[['title', 'max_hot', 'best_rank', 'viral_score']].head(10))
