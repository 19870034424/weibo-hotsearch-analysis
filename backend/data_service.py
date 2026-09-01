"""
数据服务层（唯一数据出口）

从 data/ 下的真实分析结果 CSV 构建结构化数据，供两个消费方使用：
- api_server.py:  通过 /api/data 实时提供给 Vue 前端
- generate_frontend_data.py:  导出为静态 realData.js（可选的离线快照）

所有字段口径只在这里定义一次，保证前后端数据永远一致。
"""
import os
import json
import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

FRONTEND_DATA_PATH = os.path.join(
    BASE_DIR, '..', 'frontend', 'src', 'data', 'realData.js'
)


def _py(value):
    """把 numpy/pandas 类型转成可 JSON 序列化的原生类型"""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    if value is pd.NaT or (isinstance(value, pd.Timestamp) and pd.isna(value)):
        return None
    return value


def _jsonable(obj):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return _py(obj)


def _load(path, **kwargs) -> pd.DataFrame:
    if not os.path.exists(path):
        logger.warning(f"数据文件不存在，对应前端数据将为空: {path}")
        return pd.DataFrame()
    return pd.read_csv(path, encoding='utf-8-sig', **kwargs)


def classify_sentiment(score: float) -> str:
    if score >= 0.6:
        return 'positive'
    if score <= 0.4:
        return 'negative'
    return 'neutral'


def classify_cluster_lifecycle(avg_duration: float, avg_appear: float,
                               avg_trend: float, avg_rank: float) -> str:
    """与 analysis/clustering.py 的 classify_lifecycle_type 保持同一套阈值"""
    if avg_duration < 2 and avg_appear <= 3:
        return '爆发型'
    if avg_trend > 0.3 and avg_rank < 10:
        return '快速登顶型'
    if avg_duration > 24 and avg_appear > 10:
        return '持续霸榜型'
    if avg_duration > 6 and avg_appear > 5:
        return '慢热攀升型'
    if avg_trend < -0.2:
        return '快速冷却型'
    return '正常波动型'


def build_hotsearch(records: pd.DataFrame) -> tuple:
    """最新一次快照的榜单 + 真实的小时分布/标签分布/每小时上榜TOP话题"""
    if records.empty:
        return [], [], [], None, []

    records = records.copy()
    records['crawl_time'] = pd.to_datetime(records['crawl_time'])
    records = records.sort_values('crawl_time')

    last_time = records['crawl_time'].max()
    latest = records[records['crawl_time'] == last_time].sort_values('rank')

    hotsearch_records = [
        {
            'rank': int(row['rank']),
            'title': str(row['title']),
            'hot_value': int(row['hot_value']),
            'label': '' if pd.isna(row['label']) else str(row['label']),
            'category': '',  # 爬虫的 note 字段不是分类，真实数据无类别，置空
            'crawl_time': last_time.strftime('%Y-%m-%d %H:%M'),
        }
        for _, row in latest.iterrows()
    ]

    # 全部记录的小时分布（0-23 全量，缺的小时为 0）
    hour_counts = records['crawl_time'].dt.hour.value_counts()
    hourly_distribution = [
        {'hour': f'{h:02d}:00', 'count': int(hour_counts.get(h, 0))}
        for h in range(24)
    ]

    # 每小时上榜话题的热度TOP5（前端点击小时柱展开详情用）
    hour_top = {}
    for hour, group in records.groupby(records['crawl_time'].dt.hour):
        top = group.nlargest(5, 'hot_value')[['title', 'hot_value']]
        hour_top[int(hour)] = [
            {'title': str(r['title']), 'hot_value': int(r['hot_value'])}
            for _, r in top.iterrows()
        ]
    hourly_topics = [
        {'hour': f'{h:02d}:00', 'topics': hour_top.get(h, [])}
        for h in range(24)
    ]

    # 标签分布（空标签显示为"无"）
    label_counts = records['label'].fillna('').value_counts()
    total = int(label_counts.sum())
    label_distribution = [
        {
            'label': lbl if lbl else '无',
            'count': int(cnt),
            'percentage': round(cnt / total * 100, 1),
        }
        for lbl, cnt in label_counts.items()
    ]

    return hotsearch_records, hourly_distribution, label_distribution, last_time, hourly_topics


