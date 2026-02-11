"""
Degradation detection module for RRC SR KPI.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any

try:
    from config import DEFAULT_MEDIAN_PERCENTAGE, DEFAULT_STATIC_THRESHOLD
except ImportError:
    DEFAULT_MEDIAN_PERCENTAGE = 90
    DEFAULT_STATIC_THRESHOLD = 95.0


class DegradationDetector:
    """Detects degradations in RRC SR KPI using median-based + static thresholds (both conditions must be met)."""

    def __init__(self):
        self.node_thresholds: Dict[str, float] = {}
        self.node_medians: Dict[str, float] = {}

    def get_node_medians(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute median RRC SR for each node.

        Args:
            df: DataFrame with KPI data (columns: node, rrc_sr)

        Returns:
            Dictionary mapping node (str) to median value
        """
        medians = {}
        for node in df["node"].unique():
            node_str = str(node)
            node_data = df[df["node"] == node]["rrc_sr"].dropna()
            if len(node_data) == 0:
                continue
            med = float(node_data.median())
            medians[node_str] = med
        self.node_medians = medians
        return medians

    def detect_degradations(
        self,
        df: pd.DataFrame,
        node_config: Dict[str, Dict[str, Any]],
        min_duration_minutes: int = 5,
        default_median_percentage: float = None,
        default_static_threshold: float = None,
    ) -> pd.DataFrame:
        """
        Detect degradation periods in RRC SR KPI.
        A reading is degraded only if BOTH are true:
        - rrc_sr < (median_percentage/100) * median (dynamic threshold)
        - rrc_sr < static_threshold

        Args:
            df: DataFrame with columns: node, timestamp, rrc_sr
            node_config: Per-node config: { node_id: {"median_percentage": float, "static_threshold": float} }
            min_duration_minutes: Minimum duration in minutes for a degradation period
            default_median_percentage: Used when a node is missing from node_config
            default_static_threshold: Used when a node is missing from node_config

        Returns:
            DataFrame with columns:
                - node, start_timestamp, end_timestamp, min_value
                - baseline_value: effective threshold (min of dynamic and static) for deviation
                - duration_minutes, severity, deviation_percent, readings_count
        """
        if default_median_percentage is None:
            default_median_percentage = DEFAULT_MEDIAN_PERCENTAGE
        if default_static_threshold is None:
            default_static_threshold = DEFAULT_STATIC_THRESHOLD

        medians = self.get_node_medians(df)
        degradations = []
        self.node_thresholds = {}

        for node in df["node"].unique():
            node_str = str(node)
            if node_str not in medians:
                continue

            median_val = medians[node_str]
            cfg = node_config.get(node_str) or {}
            median_pct = float(cfg.get("median_percentage", default_median_percentage))
            static_thr = float(cfg.get("static_threshold", default_static_threshold))

            # Dynamic threshold = median * (percentage / 100)
            dynamic_threshold = median_val * (median_pct / 100.0) if median_val > 0 else 0.0
            # Effective threshold for baseline_value / deviation: the stricter (lower) bar
            effective_threshold = min(dynamic_threshold, static_thr)

            node_data = df[df["node"] == node].copy()
            node_data = node_data.sort_values("timestamp").reset_index(drop=True)

            self.node_thresholds[node_str] = effective_threshold

            # Degraded only if BOTH conditions are met
            node_data["is_degraded"] = (
                (node_data["rrc_sr"] < dynamic_threshold) & (node_data["rrc_sr"] < static_thr)
            )

            node_data["group"] = (node_data["is_degraded"] != node_data["is_degraded"].shift()).cumsum()

            for group_id, group_df in node_data[node_data["is_degraded"]].groupby("group"):
                start_time = group_df["timestamp"].min()
                end_time = group_df["timestamp"].max()
                min_value = group_df["rrc_sr"].min()

                if len(group_df) == 1:
                    idx = group_df.index[0]
                    if idx < len(node_data) - 1:
                        next_time = node_data.loc[idx + 1, "timestamp"]
                        duration = (next_time - start_time).total_seconds() / 60
                    else:
                        duration = 60.0
                else:
                    duration = (end_time - start_time).total_seconds() / 60
                    time_diff = node_data["timestamp"].diff().median()
                    if pd.notna(time_diff):
                        duration += time_diff.total_seconds() / 60
                    else:
                        duration += 60.0

                if duration < min_duration_minutes:
                    continue

                deviation = effective_threshold - min_value
                deviation_pct = (deviation / effective_threshold) * 100 if effective_threshold > 0 else 0

                if deviation_pct > 50:
                    severity = "CRITICAL"
                elif deviation_pct > 25:
                    severity = "MAJOR"
                elif deviation_pct > 10:
                    severity = "MINOR"
                else:
                    severity = "WARNING"

                degradations.append({
                    "node": node,
                    "start_timestamp": start_time,
                    "end_timestamp": end_time,
                    "min_value": min_value,
                    "baseline_value": effective_threshold,
                    "duration_minutes": duration,
                    "severity": severity,
                    "deviation_percent": deviation_pct,
                    "readings_count": len(group_df),
                })

        if not degradations:
            return pd.DataFrame(
                columns=[
                    "node", "start_timestamp", "end_timestamp", "min_value",
                    "baseline_value", "duration_minutes", "severity",
                    "deviation_percent", "readings_count",
                ]
            )

        result_df = pd.DataFrame(degradations)
        result_df = result_df.sort_values(["node", "start_timestamp"]).reset_index(drop=True)
        return result_df

    def get_node_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get statistics for each node.

        Args:
            df: DataFrame with KPI data

        Returns:
            DataFrame with node statistics
        """
        stats = []
        for node in df["node"].unique():
            node_data = df[df["node"] == node]["rrc_sr"].dropna()
            if len(node_data) == 0:
                continue
            stats.append({
                "node": node,
                "count": len(node_data),
                "mean": node_data.mean(),
                "median": node_data.median(),
                "std": node_data.std(),
                "min": node_data.min(),
                "max": node_data.max(),
                "p5": np.percentile(node_data, 5),
                "p10": np.percentile(node_data, 10),
                "p25": np.percentile(node_data, 25),
                "p75": np.percentile(node_data, 75),
                "p90": np.percentile(node_data, 90),
                "p95": np.percentile(node_data, 95),
            })
        return pd.DataFrame(stats)
