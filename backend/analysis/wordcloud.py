import os
import logging
import pandas as pd
import numpy as np
from typing import List, Dict
from collections import Counter
from datetime import datetime

import jieba
import jieba.analyse

logger = logging.getLogger(__name__)


class WordCloudGenerator:
    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self.stopwords = set([
            '的', '了', '是', '在', '我', '有', '和', '就',
            '不', '人', '都', '一', '一个', '上', '也', '很',
            '到', '说', '要', '去', '你', '会', '着', '没有',
            '看', '好', '自己', '这', '微博', '热搜', '话题'
        ])

    def load_data(self, path: str) -> pd.DataFrame:
        logger.info(f"正在加载数据: {path}")
        self.df = pd.read_csv(path, encoding='utf-8-sig')

        if 'crawl_time' in self.df.columns:
            self.df['crawl_time'] = pd.to_datetime(self.df['crawl_time'])

        logger.info(f"加载了 {len(self.df)} 条记录")
        return self.df

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        if not text or pd.isna(text):
            return []

        keywords = jieba.analyse.extract_tags(str(text), topK=top_k)
        return [k for k in keywords if k not in self.stopwords and len(k) > 1]

    def get_all_titles(self) -> str:
        if self.df is None or self.df.empty:
            return ""

        titles = self.df['title'].dropna().tolist()
        return ' '.join(titles)

    def get_keyword_frequency(self, top_k: int = 100) -> Dict[str, int]:
        all_text = self.get_all_titles()

        words = jieba.lcut(all_text)
        words = [w for w in words if w not in self.stopwords and len(w) > 1]

        word_freq = Counter(words)

        return dict(word_freq.most_common(top_k))

    def get_keyword_by_label(self, top_k: int = 20) -> Dict[str, Dict[str, int]]:
        if self.df is None or 'label' not in self.df.columns:
            return {}

        result = {}

        for label in self.df['label'].unique():
            label_data = self.df[self.df['label'] == label]
            titles = label_data['title'].dropna().tolist()
            text = ' '.join(titles)

            words = jieba.lcut(text)
            words = [w for w in words if w not in self.stopwords and len(w) > 1]

            word_freq = Counter(words)
            result[label] = dict(word_freq.most_common(top_k))

        return result

    def get_keyword_by_hour(self) -> Dict[int, List[str]]:
        if self.df is None or 'crawl_time' not in self.df.columns:
            return {}

        if 'hour' not in self.df.columns:
            self.df['hour'] = self.df['crawl_time'].dt.hour

        result = {}

        for hour in range(24):
            hour_data = self.df[self.df['hour'] == hour]
            if len(hour_data) == 0:
                continue

            titles = hour_data['title'].dropna().tolist()
            text = ' '.join(titles)

            keywords = self.extract_keywords(text, top_k=10)
            if keywords:
                result[hour] = keywords

        return result

    def get_trending_keywords(self, window_hours: int = 6) -> Dict[str, float]:
        if self.df is None or 'crawl_time' not in self.df.columns:
            return {}

        now = self.df['crawl_time'].max()
        recent = self.df[self.df['crawl_time'] > now - pd.Timedelta(hours=window_hours)]
        earlier = self.df[self.df['crawl_time'] <= now - pd.Timedelta(hours=window_hours)]

        if recent.empty or earlier.empty:
            return {}

        recent_text = ' '.join(recent['title'].dropna().tolist())
        earlier_text = ' '.join(earlier['title'].dropna().tolist())

        recent_words = Counter([w for w in jieba.lcut(recent_text)
                               if w not in self.stopwords and len(w) > 1])
        earlier_words = Counter([w for w in jieba.lcut(earlier_text)
                                if w not in self.stopwords and len(w) > 1])

        trending = {}
        for word, count in recent_words.most_common(50):
            earlier_count = earlier_words.get(word, 0)
            if earlier_count == 0:
                trending[word] = count
            else:
                trending[word] = (count / len(recent)) / (earlier_count / len(earlier))

        return dict(sorted(trending.items(), key=lambda x: x[1], reverse=True)[:20])

    def generate_wordcloud_data(self, output_path: str = None) -> Dict:
        logger.info("正在生成词云数据...")

        word_freq = self.get_keyword_frequency(200)
        keyword_by_label = self.get_keyword_by_label(20)
        trending_keywords = self.get_trending_keywords()

        result = {
            'word_frequency': word_freq,
            'keywords_by_label': keyword_by_label,
            'trending_keywords': trending_keywords,
            'total_words': sum(word_freq.values()),
            'unique_words': len(word_freq)
        }

        if output_path:
            word_freq_df = pd.DataFrame([
                {'word': k, 'frequency': v}
                for k, v in word_freq.items()
            ])
            word_freq_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"词频数据已保存: {output_path}")

        logger.info(f"词云数据生成完成: {len(word_freq)} 个关键词")
        return result

    def get_entity_analysis(self) -> Dict[str, List[str]]:
        if self.df is None:
            return {}

        entities = {
            'celebrity': [],
            'location': [],
            'brand': [],
            'event': []
        }

        entity_cols = {
            'celebrity': 'entity_celebrity',
            'location': 'entity_location',
            'brand': 'entity_brand',
            'event': 'entity_event'
        }

        for entity_type, col in entity_cols.items():
            if col in self.df.columns:
                values = self.df[col].dropna().tolist()
                all_entities = []
                for v in values:
                    if isinstance(v, str) and v:
                        all_entities.extend([e.strip() for e in v.split(',') if e.strip()])
                entities[entity_type] = list(set(all_entities))[:50]

        return entities


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    generator = WordCloudGenerator()
    generator.load_data('data/processed_features_20260511.csv')
    results = generator.generate_wordcloud_data('data/word_frequency.csv')

    print("\nTop 20 关键词:")
    for word, freq in list(results['word_frequency'].items())[:20]:
        print(f"  {word}: {freq}")

    print("\n热门关键词:")
    for word, score in list(results['trending_keywords'].items())[:10]:
        print(f"  {word}: {score:.2f}")