def build_clusters(clustering: pd.DataFrame) -> list:
    """聚类结果 + 每个簇的生命周期命名（与聚类模块同一套阈值）"""
    if clustering.empty or 'cluster_kmeans' not in clustering.columns:
        return []

    out = []
    for cluster_id, group in clustering.groupby('cluster_kmeans'):
        name = f"聚类{int(cluster_id)}·{classify_cluster_lifecycle(
            group['duration_hours'].mean(),
            group['appear_count'].mean(),
            group['hot_trend'].mean() if 'hot_trend' in group.columns else 0,
            group['avg_rank'].mean() if 'avg_rank' in group.columns else 50,
        )}"
        for _, row in group.iterrows():
            out.append({
                'title': str(row['title']),
                'cluster': int(cluster_id),
                'cluster_name': name,
                'peak_hot': _py(row['peak_hot']),
                'avg_hot': _py(row['avg_hot']),
            })
    return out


def build_predictions(pred: pd.DataFrame, comparison: pd.DataFrame) -> tuple:
    """样本外预测结果 + 真实模型指标（替代前端原先硬编码的统计卡）"""
    if pred.empty:
        return [], {}

    pred = pred.sort_values('target_time')
    results = [
        {
            'title': str(row['title']),
            'target_time': str(row['target_time'])[:16],
            'current_rank': int(row['current_rank']),
            'current_hot': _py(row['current_hot']),
            'next_rank': _py(row['next_rank']),
            'will_top10': int(row['will_top10']),
            'will_top5': int(row['will_top5']),
            'prediction_top10': int(row.get('prediction_top10', 0)),
            'probability': _py(row.get('probability_top10')),
            'prediction_top5': int(row.get('prediction_top5', 0)) if 'prediction_top5' in pred.columns else None,
        }
        for _, row in pred.iterrows()
    ]

    metrics = {
        'samples': len(results),
        'top10_accuracy': round(float((pred['prediction_top10'] == pred['will_top10']).mean()), 3),
        'top5_accuracy': round(float((pred['prediction_top5'] == pred['will_top5']).mean()), 3)
        if 'prediction_top5' in pred.columns else None,
        'auc': None,
        'model': str(pred['predicted_by_top10'].iloc[0]) if 'predicted_by_top10' in pred.columns else '',
    }

    comp = comparison[comparison['target'] == 'will_top10'] if not comparison.empty else pd.DataFrame()
    if not comp.empty:
        comp = comp[comp['model'] == metrics['model']]
        if not comp.empty:
            metrics['auc'] = _py(comp['roc_auc'].iloc[0])

    return results, metrics


def build_anomalies(anomaly: pd.DataFrame) -> tuple:
    """异常检测结果，按类别补齐展示所需字段"""
    if anomaly.empty:
        return [], {}

    out = []
    for _, row in anomaly.iterrows():
        category = row.get('anomaly_category', '')
        a_type = row.get('anomaly_type', '')

        hot_value = row.get('hot_value', None)
        crawl_time = row.get('crawl_time', None)

        if category == 'viral_topics':
            # 爆款话题是话题级聚合记录，没有单条 crawl_time
            hot_value = row.get('max_hot', hot_value)
            crawl_time = None
            a_type = 'viral_topic'
        elif category == 'disappeared_topics':
            a_type = 'disappeared'
        elif category == 'new_emerging':
            a_type = 'new_emerging'

        out.append({
            'title': str(row['title']),
            'hot_value': _py(hot_value),
            'anomaly_type': str(a_type) if a_type else str(category),
            'anomaly_category': str(category),
            'crawl_time': str(crawl_time)[:16] if pd.notna(crawl_time) else None,
        })

    # 同一话题的同一类异常在每个快照都会触发一次，展示时按(话题,类型)去重，
    # 保留热度峰值最高的一次；完整明细仍在 data/anomaly_results.csv
    dedup = {}
    for item in out:
        key = (item['title'], item['anomaly_type'])
        if key not in dedup or (item['hot_value'] or 0) > (dedup[key]['hot_value'] or 0):
            dedup[key] = item
    out = sorted(dedup.values(), key=lambda x: x['hot_value'] or 0, reverse=True)

    involved = anomaly['title'].nunique() if 'title' in anomaly.columns else 0
    by_type = {}
    for item in out:
        by_type[item['anomaly_type']] = by_type.get(item['anomaly_type'], 0) + 1

    stats = {
        'total': int(len(anomaly)),  # 原始异常事件总数
        'display_count': len(out),
        'involved_topics': int(involved),
        'by_type': by_type,  # 去重后各类数量
    }
    return out, stats


