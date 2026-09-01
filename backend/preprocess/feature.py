import re
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)


class FeatureEngineer:
    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self.entity_patterns = {
            'celebrity': re.compile(r'[\u4e00-\u9fa5]{2,4}(?:[明星演员歌手]|先生|女士|总裁|CEO)'),
            'location': re.compile(r'(?:北京|上海|深圳|广州|杭州|成都|武汉|西安|南京|重庆|Chinese|American|Japanese|Korean)'),
            'brand': re.compile(r'(?:华为|小米|苹果|OPPO|VIVO|腾讯|阿里|字节|百度|京东|美团|滴滴|抖音|微信|微博)'),
            'event': re.compile(r'(?:宣布|发布|回应|致歉|热搜|封禁|上市|融资|离婚|结婚|出轨|去世)'),
        }

    def load_csv(self, path: str) -> pd.DataFrame:
        logger.info(f"正在加载数据: {path}")
        self.df = pd.read_csv(path, encoding='utf-8-sig')
        if 'crawl_time' in self.df.columns:
            self.df['crawl_time'] = pd.to_datetime(self.df['crawl_time'])
        logger.info(f"加载了 {len(self.df)} 条记录")
        return self.df

    def extract_keywords(self, text_column: str = 'title') -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return self.df

        if text_column not in self.df.columns:
            logger.warning(f"列 {text_column} 不存在")
            return self.df

        try:
            import jieba
            import jieba.analyse

            jieba.setLogLevel(jieba.logging.INFO)

            def extract_top_keywords(text: str, topK: int = 5) -> str:
                if not text:
                    return ''
                try:
                    keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=False)
                    return ','.join(keywords)
                except:
                    return ''

            self.df['keywords'] = self.df[text_column].apply(extract_top_keywords)
            logger.info("关键词提取完成 (TF-IDF)")

        except ImportError:
            logger.warning("jieba未安装，使用简单分词")
            self.df['keywords'] = self.df[text_column].apply(self._simple_tokenize)

        return self.df

    def _simple_tokenize(self, text: str) -> str:
        if not text:
            return ''
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]+', text)
        return ','.join(chinese_chars[:5]) if chinese_chars else ''

    def extract_entities(self, text_column: str = 'title') -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return self.df

        def find_entities(text: str) -> Dict[str, List[str]]:
            entities = {
                'celebrity': [],
                'location': [],
                'brand': [],
                'event': []
            }

            if not text:
                return entities

            for entity_type, pattern in self.entity_patterns.items():
                matches = pattern.findall(text)
                entities[entity_type] = list(set(matches))

            return entities

        entity_results = self.df[text_column].apply(find_entities)

        self.df['entity_celebrity'] = entity_results.apply(lambda x: ','.join(x['celebrity']))
        self.df['entity_location'] = entity_results.apply(lambda x: ','.join(x['location']))
        self.df['entity_brand'] = entity_results.apply(lambda x: ','.join(x['brand']))
        self.df['entity_event'] = entity_results.apply(lambda x: ','.join(x['event']))

        logger.info("实体识别完成")
        return self.df

    def calculate_hot_change_rate(self) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return self.df

        if 'crawl_time' not in self.df.columns or 'title' not in self.df.columns:
            logger.warning("缺少必要列: crawl_time 或 title")
            return self.df

        self.df = self.df.sort_values(['title', 'crawl_time'])

        def calc_change_rate(group):
            if len(group) < 2:
                return pd.Series({
                    'hot_change_rate': 0.0,
                    'hot_rise_speed': 0.0,
                    'hot_fall_speed': 0.0
                })

            hot_values = group['hot_value'].values
            times = group['crawl_time'].values

            if hot_values[0] > 0:
                change_rate = (hot_values[-1] - hot_values[0]) / hot_values[0]
            else:
                change_rate = 0.0

            duration_hours = (pd.Timestamp(times[-1]) - pd.Timestamp(times[0])).total_seconds() / 3600
            if duration_hours > 0:
                rise_speed = (hot_values.max() - hot_values[0]) / duration_hours
                fall_speed = (hot_values.max() - hot_values[-1]) / duration_hours
            else:
                rise_speed = 0.0
                fall_speed = 0.0

            return pd.Series({
                'hot_change_rate': change_rate,
                'hot_rise_speed': rise_speed,
                'hot_fall_speed': fall_speed
            })

        change_features = self.df.groupby('title', group_keys=False).apply(calc_change_rate)
        self.df = self.df.join(change_features, rsuffix='_calc')

        logger.info("热度变化率计算完成")
        return self.df

    def build_lifecycle_features(self) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return self.df

        if 'crawl_time' not in self.df.columns or 'title' not in self.df.columns:
            logger.warning("缺少必要列")
            return self.df

        self.df = self.df.sort_values(['title', 'crawl_time'])

        def calc_lifecycle(group):
            if len(group) < 1:
                return pd.Series({
                    'first_seen': None,
                    'last_seen': None,
                    'duration_hours': 0.0,
                    'appear_count': 0,
                    'peak_hot': 0,
                    'peak_time': None,
                    'avg_hot': 0.0
                })

            first_time = group['crawl_time'].min()
            last_time = group['crawl_time'].max()
            duration = (last_time - first_time).total_seconds() / 3600

            peak_idx = group['hot_value'].idxmax()
            peak_hot = group.loc[peak_idx, 'hot_value']
            peak_time = group.loc[peak_idx, 'crawl_time']

            return pd.Series({
                'first_seen': first_time,
                'last_seen': last_time,
                'duration_hours': duration,
                'appear_count': len(group),
                'peak_hot': peak_hot,
                'peak_time': peak_time,
                'avg_hot': group['hot_value'].mean()
            })

        lifecycle_features = self.df.groupby('title', group_keys=False).apply(calc_lifecycle)
        self.df = self.df.join(lifecycle_features, rsuffix='_life')

        self.df['lifecycle_type'] = self.df.apply(self._classify_lifecycle, axis=1)

        logger.info("生命周期特征构建完成")
        return self.df

    def _classify_lifecycle(self, row) -> str:
        if pd.isna(row.get('duration_hours', 0)) or row.get('appear_count', 0) < 2:
            return 'unknown'

        duration = row['duration_hours']
        appear_count = row['appear_count']
        change_rate = row.get('hot_change_rate', 0)   # (末次-首次)/首次
        rise_speed = row.get('hot_rise_speed', 0)     # (峰值-首次)/持续小时数

        if duration < 2 and appear_count <= 2:
            return 'short_burst'
        elif rise_speed > 0 and row['peak_time'] == row['first_seen']:
            # 首次上榜即峰值、随后回落 —— 典型爆发形态
            # (原条件 change_rate>0.5 且 peak==first_seen 自相矛盾，永不触发)
            return 'explosive'
        elif duration > 24 and appear_count > 10:
            return 'long_tail'
        elif duration > 6 and appear_count > 5:
            return 'slow_rise'
        elif change_rate < -0.5:
            return 'cooling'
        else:
            return 'normal'

    def add_label_features(self) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return self.df

        if 'label' not in self.df.columns:
            logger.warning("缺少 label 列")
            return self.df

        self.df['is_new'] = self.df['label'].str.contains('新', na=False)
        self.df['is_hot'] = self.df['label'].str.contains('热', na=False)
        self.df['is_boiling'] = self.df['label'].str.contains('沸', na=False)
        self.df['is_recommend'] = self.df['label'].str.contains('荐', na=False)

        logger.info("标签特征提取完成")
        return self.df

    def add_time_features(self) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            return self.df

        if 'crawl_time' not in self.df.columns:
            logger.warning("缺少 crawl_time 列")
            return self.df

        self.df['hour'] = self.df['crawl_time'].dt.hour
        self.df['day_of_week'] = self.df['crawl_time'].dt.dayofweek
        self.df['is_weekend'] = self.df['day_of_week'].isin([5, 6])
        self.df['time_period'] = self.df['hour'].apply(self._get_time_period)

        logger.info("时间特征提取完成")
        return self.df

    def _get_time_period(self, hour: int) -> str:
        if 6 <= hour < 9:
            return 'morning'
        elif 9 <= hour < 12:
            return 'forenoon'
        elif 12 <= hour < 14:
            return 'noon'
        elif 14 <= hour < 18:
            return 'afternoon'
        elif 18 <= hour < 22:
            return 'evening'
        else:
            return 'night'

    def get_feature_summary(self) -> Dict:
        if self.df is None or self.df.empty:
            return {}

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        feature_cols = [c for c in self.df.columns if c not in
                       ['rank', 'title', 'label', 'category', 'link', 'img_url', 'crawl_time']]

        return {
            'total_records': len(self.df),
            'total_features': len(feature_cols),
            'numeric_features': len(numeric_cols),
            'feature_list': feature_cols,
            'lifecycle_distribution': self.df['lifecycle_type'].value_counts().to_dict() if 'lifecycle_type' in self.df.columns else {}
        }

    def feature_pipeline(self) -> pd.DataFrame:
        logger.info("=" * 50)
        logger.info("开始特征工程流程")
        logger.info("=" * 50)

        self.extract_keywords()
        self.extract_entities()
        self.add_label_features()
        self.add_time_features()
        # 必须在生命周期分类之前计算热度变化特征，
        # 否则 _classify_lifecycle 依赖的 hot_change_rate/hot_rise_speed 不存在
        self.calculate_hot_change_rate()
        self.build_lifecycle_features()

        logger.info("=" * 50)
        logger.info("特征工程完成")
        logger.info(f"特征摘要: {self.get_feature_summary()}")
        logger.info("=" * 50)

        return self.df

    def save_features(self, output_path: str):
        if self.df is not None and not self.df.empty:
            self.df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"特征数据已保存: {output_path}")
