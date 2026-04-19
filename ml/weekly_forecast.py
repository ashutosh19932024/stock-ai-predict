from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor


@dataclass(frozen=True, slots=True)
class HorizonForecast:
    outlook: str
    probability_up: float
    predicted_return_pct: float
    confidence: float
    holdout_accuracy: float
    holdout_precision: float
    target_date: str
    prediction_history: pd.DataFrame
    target_return_column: str
    target_up_column: str


@dataclass(frozen=True, slots=True)
class WeeklyForecastResult:
    tomorrow: HorizonForecast
    next_week: HorizonForecast
    final_recommendation: str
    recommendation_reason: str
    train_rows: int
    test_rows: int
    last_close: float
    feature_importance: pd.DataFrame
    feature_frame: pd.DataFrame


class WeeklyForecastModel:
    feature_columns = [
        "return_1d",
        "return_5d",
        "return_20d",
        "volatility_5d",
        "volatility_20d",
        "sma_10_ratio",
        "sma_20_ratio",
        "sma_50_ratio",
        "sma_200_ratio",
        "volume_ratio_5_20",
        "range_pct",
        "rsi_14",
        "drawdown_60d",
    ]

    def run(self, history: pd.DataFrame) -> WeeklyForecastResult:
        feature_frame = self._build_feature_frame(history)
        if len(feature_frame) < 260:
            raise ValueError("Not enough historical rows to train a one-week model. Need about 260 feature rows.")

        split_idx = max(int(len(feature_frame) * 0.8), len(feature_frame) - 252)
        split_idx = min(split_idx, len(feature_frame) - 30)
        if split_idx <= 100:
            raise ValueError("Not enough data after train/test split for model evaluation.")

        train_df = feature_frame.iloc[:split_idx].copy()
        test_df = feature_frame.iloc[split_idx:].copy()

        clf = RandomForestClassifier(
            n_estimators=300,
            max_depth=7,
            min_samples_leaf=6,
            random_state=42,
        )
        reg = RandomForestRegressor(
            n_estimators=250,
            max_depth=7,
            min_samples_leaf=6,
            random_state=42,
        )

        x_train = train_df[self.feature_columns]
        x_test = test_df[self.feature_columns]

        tomorrow_forecast = self._run_horizon_model(
            train_df=train_df,
            test_df=test_df,
            x_train=x_train,
            x_test=x_test,
            latest_features=feature_frame[self.feature_columns].iloc[[-1]],
            target_return_column="target_return_1d",
            target_up_column="target_up_1d",
            horizon_days=1,
            latest_index=feature_frame.index[-1],
        )
        next_week_forecast = self._run_horizon_model(
            train_df=train_df,
            test_df=test_df,
            x_train=x_train,
            x_test=x_test,
            latest_features=feature_frame[self.feature_columns].iloc[[-1]],
            target_return_column="target_return_5d",
            target_up_column="target_up_5d",
            horizon_days=5,
            latest_index=feature_frame.index[-1],
        )

        final_recommendation, recommendation_reason = self._build_final_recommendation(
            tomorrow=tomorrow_forecast,
            next_week=next_week_forecast,
        )

        importance = pd.DataFrame(
            {
                "feature": self.feature_columns,
                "importance": (
                    np.array(self._fit_importance_model(x_train, train_df["target_up_5d"]).feature_importances_)
                    + np.array(self._fit_importance_model(x_train, train_df["target_up_1d"]).feature_importances_)
                ) / 2,
            }
        ).sort_values("importance", ascending=False)

        return WeeklyForecastResult(
            tomorrow=tomorrow_forecast,
            next_week=next_week_forecast,
            final_recommendation=final_recommendation,
            recommendation_reason=recommendation_reason,
            train_rows=len(train_df),
            test_rows=len(test_df),
            last_close=float(history["close"].iloc[-1]),
            feature_importance=importance,
            feature_frame=feature_frame,
        )

    def _build_feature_frame(self, history: pd.DataFrame) -> pd.DataFrame:
        frame = history.copy().sort_index()
        frame["return_1d"] = frame["close"].pct_change(1)
        frame["return_5d"] = frame["close"].pct_change(5)
        frame["return_20d"] = frame["close"].pct_change(20)
        frame["volatility_5d"] = frame["return_1d"].rolling(5).std()
        frame["volatility_20d"] = frame["return_1d"].rolling(20).std()
        frame["sma_10"] = frame["close"].rolling(10).mean()
        frame["sma_20"] = frame["close"].rolling(20).mean()
        frame["sma_50"] = frame["close"].rolling(50).mean()
        frame["sma_200"] = frame["close"].rolling(200).mean()
        frame["sma_10_ratio"] = frame["close"] / frame["sma_10"] - 1
        frame["sma_20_ratio"] = frame["close"] / frame["sma_20"] - 1
        frame["sma_50_ratio"] = frame["close"] / frame["sma_50"] - 1
        frame["sma_200_ratio"] = frame["close"] / frame["sma_200"] - 1
        frame["volume_sma_5"] = frame["volume"].rolling(5).mean()
        frame["volume_sma_20"] = frame["volume"].rolling(20).mean()
        frame["volume_ratio_5_20"] = frame["volume_sma_5"] / frame["volume_sma_20"]
        frame["range_pct"] = (frame["high"] - frame["low"]) / frame["close"]
        frame["drawdown_60d"] = frame["close"] / frame["close"].rolling(60).max() - 1
        frame["rsi_14"] = self._compute_rsi(frame["close"], period=14)
        frame["target_return_1d"] = frame["close"].shift(-1) / frame["close"] - 1
        frame["target_up_1d"] = (frame["target_return_1d"] > 0).astype(int)
        frame["target_return_5d"] = frame["close"].shift(-5) / frame["close"] - 1
        frame["target_up_5d"] = (frame["target_return_5d"] > 0).astype(int)
        frame = frame.replace([np.inf, -np.inf], np.nan).dropna().copy()
        return frame

    def _fit_importance_model(self, x_train: pd.DataFrame, y_train: pd.Series) -> RandomForestClassifier:
        clf = RandomForestClassifier(
            n_estimators=300,
            max_depth=7,
            min_samples_leaf=6,
            random_state=42,
        )
        clf.fit(x_train, y_train)
        return clf

    def _run_horizon_model(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        x_train: pd.DataFrame,
        x_test: pd.DataFrame,
        latest_features: pd.DataFrame,
        target_return_column: str,
        target_up_column: str,
        horizon_days: int,
        latest_index: pd.Timestamp,
    ) -> HorizonForecast:
        clf = RandomForestClassifier(
            n_estimators=300,
            max_depth=7,
            min_samples_leaf=6,
            random_state=42 + horizon_days,
        )
        reg = RandomForestRegressor(
            n_estimators=250,
            max_depth=7,
            min_samples_leaf=6,
            random_state=42 + horizon_days,
        )

        y_train_cls = train_df[target_up_column]
        y_train_reg = train_df[target_return_column]
        y_test_cls = test_df[target_up_column]

        clf.fit(x_train, y_train_cls)
        reg.fit(x_train, y_train_reg)

        test_prob = clf.predict_proba(x_test)[:, 1]
        test_pred = (test_prob >= 0.5).astype(int)
        test_pred_return = reg.predict(x_test)

        holdout_accuracy = float((test_pred == y_test_cls).mean())
        positive_predictions = max(int(test_pred.sum()), 1)
        holdout_precision = float(((test_pred == 1) & (y_test_cls == 1)).sum() / positive_predictions)

        probability_up = float(clf.predict_proba(latest_features)[0, 1])
        predicted_return_pct = float(reg.predict(latest_features)[0] * 100)
        confidence = min(0.95, 0.45 + abs(probability_up - 0.5) * 1.2 + max(holdout_accuracy - 0.5, 0) * 0.8)

        if probability_up >= 0.57:
            outlook = "up"
        elif probability_up <= 0.43:
            outlook = "down"
        else:
            outlook = "sideways"

        history_with_predictions = test_df.copy()
        history_with_predictions["predicted_prob_up"] = test_prob
        history_with_predictions["predicted_label"] = np.where(test_pred == 1, "Up", "Down")
        history_with_predictions["predicted_return_pct"] = test_pred_return * 100

        target_date = (latest_index + pd.tseries.offsets.BDay(horizon_days)).strftime("%Y-%m-%d")
        return HorizonForecast(
            outlook=outlook,
            probability_up=probability_up,
            predicted_return_pct=predicted_return_pct,
            confidence=confidence,
            holdout_accuracy=holdout_accuracy,
            holdout_precision=holdout_precision,
            target_date=target_date,
            prediction_history=history_with_predictions,
            target_return_column=target_return_column,
            target_up_column=target_up_column,
        )

    def _build_final_recommendation(self, tomorrow: HorizonForecast, next_week: HorizonForecast) -> tuple[str, str]:
        if tomorrow.outlook == "up" and next_week.outlook == "up":
            return "Buy / Positive Bias", "Both the tomorrow and next-week models lean upward."
        if tomorrow.outlook == "down" and next_week.outlook == "down":
            return "Avoid / Bearish Bias", "Both horizons lean downward, so risk is skewed to the downside."
        if next_week.outlook == "up" and tomorrow.outlook == "sideways":
            return "Accumulate Gradually", "The near-term read is mixed, but the next-week model still leans positive."
        if next_week.outlook == "down" and tomorrow.outlook == "sideways":
            return "Wait / Avoid Fresh Entry", "Tomorrow is unclear and the one-week view is soft."
        return "Hold / Wait For Confirmation", "The two horizons disagree, so confirmation is better than forcing a trade."

    def _compute_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)
        avg_gain = gains.rolling(period).mean()
        avg_loss = losses.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)