def build_hot_trend_series(records: pd.DataFrame, top_n: int = 3) -> dict:
    """热度最高话题的真实热度轨迹（替代前端原先手绘的预测趋势线）"""
    if records.empty:
        return {'labels': [], 'series': []}

    records = records.copy()
    records['crawl_time'] = pd.to_datetime(records['crawl_time'])

    top_titles = (
        records.groupby('title')['hot_value'].max()
        .sort_values(ascending=False).head(top_n).index.tolist()
    )

    all_times = sorted(records['crawl_time'].unique())
    labels = [pd.Timestamp(t).strftime('%H:%M') for t in all_times]

    series = []
    for title in top_titles:
        topic = records[records['title'] == title]
        by_time = dict(zip(topic['crawl_time'], topic['hot_value']))
        series.append({
            'title': title[:12],
            'data': [_py(by_time.get(t)) for t in all_times],
        })

    return {'labels': labels, 'series': series}


def build_sentiment_trend(records: pd.DataFrame, sentiment: pd.DataFrame) -> list:
    """每小时上榜话题的真实情感极性占比（按标题得分归到该话题出现的每个小时）"""
    if records.empty or sentiment.empty:
        return []

    score_by_title = dict(zip(sentiment['title'], sentiment['avg_sentiment']))
    df = records[records['title'].isin(score_by_title)].copy()
    if df.empty:
        return []

    df['hour'] = pd.to_datetime(df['crawl_time']).dt.hour
    df['score'] = df['title'].map(score_by_title)

    out = []
    for hour, group in df.groupby('hour'):
        n = len(group)
        pos = (group['score'] >= 0.6).sum() / n * 100
        neg = (group['score'] <= 0.4).sum() / n * 100
        neu = 100 - pos - neg
        out.append({
            'hour': f'{int(hour):02d}:00',
            'positive': round(float(pos), 1),
            'negative': round(float(neg), 1),
            'neutral': round(float(neu), 1),
        })
    return out


def build_chat_context(records: pd.DataFrame) -> str:
    """构建智能问答的系统上下文：最新榜单 TOP10 + 全局统计"""
    if records.empty:
        return "当前没有热搜数据。"

    df = records.copy()
    df['crawl_time'] = pd.to_datetime(df['crawl_time'])
    latest_time = df['crawl_time'].max()
    latest_data = df[df['crawl_time'] == latest_time].sort_values('rank').head(10)

    context = f"数据时间: {latest_time:%Y-%m-%d %H:%M}\n\n当前热搜TOP10:\n"
    for _, row in latest_data.iterrows():
        context += f"{int(row['rank']) + 1}. {row['title']} - 热度: {int(row['hot_value']):,}\n"

    context += f"\n统计信息:\n"
    context += f"- 总话题数: {df['title'].nunique()}\n"
    context += f"- 数据跨度(小时): {(df['crawl_time'].max() - df['crawl_time'].min()).total_seconds() / 3600:.1f}\n"
    context += f"- 最高热度: {int(df['hot_value'].max()):,}\n"
    return context


