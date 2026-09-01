import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    基于话题标题文本的情感打分。

    局限性说明（诚实边界）：
    - 分析对象是热搜"标题"，不是网友评论/博文，因此反映的是话题措辞的
      情感色彩，不能等同于"公众情绪"；
    - 同一标题在所有快照中得分恒定，"情感演化/反转"只有在接入评论文本
      等异构数据后才有意义；
    - SnowNLP 的训练语料是电商评论，对新闻类标题的打分仅供参考。
    """

    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self.sentiment_scores = {}
        self.topic_sentiments = {}

    def load_data(self, path: str) -> pd.DataFrame:
        logger.info(f"正在加载数据: {path}")
        self.df = pd.read_csv(path, encoding='utf-8-sig')

        if 'crawl_time' in self.df.columns:
            self.df['crawl_time'] = pd.to_datetime(self.df['crawl_time'])

        logger.info(f"加载了 {len(self.df)} 条记录")
        return self.df

    def analyze_text(self, text: str) -> float:
        if not text or pd.isna(text):
            return 0.0

        try:
            from snownlp import SnowNLP
            s = SnowNLP(str(text))
            return s.sentiments
        except ImportError:
            logger.warning("snownlp未安装，使用简单情感词典")
            return self._simple_sentiment(text)

    def _simple_sentiment(self, text: str) -> float:
        positive_words = ['好', '棒', '赞', '喜', '爱', '美', '棒', '牛', '帅', '甜',
                         'happy', 'good', 'great', 'best', 'love', 'nice']
        negative_words = ['坏', '差', '烂', '垃圾', '讨厌', '恨', '丑', '冷', '悲',
                         'bad', 'worst', 'hate', 'terrible', 'awful', 'sad']

        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return 0.5

        return pos_count / total

    def classify_sentiment(self, score: float) -> str:
        if score >= 0.6:
            return 'positive'
        elif score <= 0.4:
            return 'negative'
        else:
            return 'neutral'

    def analyze_single_text(self, text: str) -> Dict:
        score = self.analyze_text(text)
        sentiment = self.classify_sentiment(score)

        return {
            'text': text,
            'sentiment_score': score,
            'sentiment_label': sentiment
        }

    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        results = []

        for text in texts:
            results.append(self.analyze_single_text(text))

        return results

    def analyze_topic_sentiment_evolution(self, title: str) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            logger.warning("DataFrame为空")
            return pd.DataFrame()

        topic_data = self.df[self.df['title'] == title].copy()

        if len(topic_data) == 0:
            logger.warning(f"未找到话题: {title}")
            return pd.DataFrame()

        topic_data = topic_data.sort_values('crawl_time')

        topic_data['sentiment_score'] = topic_data['title'].apply(self.analyze_text)
        topic_data['sentiment_label'] = topic_data['sentiment_score'].apply(self.classify_sentiment)

        evolution = topic_data[['crawl_time', 'title', 'rank', 'hot_value',
                              'sentiment_score', 'sentiment_label']].copy()

        logger.info(f"话题 '{title}' 情感演化分析完成: {len(evolution)} 个时间点")

        return evolution

    def analyze_all_topics(self) -> pd.DataFrame:
        if self.df is None or self.df.empty:
            logger.warning("DataFrame为空")
            return self.df

        logger.info("正在分析所有话题的情感（按标题文本，每话题一次）...")

        # 同一话题的标题文本在所有快照中相同，情感得分恒定，
        # 因此每个独立标题只分析一次，避免重复计算
        unique_titles = self.df['title'].dropna().unique()
        title_scores = {t: self.analyze_text(t) for t in unique_titles}

        self.df['sentiment_score'] = self.df['title'].map(title_scores)
        self.df['sentiment_label'] = self.df['sentiment_score'].apply(self.classify_sentiment)

        sentiment_summary = self.df.groupby('title').agg({
            'sentiment_score': ['mean', 'std', 'min', 'max'],
            'sentiment_label': lambda x: x.value_counts().index[0],
            'crawl_time': ['min', 'max', 'count']
        }).reset_index()

        sentiment_summary.columns = [
            'title', 'avg_sentiment', 'std_sentiment', 'min_sentiment', 'max_sentiment',
            'dominant_sentiment', 'first_seen', 'last_seen', 'appear_count'
        ]

        # 波动幅度（max-min）。当前数据源只分析标题，同一话题得分恒定，波动恒为0；
        # 未来接入评论文本后该字段才会出现真实波动
        sentiment_summary['sentiment_change'] = (
            sentiment_summary['max_sentiment'] - sentiment_summary['min_sentiment']
        )

        sentiment_summary['emotion_type'] = sentiment_summary.apply(
            lambda x: self._classify_emotion(x['avg_sentiment'], x['sentiment_change']),
            axis=1
        )

        logger.info(f"情感分析完成: {len(sentiment_summary)} 个话题")

        self.topic_sentiments = sentiment_summary

        return sentiment_summary

    def _classify_emotion(self, avg_score: float, change: float) -> str:
        """
        按平均极性和波动幅度分类。
        注意: change 是波动幅度(max-min)，恒 >= 0，不能用来表达"下降"方向。
        """
        if change > 0.3:
            return '情感波动型'
        elif avg_score > 0.6:
            return '持续正面型'
        elif avg_score < 0.4:
            return '持续负面型'
        else:
            return '情感稳定型'

    def get_emotion_distribution(self) -> Dict:
        if not isinstance(self.topic_sentiments, pd.DataFrame) or self.topic_sentiments.empty:
            self.analyze_all_topics()

        if isinstance(self.topic_sentiments, pd.DataFrame) and not self.topic_sentiments.empty:
            return self.topic_sentiments['emotion_type'].value_counts().to_dict()

        return {}

    def get_sentiment_stats(self) -> Dict:
        if self.df is None or 'sentiment_score' not in self.df.columns:
            return {}

        return {
            'avg_sentiment': self.df['sentiment_score'].mean(),
            'median_sentiment': self.df['sentiment_score'].median(),
            'positive_count': (self.df['sentiment_score'] >= 0.6).sum(),
            'negative_count': (self.df['sentiment_score'] <= 0.4).sum(),
            'neutral_count': ((self.df['sentiment_score'] > 0.4) & (self.df['sentiment_score'] < 0.6)).sum(),
            'positive_ratio': (self.df['sentiment_score'] >= 0.6).mean(),
            'negative_ratio': (self.df['sentiment_score'] <= 0.4).mean()
        }

    def find_sentiment_reversal(self, threshold: float = 0.3) -> List[Dict]:
        if not isinstance(self.topic_sentiments, pd.DataFrame) or self.topic_sentiments.empty:
            self.analyze_all_topics()

        if isinstance(self.topic_sentiments, pd.DataFrame) and not self.topic_sentiments.empty:
            reversals = self.topic_sentiments[
                abs(self.topic_sentiments['sentiment_change']) > threshold
            ].copy()

            reversals = reversals.sort_values('sentiment_change', key=abs, ascending=False)

            results = []
            for _, row in reversals.head(10).iterrows():
                results.append({
                    'title': row['title'],
                    'min_sentiment': row['min_sentiment'],
                    'max_sentiment': row['max_sentiment'],
                    'change': row['sentiment_change'],
                    'appear_count': row['appear_count']
                })

            return results

        return []

    def run_pipeline(self, data_path: str = None, output_path: str = None) -> Dict:
        logger.info("=" * 60)
        logger.info("微博热搜情感分析")
        logger.info("=" * 60)

        if data_path:
            self.load_data(data_path)

        if self.df is None or self.df.empty:
            logger.error("没有数据")
            return {}

        topic_sentiments = self.analyze_all_topics()

        sentiment_stats = self.get_sentiment_stats()
        emotion_dist = self.get_emotion_distribution()
        reversals = self.find_sentiment_reversal()

        logger.info(f"\n📊 情感统计:")
        logger.info(f"   平均情感得分: {sentiment_stats.get('avg_sentiment', 0):.3f}")
        logger.info(f"   正面话题: {sentiment_stats.get('positive_count', 0)}")
        logger.info(f"   负面话题: {sentiment_stats.get('negative_count', 0)}")
        logger.info(f"   中性话题: {sentiment_stats.get('neutral_count', 0)}")

        logger.info(f"\n📈 情感类型分布:")
        for emotion, count in emotion_dist.items():
            logger.info(f"   {emotion}: {count}")

        if reversals:
            logger.info(f"\n🔄 情感反转话题 (Top 5):")
            for r in reversals[:5]:
                logger.info(f"   {r['title']}: {r['min_sentiment']:.2f} -> {r['max_sentiment']:.2f}")

        if output_path:
            topic_sentiments.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"情感分析结果已保存: {output_path}")

        logger.info("=" * 60)
        logger.info("情感分析完成")
        logger.info("=" * 60)

        return {
            'topic_sentiments': topic_sentiments,
            'sentiment_stats': sentiment_stats,
            'emotion_distribution': emotion_dist,
            'sentiment_reversals': reversals
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    analyzer = SentimentAnalyzer()
    results = analyzer.run_pipeline(
        data_path='data/processed_features_20260511.csv',
        output_path='data/sentiment_results.csv'
    )

    print("\n情感反转话题:")
    for r in results['sentiment_reversals'][:5]:
        print(f"  {r['title']}: {r['min_sentiment']:.2f} -> {r['max_sentiment']:.2f}")
