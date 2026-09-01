import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
from datetime import datetime

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, accuracy_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class HotSearchPredictor:
    """
    热搜排名预测（时间外推任务）

    任务定义：给定某话题在 t 时刻及之前的全部上榜历史，
    预测它在下一次爬取时刻 (t+1) 是否进入 TOP10 / TOP5。

    防泄露措施：
    1. 特征只使用目标时刻之前的历史数据；
    2. 训练/测试按时间先后切分（前 test_size 比例的快照训练，其余测试），
       不使用随机切分；
    3. 标准化只在训练集上 fit；
    4. 最终 prediction_results.csv 只保存测试集（样本外）预测。
    """

    TARGETS = ['will_top10', 'will_top5']

    def __init__(self, df: pd.DataFrame = None):
        self.df = df
        self.scaler = StandardScaler()
        self.model = None
        self.model_name = None
        self.feature_names: List[str] = []
        self.metrics: Dict = {}
        self.results_df: Optional[pd.DataFrame] = None

    def load_data(self, path: str) -> pd.DataFrame:
        logger.info(f"正在加载数据: {path}")
        self.df = pd.read_csv(path, encoding='utf-8-sig')

        if 'crawl_time' in self.df.columns:
            self.df['crawl_time'] = pd.to_datetime(self.df['crawl_time'])

        logger.info(f"加载了 {len(self.df)} 条记录")
        return self.df

    def prepare_prediction_data(self) -> pd.DataFrame:
        """构造观测级样本：每个样本 = 某话题的某次上榜，特征来自其历史，标签来自下一次上榜"""
        if self.df is None or self.df.empty:
            logger.warning("DataFrame为空")
            return pd.DataFrame()

        required = ['crawl_time', 'title', 'rank', 'hot_value']
        missing = [c for c in required if c not in self.df.columns]
        if missing:
            logger.error(f"缺少必要列: {missing}")
            return pd.DataFrame()

        logger.info("正在构造时间外推样本（特征仅使用历史数据）...")

        df = self.df.sort_values(['title', 'crawl_time']).reset_index(drop=True)

        samples = []
        for title, group in df.groupby('title'):
            group = group.sort_values('crawl_time')
            hot_values = group['hot_value'].values.astype(float)
            ranks = group['rank'].values.astype(float)
            times = group['crawl_time'].values

            is_new = group['is_new'].astype(float).values if 'is_new' in group.columns else np.zeros(len(group))
            is_hot = group['is_hot'].astype(float).values if 'is_hot' in group.columns else np.zeros(len(group))

            # 从第2次上榜开始才存在"历史"，i 为目标时刻下标
            for i in range(1, len(group)):
                hist_hot = hot_values[:i]
                hist_rank = ranks[:i]
                hist_new = is_new[:i]
                hist_hot_flag = is_hot[:i]

                samples.append({
                    'title': title,
                    # ---- 特征：仅目标时刻之前的历史 ----
                    'appear_count': float(i),
                    'avg_hot': hist_hot.mean(),
                    'max_hot': hist_hot.max(),
                    'min_hot': hist_hot.min(),
                    'std_hot': hist_hot.std() if i > 1 else 0.0,
                    'hot_change_rate': (hist_hot[-1] - hist_hot[0]) / (hist_hot[0] + 1),
                    'hot_volatility': np.std(np.diff(hist_hot)) / (hist_hot.mean() + 1) if i > 1 else 0.0,
                    'avg_rank': hist_rank.mean(),
                    'best_rank': hist_rank.min(),
                    'worst_rank': hist_rank.max(),
                    'last_rank': hist_rank[-1],
                    'last_hot': hist_hot[-1],
                    'is_new_ratio': hist_new.mean(),
                    'is_hot_ratio': hist_hot_flag.mean(),
                    'last_hour': pd.Timestamp(times[i - 1]).hour,
                    # ---- 目标时刻的已知信息（预测时墙钟时间已知）----
                    'target_time': pd.Timestamp(times[i]),
                    # ---- 标签：目标时刻的排名 ----
                    'will_top10': 1 if ranks[i] <= 10 else 0,
                    'will_top5': 1 if ranks[i] <= 5 else 0,
                    # ---- 参考信息（不作为特征）----
                    'next_rank': ranks[i],
                    'next_hot': hot_values[i],
                })

        result_df = pd.DataFrame(samples)
        logger.info(f"时间外推样本构造完成: {len(result_df)} 个样本 "
                    f"(TOP10正样本={int(result_df['will_top10'].sum()) if not result_df.empty else 0})")
        return result_df

    def temporal_split(self, samples: pd.DataFrame, test_size: float = 0.25):
        """按目标时间切分：前 test_size 比例的快照时刻用于训练，其余用于测试"""
        unique_times = np.sort(samples['target_time'].unique())
        n_train_times = max(1, int(len(unique_times) * (1 - test_size)))
        train_times = set(unique_times[:n_train_times])

        train_mask = samples['target_time'].isin(train_times)

        X_train = samples[train_mask]
        X_test = samples[~train_mask]

        # 兜底：如果测试集为空或只有一类标签，退化为随机分层切分并明确告警
        if X_test.empty or X_train['will_top10'].nunique() < 2 or X_test['will_top10'].nunique() < 2:
            logger.warning("时间切分后训练/测试集类别不完整，退化为随机分层切分（结果需谨慎解读）")
            idx = np.arange(len(samples))
            tr, te = train_test_split(idx, test_size=test_size, random_state=42,
                                      stratify=samples['will_top10'])
            return samples.iloc[tr], samples.iloc[te]

        return X_train, X_test

    def build_features(self, train_df: pd.DataFrame, test_df: pd.DataFrame, target: str):
        feature_cols = [
            'appear_count', 'avg_hot', 'max_hot', 'min_hot', 'std_hot',
            'hot_change_rate', 'hot_volatility',
            'avg_rank', 'best_rank', 'worst_rank', 'last_rank', 'last_hot',
            'is_new_ratio', 'is_hot_ratio', 'last_hour'
        ]
        self.feature_names = feature_cols

        X_train = train_df[feature_cols].fillna(0).values
        X_test = test_df[feature_cols].fillna(0).values
        y_train = train_df[target].values
        y_test = test_df[target].values

        # 标准化只在训练集上 fit，避免测试集信息泄露
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        return X_train_scaled, X_test_scaled, y_train, y_test

    def train_random_forest(self, X_train, X_test, y_train, y_test) -> Dict:
        logger.info("训练随机森林模型...")

        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(X_train, y_train)
        return self._evaluate('RandomForest', X_train, y_train, X_test, y_test)

    def train_xgboost(self, X_train, X_test, y_train, y_test) -> Dict:
        try:
            import xgboost as xgb
            logger.info("训练XGBoost模型...")

            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='logloss'
            )
            self.model.fit(X_train, y_train)
            return self._evaluate('XGBoost', X_train, y_train, X_test, y_test)
        except ImportError:
            logger.warning("XGBoost未安装，使用GradientBoosting替代")
            return self.train_gradient_boosting(X_train, X_test, y_train, y_test)

    def train_gradient_boosting(self, X_train, X_test, y_train, y_test) -> Dict:
        logger.info("训练GradientBoosting模型...")

        self.model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        return self._evaluate('GradientBoosting', X_train, y_train, X_test, y_test)

    def train_baseline(self, X_train, X_test, y_train, y_test) -> Dict:
        logger.info("训练基线模型 (逻辑回归)...")

        self.model = LogisticRegression(random_state=42, max_iter=1000)
        self.model.fit(X_train, y_train)
        return self._evaluate('Baseline', X_train, y_train, X_test, y_test)

    def _evaluate(self, name: str, X_train, y_train, X_test, y_test) -> Dict:
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'classification_report': classification_report(y_test, y_pred, zero_division=0),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        }

        # 测试集两个类别都存在时 AUC 才有意义
        if len(set(y_test)) > 1:
            metrics['roc_auc'] = roc_auc_score(y_test, y_pred_proba)
        else:
            metrics['roc_auc'] = float('nan')
            logger.warning(f"{name}: 测试集只有一个类别，AUC不可计算")

        cv_scores = cross_val_score(self.model, X_train, y_train, cv=5)
        metrics['cv_mean'] = cv_scores.mean()
        metrics['cv_std'] = cv_scores.std()

        self.metrics = metrics
        logger.info(f"{name} 训练完成: 准确率={metrics['accuracy']:.3f}, "
                    f"AUC={metrics['roc_auc']:.3f}, CV={metrics['cv_mean']:.3f}")
        return metrics

    def compare_models(self, X_train, X_test, y_train, y_test, target: str) -> pd.DataFrame:
        results = []

        for name, train_func in [
            ('RandomForest', lambda: self.train_random_forest(X_train, X_test, y_train, y_test)),
            ('XGBoost', lambda: self.train_xgboost(X_train, X_test, y_train, y_test)),
            ('Baseline', lambda: self.train_baseline(X_train, X_test, y_train, y_test))
        ]:
            try:
                metrics = train_func()
                results.append({
                    'model': name,
                    'target': target,
                    'accuracy': round(metrics['accuracy'], 4),
                    'roc_auc': round(metrics['roc_auc'], 4) if not np.isnan(metrics['roc_auc']) else '',
                    'cv_mean': round(metrics['cv_mean'], 4),
                    'cv_std': round(metrics['cv_std'], 4)
                })
            except Exception as e:
                logger.warning(f"{name} 训练失败: {e}")

        return pd.DataFrame(results)

    def get_feature_importance(self) -> Dict:
        if self.model is None or not hasattr(self.model, 'feature_importances_'):
            return {}

        return dict(sorted(
            zip(self.feature_names, self.model.feature_importances_),
            key=lambda x: x[1],
            reverse=True
        ))

    def run_pipeline(self, data_path: str = None, output_path: str = None,
                     test_size: float = 0.25) -> Dict:
        logger.info("=" * 60)
        logger.info("热搜预测模型训练（时间外推任务，仅输出样本外预测）")
        logger.info("=" * 60)

        if data_path:
            self.load_data(data_path)

        if self.df is None or self.df.empty:
            logger.error("没有数据")
            return {}

        samples = self.prepare_prediction_data()
        if samples.empty or samples['will_top10'].nunique() < 2:
            logger.error("样本不足或标签只有一类，无法训练")
            return {}

        train_df, test_df = self.temporal_split(samples, test_size=test_size)
        logger.info(f"时间切分: 训练集 {len(train_df)} 样本 (截至 {train_df['target_time'].max()}), "
                    f"测试集 {len(test_df)} 样本")

        comparison_frames = []
        best = {}  # target -> {'model_name', 'probabilities', 'predictions'}

        for target in self.TARGETS:
            if train_df[target].nunique() < 2 or test_df[target].nunique() < 2:
                logger.warning(f"目标 {target} 在训练或测试集中类别不足，跳过")
                continue

            X_train, X_test, y_train, y_test = self.build_features(train_df, test_df, target)

            results_df = self.compare_models(X_train, X_test, y_train, y_test, target)
            comparison_frames.append(results_df)
            logger.info(f"\n{target} 模型对比:\n{results_df.to_string()}")

            # 按 AUC 选最优模型，用其在测试集上的概率作为最终输出
            valid = results_df[results_df['roc_auc'] != ''].copy()
            if valid.empty:
                continue
            valid['roc_auc_num'] = pd.to_numeric(valid['roc_auc'])
            best_row = valid.sort_values('roc_auc_num', ascending=False).iloc[0]
            best_name = best_row['model']

            # 重新训练最优模型得到测试集概率
            train_func = {
                'RandomForest': self.train_random_forest,
                'XGBoost': self.train_xgboost,
                'GradientBoosting': self.train_gradient_boosting,
                'Baseline': self.train_baseline,
            }[best_name]
            train_func(X_train, X_test, y_train, y_test)

            proba = self.model.predict_proba(X_test)[:, 1]
            pred = (proba >= 0.5).astype(int)
            best[target] = {'model_name': best_name, 'probability': proba, 'prediction': pred}

            logger.info(f"{target} 最优模型: {best_name} (AUC={best_row['roc_auc_num']:.3f})")

        results_df = pd.concat(comparison_frames, ignore_index=True) if comparison_frames else pd.DataFrame()

        if output_path and not results_df.empty:
            results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"模型对比结果已保存: {output_path}")

        # 只保存测试集（样本外）预测结果
        if 'will_top10' in best:
            out = test_df[['title', 'target_time', 'last_rank', 'last_hot',
                           'next_rank', 'next_hot', 'will_top10', 'will_top5']].copy()
            out = out.rename(columns={
                'last_rank': 'current_rank',
                'last_hot': 'current_hot',
            })
            out['prediction_top10'] = best['will_top10']['prediction']
            out['probability_top10'] = np.round(best['will_top10']['probability'], 4)
            out['predicted_by_top10'] = best['will_top10']['model_name']
            if 'will_top5' in best:
                out['prediction_top5'] = best['will_top5']['prediction']
                out['probability_top5'] = np.round(best['will_top5']['probability'], 4)
                out['predicted_by_top5'] = best['will_top5']['model_name']

            pred_output_path = 'data/prediction_results.csv'
            out.sort_values('target_time').to_csv(pred_output_path, index=False, encoding='utf-8-sig')
            self.results_df = out
            logger.info(f"样本外预测结果已保存: {pred_output_path} ({len(out)} 条测试集记录)")

        logger.info("=" * 60)
        logger.info("预测模型训练完成")
        logger.info("=" * 60)

        return {
            'model_comparison': results_df,
            'metrics': self.metrics,
            'feature_importance': self.get_feature_importance(),
            'predictions': self.results_df
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    predictor = HotSearchPredictor()
    results = predictor.run_pipeline(
        data_path='data/processed_features.csv',
        output_path='data/model_comparison.csv'
    )

    print("\n特征重要性:")
    for feat, imp in list(results['feature_importance'].items())[:5]:
        print(f"  {feat}: {imp:.4f}")