def build_payload() -> dict:
    """构建完整的前端数据负载（API 与静态导出的共同来源）"""
    records = _load(os.path.join(DATA_DIR, 'hotsearch_records.csv'))
    sentiment = _load(os.path.join(DATA_DIR, 'sentiment_results.csv'))
    clustering = _load(os.path.join(DATA_DIR, 'clustering_results.csv'))
    prediction = _load(os.path.join(DATA_DIR, 'prediction_results.csv'))
    comparison = _load(os.path.join(DATA_DIR, 'model_comparison.csv'))
    anomaly = _load(os.path.join(DATA_DIR, 'anomaly_results.csv'))
    word_freq = _load(os.path.join(DATA_DIR, 'word_frequency.csv'))

    hotsearch_records, hourly_distribution, label_distribution, last_crawl, hourly_topics = build_hotsearch(records)

    # 情感：真实分析结果，emotion_type 已由后端重新定义
    sentiment_results = []
    sentiment_trend = []
    if not sentiment.empty:
        sentiment = sentiment.sort_values('appear_count', ascending=False)
        sentiment_results = [
            {
                'title': str(row['title']),
                'avg_sentiment': round(float(row['avg_sentiment']), 3),
                'std_sentiment': round(float(row['std_sentiment']), 3) if pd.notna(row['std_sentiment']) else 0.0,
                'dominant_sentiment': classify_sentiment(row['avg_sentiment']),
                'appear_count': int(row['appear_count']),
                'emotion_type': str(row['emotion_type']),
            }
            for _, row in sentiment.iterrows()
        ]
        sentiment_trend = build_sentiment_trend(records, sentiment)

    clustering_results = build_clusters(clustering)

    # 聚类类别分布（替代真实数据中不存在的"话题分类"）
    stats = {}
    for item in clustering_results:
        stats.setdefault(item['cluster_name'], 0)
        stats[item['cluster_name']] += 1
    cluster_distribution = [{'cluster_name': k, 'count': v} for k, v in stats.items()]

    prediction_results, prediction_metrics = build_predictions(prediction, comparison)
    anomaly_results, anomaly_stats = build_anomalies(anomaly)
    hot_trend_series = build_hot_trend_series(records)

    word_frequency = [
        {'word': str(row['word']), 'frequency': int(row['frequency'])}
        for _, row in word_freq.iterrows()
    ]

    now = datetime.now()
    age_hours = None
    if last_crawl is not None:
        age_hours = round((now - last_crawl).total_seconds() / 3600, 1)

    return {
        'dataMeta': {
            'generated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
            'last_crawl': last_crawl.strftime('%Y-%m-%d %H:%M') if last_crawl is not None else None,
            'total_records': int(len(records)),
            'unique_topics': int(records['title'].nunique()) if not records.empty else 0,
        },
        'dataStatus': {
            'last_crawl': last_crawl.strftime('%Y-%m-%d %H:%M') if last_crawl is not None else None,
            'age_hours': age_hours,
            'fresh': bool(age_hours is not None and age_hours < 72),
        },
        'hotsearchRecords': hotsearch_records,
        'hourlyDistribution': hourly_distribution,
        'hourlyTopics': hourly_topics,
        'labelDistribution': label_distribution,
        'clusterDistribution': cluster_distribution,
        'sentimentResults': sentiment_results,
        'sentimentTrend': sentiment_trend,
        'clusteringResults': clustering_results,
        'predictionResults': prediction_results,
        'predictionMetrics': prediction_metrics,
        'anomalyResults': anomaly_results,
        'anomalyStats': anomaly_stats,
        'hotTrendSeries': hot_trend_series,
        'wordFrequency': word_frequency,
        'chatContext': build_chat_context(records),
    }


def generate(output_path: str = None) -> str:
    """导出为静态 realData.js（可选的离线快照，正常使用走 API 即可）"""
    payload = build_payload()
    output_path = output_path or os.path.normpath(FRONTEND_DATA_PATH)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('// 本文件由 generate_frontend_data.py 自动生成 —— 数据与后端分析结果一致\n')
        f.write('// 正常使用请通过 API (/api/data) 获取实时数据，此文件仅作离线快照\n\n')
        for key, value in payload.items():
            f.write(f'export const {key} = {json.dumps(_jsonable(value), ensure_ascii=False, indent=2)}\n\n')

    logger.info(f"前端静态数据快照已生成: {output_path}")
    return output_path
