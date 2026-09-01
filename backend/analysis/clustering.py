import logging
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict
from datetime import datetime

from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


class TopicClustering:
    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self.scaler = StandardScaler()
        self.kmeans_model = None
        self.dbscan_model = None
        self.cluster_labels = None
        self.feature_names = []

    def load_data(self, path: str) -> pd.DataFrame:
        logger.info(f"正在加载数据: {path}")
        self.df = pd.read_csv(path, encoding='utf-8-sig')

        if 'crawl_time' in self.df.columns:
            self.df['crawl_time'] = pd.to_datetime(self.df['crawl_time'])

        logger.info(f"加载了 {len(self.df)} 条记录")
        return self.df

    def prepare_lifecycle_features(self) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            logger.warning("DataFrame为空")
            return self.df

        if 'crawl_time' not in self.df.columns or 'title' not in self.df.columns:
            logger.error("缺少必要列: crawl_time 或 title")
            return self.df

        logger.info("正在构造生命周期特征...")

        self.df = self.df.sort_values(['title', 'crawl_time'])

        lifecycle_df = self.df.groupby('title').agg({
            'hot_value': ['max', 'mean', 'std', 'first', 'last'],
            'rank': ['min', 'mean'],
            'crawl_time': ['min', 'max', 'count'],
            'label': lambda x: ','.join(set(x.dropna().astype(str))),
            'is_new': 'sum',
            'is_hot': 'sum',
            'hour': ['mean', 'std']
        }).reset_index()

        lifecycle_df.columns = [
            'title', 'peak_hot', 'avg_hot', 'std_hot', 'first_hot', 'last_hot',
            'best_rank', 'avg_rank', 'first_seen', 'last_seen', 'appear_count',
            'labels', 'new_count', 'hot_count', 'avg_hour', 'std_hour'
        ]

        lifecycle_df['duration_hours'] = (
            lifecycle_df['last_seen'] - lifecycle_df['first_seen']
        ).dt.total_seconds() / 3600

        lifecycle_df['hot_trend'] = (lifecycle_df['last_hot'] - lifecycle_df['first_hot']) / (lifecycle_df['first_hot'] + 1)
        lifecycle_df['rank_change'] = lifecycle_df['best_rank'] - lifecycle_df['avg_rank']

        lifecycle_df['first_seen'] = pd.to_datetime(lifecycle_df['first_seen'])
        lifecycle_df['hour_sin'] = np.sin(2 * np.pi * lifecycle_df['first_seen'].dt.hour / 24)
        lifecycle_df['hour_cos'] = np.cos(2 * np.pi * lifecycle_df['first_seen'].dt.hour / 24)
        lifecycle_df['dow_sin'] = np.sin(2 * np.pi * lifecycle_df['first_seen'].dt.dayofweek / 7)
        lifecycle_df['dow_cos'] = np.cos(2 * np.pi * lifecycle_df['first_seen'].dt.dayofweek / 7)

        lifecycle_df['is_new_topic'] = lifecycle_df['new_count'] > 0
        lifecycle_df['is_hot_topic'] = lifecycle_df['hot_count'] > 0

        lifecycle_df = lifecycle_df.fillna(0)

        self.df = lifecycle_df
        logger.info(f"生命周期特征构造完成: {len(self.df)} 个独立话题")

        return self.df

    def extract_clustering_features(self) -> np.ndarray:
        feature_cols = [
            'peak_hot', 'avg_hot', 'std_hot', 'hot_trend',
            'best_rank', 'avg_rank', 'rank_change',
            'duration_hours', 'appear_count',
            'new_count', 'hot_count',
            'is_new_topic', 'is_hot_topic',
            'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos'
        ]

        available_cols = [c for c in feature_cols if c in self.df.columns]

        if not available_cols:
            logger.error("没有可用的聚类特征")
            return None

        self.feature_names = available_cols

        X = self.df[available_cols].values

        X = np.nan_to_num(X, nan=0, posinf=0, neginf=0)

        X_scaled = self.scaler.fit_transform(X)

        logger.info(f"提取了 {len(available_cols)} 个聚类特征")
        return X_scaled

    def find_optimal_k(self, X: np.ndarray, k_range: range = None) -> int:
        if k_range is None:
            k_range = range(2, min(10, len(X)))

        silhouettes = []
        inertias = []

        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)

            if len(set(labels)) > 1:
                sil_score = silhouette_score(X, labels)
                silhouettes.append((k, sil_score))
                inertias.append((k, kmeans.inertia_))
                logger.debug(f"K={k}: silhouette={sil_score:.3f}, inertia={kmeans.inertia_:.2f}")

        if silhouettes:
            best_k = max(silhouettes, key=lambda x: x[1])[0]
            logger.info(f"最优K值: {best_k} (silhouette score: {max(silhouettes, key=lambda x: x[1])[1]:.3f})")
            return best_k

        return 4

    def cluster_kmeans(self, n_clusters: int = None) -> Tuple[np.ndarray, Dict]:
        X = self.extract_clustering_features()

        if X is None:
            return None, {}

        if n_clusters is None:
            n_clusters = self.find_optimal_k(X)

        logger.info(f"执行K-Means聚类 (K={n_clusters})...")

        self.kmeans_model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.cluster_labels = self.kmeans_model.fit_predict(X)

        self.df['cluster_kmeans'] = self.cluster_labels

        cluster_stats = self._compute_cluster_stats('cluster_kmeans')

        logger.info(f"K-Means聚类完成: {n_clusters} 个簇")
        return self.cluster_labels, cluster_stats

    def cluster_dbscan(self, eps: float = 0.5, min_samples: int = 5) -> Tuple[np.ndarray, Dict]:
        X = self.extract_clustering_features()

        if X is None:
            return None, {}

        logger.info(f"执行DBSCAN聚类 (eps={eps}, min_samples={min_samples})...")

        self.dbscan_model = DBSCAN(eps=eps, min_samples=min_samples)
        self.cluster_labels = self.dbscan_model.fit_predict(X)

        self.df['cluster_dbscan'] = self.cluster_labels

        n_clusters = len(set(self.cluster_labels)) - (1 if -1 in self.cluster_labels else 0)
        n_noise = list(self.cluster_labels).count(-1)

        logger.info(f"DBSCAN聚类完成: {n_clusters} 个簇, {n_noise} 个噪声点")

        cluster_stats = self._compute_cluster_stats('cluster_dbscan')

        return self.cluster_labels, cluster_stats

    def _compute_cluster_stats(self, cluster_col: str) -> Dict:
        stats = {}

        for cluster_id in sorted(self.df[cluster_col].unique()):
            cluster_data = self.df[self.df[cluster_col] == cluster_id]

            cluster_name = f"cluster_{cluster_id}" if cluster_id != -1 else "noise"

            stats[cluster_name] = {
                'count': len(cluster_data),
                'avg_peak_hot': cluster_data['peak_hot'].mean(),
                'avg_duration': cluster_data['duration_hours'].mean(),
                'avg_appear_count': cluster_data['appear_count'].mean(),
                'avg_rank': cluster_data['avg_rank'].mean(),
                'hot_trend_avg': cluster_data['hot_trend'].mean(),
                'top_topics': cluster_data.nlargest(3, 'peak_hot')['title'].tolist()
            }

        return stats

    def classify_lifecycle_type(self, cluster_id: int) -> str:
        if cluster_id == -1:
            return 'noise'

        if cluster_id not in self.df['cluster_kmeans'].values:
            return 'unknown'

        cluster_data = self.df[self.df['cluster_kmeans'] == cluster_id]

        avg_duration = cluster_data['duration_hours'].mean()
        avg_appear = cluster_data['appear_count'].mean()
        avg_trend = cluster_data['hot_trend'].mean()
        avg_rank = cluster_data['avg_rank'].mean()

        if avg_duration < 2 and avg_appear <= 3:
            return '爆发型 (短时突爆)'
        elif avg_trend > 0.3 and avg_rank < 10:
            return '明星型 (快速登顶)'
        elif avg_duration > 24 and avg_appear > 10:
            return '长尾型 (持续霸榜)'
        elif avg_duration > 6 and avg_appear > 5:
            return '慢热型 (逐渐攀升)'
        elif avg_trend < -0.2:
            return '衰退型 (快速冷却)'
        else:
            return '普通型 (正常波动)'

    def get_cluster_summary(self) -> pd.DataFrame:
        if self.df is None or 'cluster_kmeans' not in self.df.columns:
            logger.warning("请先执行聚类")
            return pd.DataFrame()

        summary = []

        for cluster_id in sorted(self.df['cluster_kmeans'].unique()):
            cluster_data = self.df[self.df['cluster_kmeans'] == cluster_id]

            lifecycle_type = self.classify_lifecycle_type(cluster_id)

            summary.append({
                'cluster_id': cluster_id,
                'lifecycle_type': lifecycle_type,
                'topic_count': len(cluster_data),
                'avg_peak_hot': f"{cluster_data['peak_hot'].mean():,.0f}",
                'avg_duration_hours': f"{cluster_data['duration_hours'].mean():.1f}",
                'avg_appear_count': f"{cluster_data['appear_count'].mean():.1f}",
                'avg_rank': f"{cluster_data['avg_rank'].mean():.1f}",
                'top_topic_1': cluster_data.nlargest(1, 'peak_hot')['title'].values[0] if len(cluster_data) > 0 else '',
                'top_topic_2': cluster_data.nlargest(2, 'peak_hot')['title'].values[1] if len(cluster_data) > 1 else '',
                'top_topic_3': cluster_data.nlargest(3, 'peak_hot')['title'].values[2] if len(cluster_data) > 2 else ''
            })

        return pd.DataFrame(summary)

    def get_cluster_examples(self, cluster_id: int, n: int = 5) -> List[Dict]:
        if self.df is None or 'cluster_kmeans' not in self.df.columns:
            return []

        cluster_data = self.df[self.df['cluster_kmeans'] == cluster_id].copy()
        cluster_data = cluster_data.sort_values('peak_hot', ascending=False)

        examples = []
        for _, row in cluster_data.head(n).iterrows():
            examples.append({
                'title': row['title'],
                'peak_hot': row['peak_hot'],
                'duration_hours': row['duration_hours'],
                'appear_count': row['appear_count'],
                'best_rank': row['best_rank'],
                'hot_trend': row['hot_trend']
            })

        return examples

    def save_results(self, output_path: str):
        if self.df is not None and not self.df.empty:
            self.df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"聚类结果已保存: {output_path}")

    def run_pipeline(self, data_path: str = None, output_path: str = None,
                    method: str = 'kmeans', n_clusters: int = 4) -> Dict:
        logger.info("=" * 60)
        logger.info("话题生命周期聚类分析")
        logger.info("=" * 60)

        if data_path:
            self.load_data(data_path)

        if self.df is None or self.df.empty:
            logger.error("没有数据")
            return {}

        self.prepare_lifecycle_features()

        if method == 'kmeans':
            self.cluster_kmeans(n_clusters=n_clusters)
        elif method == 'dbscan':
            self.cluster_dbscan()
        else:
            logger.error(f"未知聚类方法: {method}")
            return {}

        summary = self.get_cluster_summary()
        logger.info(f"\n聚类摘要:\n{summary.to_string()}")

        if output_path:
            self.save_results(output_path)

        logger.info("=" * 60)
        logger.info("聚类分析完成")
        logger.info("=" * 60)

        return {
            'summary': summary,
            'cluster_stats': self._compute_cluster_stats('cluster_kmeans')
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    clustering = TopicClustering()
    results = clustering.run_pipeline(
        data_path='data/processed_features_20260511.csv',
        output_path='data/clustering_results.csv',
        method='kmeans',
        n_clusters=4
    )

    print("\n聚类摘要:")
    print(results['summary'])
