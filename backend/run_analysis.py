import os
import sys
import argparse
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 固定的中间数据文件名（避免每次分析按日期堆积新文件）
PROCESSED_DATA_PATH = 'data/processed_features.csv'


def run_preprocess():
    logger.info("=" * 60)
    logger.info("步骤1: 数据预处理")
    logger.info("=" * 60)

    from preprocess.cleaner import DataCleaner
    from preprocess.feature import FeatureEngineer

    raw_data_path = 'data/hotsearch_records.csv'
    cleaned_data_path = 'data/cleaned_features.csv'

    if not os.path.exists(raw_data_path):
        logger.warning(f"原始数据不存在: {raw_data_path}")
        return None

    cleaner = DataCleaner()
    df = cleaner.load_csv(raw_data_path)
    df = cleaner.clean_pipeline(
        remove_duplicates=True,
        fill_nulls=True,
        detect_anomalies=True
    )
    df.to_csv(cleaned_data_path, index=False, encoding='utf-8-sig')
    logger.info(f"清洗后数据已保存: {cleaned_data_path}")

    engineer = FeatureEngineer(df)
    df = engineer.feature_pipeline()
    df.to_csv(PROCESSED_DATA_PATH, index=False, encoding='utf-8-sig')
    logger.info(f"特征工程数据已保存: {PROCESSED_DATA_PATH}")

    return PROCESSED_DATA_PATH


def run_clustering(data_path: str = None):
    logger.info("=" * 60)
    logger.info("步骤2: 话题聚类分析")
    logger.info("=" * 60)

    from analysis.clustering import TopicClustering

    if data_path is None:
        data_path = PROCESSED_DATA_PATH

    if not os.path.exists(data_path):
        logger.error(f"数据文件不存在: {data_path}")
        return None

    clustering = TopicClustering()
    results = clustering.run_pipeline(
        data_path=data_path,
        output_path='data/clustering_results.csv',
        method='kmeans',
        n_clusters=None  # None 时用轮廓系数自动寻优，不再硬编码 K=4
    )

    return results


def run_prediction(data_path: str = None):
    logger.info("=" * 60)
    logger.info("步骤3: 热度预测模型")
    logger.info("=" * 60)

    from analysis.prediction import HotSearchPredictor

    if data_path is None:
        data_path = PROCESSED_DATA_PATH

    if not os.path.exists(data_path):
        logger.error(f"数据文件不存在: {data_path}")
        return None

    predictor = HotSearchPredictor()
    results = predictor.run_pipeline(
        data_path=data_path,
        output_path='data/model_comparison.csv'
    )

    return results


def run_sentiment(data_path: str = None):
    logger.info("=" * 60)
    logger.info("步骤4: 情感分析")
    logger.info("=" * 60)

    from analysis.sentiment import SentimentAnalyzer

    if data_path is None:
        data_path = PROCESSED_DATA_PATH

    if not os.path.exists(data_path):
        logger.error(f"数据文件不存在: {data_path}")
        return None

    analyzer = SentimentAnalyzer()
    results = analyzer.run_pipeline(
        data_path=data_path,
        output_path='data/sentiment_results.csv'
    )

    return results


def run_wordcloud(data_path: str = None):
    logger.info("=" * 60)
    logger.info("步骤5: 词云分析")
    logger.info("=" * 60)

    from analysis.wordcloud import WordCloudGenerator

    if data_path is None:
        data_path = PROCESSED_DATA_PATH

    if not os.path.exists(data_path):
        logger.error(f"数据文件不存在: {data_path}")
        return None

    generator = WordCloudGenerator()
    generator.load_data(data_path)
    results = generator.generate_wordcloud_data('data/word_frequency.csv')

    return results


def run_anomaly(data_path: str = None):
    logger.info("=" * 60)
    logger.info("步骤6: 异常检测")
    logger.info("=" * 60)

    from analysis.anomaly import AnomalyDetector

    if data_path is None:
        data_path = PROCESSED_DATA_PATH

    if not os.path.exists(data_path):
        logger.error(f"数据文件不存在: {data_path}")
        return None

    detector = AnomalyDetector()
    results = detector.run_pipeline(
        data_path=data_path,
        output_path='data/anomaly_results.csv'
    )

    return results


def main():
    parser = argparse.ArgumentParser(description='微博热搜数据分析')
    parser.add_argument('--method', type=str, default='all',
                       choices=['all', 'preprocess', 'clustering', 'prediction', 'sentiment',
                               'wordcloud', 'anomaly'],
                       help='选择分析方法')
    parser.add_argument('--data', type=str, default=None,
                       help='输入数据路径')
    parser.add_argument('--skip-preprocess', action='store_true',
                       help='跳过预处理步骤')

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("微博热搜数据分析系统")
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    processed_data_path = args.data

    if args.method in ['all', 'preprocess'] and not args.skip_preprocess:
        processed_data_path = run_preprocess()

    if args.method == 'all':
        run_clustering(processed_data_path)
        run_prediction(processed_data_path)
        run_sentiment(processed_data_path)
        run_wordcloud(processed_data_path)
        run_anomaly(processed_data_path)
    elif args.method == 'clustering':
        run_clustering(processed_data_path)
    elif args.method == 'prediction':
        run_prediction(processed_data_path)
    elif args.method == 'sentiment':
        run_sentiment(processed_data_path)
    elif args.method == 'wordcloud':
        run_wordcloud(processed_data_path)
    elif args.method == 'anomaly':
        run_anomaly(processed_data_path)

    logger.info("=" * 60)
    logger.info("分析完成!")
    logger.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
