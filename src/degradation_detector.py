"""
Degradation detection module for RRC SR KPI.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import timedelta


class DegradationDetector:
    """Detects degradations in RRC SR KPI using percentile-based thresholds."""
    
    def __init__(self):
        self.node_thresholds: Dict[str, float] = {}
    
    def calculate_threshold(self, df: pd.DataFrame, node: str, percentile: float) -> float:
        """
        Calculate percentile threshold for a specific node.
        
        Args:
            df: DataFrame with KPI data
            node: Node identifier
            percentile: Percentile value (e.g., 10 for 10th percentile)
            
        Returns:
            Threshold value below which readings are considered degraded
        """
        node_data = df[df['node'] == node]['rrc_sr'].dropna()
        
        if len(node_data) == 0:
            return np.nan
        
        threshold = np.percentile(node_data, percentile)
        return threshold
    
    def calculate_all_thresholds(self, df: pd.DataFrame, percentile: float) -> Dict[str, float]:
        """
        Calculate thresholds for all nodes.
        
        Args:
            df: DataFrame with KPI data
            percentile: Percentile value
            
        Returns:
            Dictionary mapping node to threshold value
        """
        thresholds = {}
        for node in df['node'].unique():
            threshold = self.calculate_threshold(df, node, percentile)
            if not np.isnan(threshold):
                thresholds[node] = threshold
        
        self.node_thresholds = thresholds
        return thresholds
    
    def detect_degradations(
        self, 
        df: pd.DataFrame, 
        percentile: float = 10,
        min_duration_minutes: int = 5
    ) -> pd.DataFrame:
        """
        Detect degradation periods in RRC SR KPI.
        
        Args:
            df: DataFrame with columns: node, timestamp, rrc_sr
            percentile: Percentile threshold (default: 10)
            min_duration_minutes: Minimum duration in minutes for a degradation period
            
        Returns:
            DataFrame with columns:
                - node: Node identifier
                - start_timestamp: Start of degradation
                - end_timestamp: End of degradation
                - min_value: Minimum RRC SR value during degradation
                - baseline_value: Threshold value (percentile)
                - duration_minutes: Duration of degradation in minutes
                - severity: Severity level based on how far below threshold
        """
        # Calculate thresholds for all nodes
        thresholds = self.calculate_all_thresholds(df, percentile)
        
        degradations = []
        
        for node in df['node'].unique():
            if node not in thresholds:
                continue
            
            threshold = thresholds[node]
            node_data = df[df['node'] == node].copy()
            node_data = node_data.sort_values('timestamp').reset_index(drop=True)
            
            # Identify degraded readings
            node_data['is_degraded'] = node_data['rrc_sr'] < threshold
            
            # Group consecutive degraded readings
            node_data['group'] = (node_data['is_degraded'] != node_data['is_degraded'].shift()).cumsum()
            
            # Process each group of degraded readings
            for group_id, group_df in node_data[node_data['is_degraded']].groupby('group'):
                start_time = group_df['timestamp'].min()
                end_time = group_df['timestamp'].max()
                min_value = group_df['rrc_sr'].min()
                
                # Calculate duration
                # For single reading, use the time difference to next reading or assume 1 hour
                if len(group_df) == 1:
                    # Single degraded reading - check time to next reading
                    idx = group_df.index[0]
                    if idx < len(node_data) - 1:
                        next_time = node_data.loc[idx + 1, 'timestamp']
                        duration = (next_time - start_time).total_seconds() / 60
                    else:
                        # Last reading, assume 1 hour duration
                        duration = 60.0
                else:
                    # Multiple consecutive readings
                    duration = (end_time - start_time).total_seconds() / 60
                    # Add the duration of the last reading (assume 1 hour if not specified)
                    if len(group_df) > 1:
                        # For hourly data, add 1 hour for the last reading
                        time_diff = node_data['timestamp'].diff().median()
                        if pd.notna(time_diff):
                            duration += time_diff.total_seconds() / 60
                        else:
                            duration += 60.0  # Default to 1 hour
                
                # Skip if duration is too short
                if duration < min_duration_minutes:
                    continue
                
                # Calculate severity based on how far below threshold
                deviation = threshold - min_value
                deviation_pct = (deviation / threshold) * 100 if threshold > 0 else 0
                
                if deviation_pct > 50:
                    severity = 'CRITICAL'
                elif deviation_pct > 25:
                    severity = 'MAJOR'
                elif deviation_pct > 10:
                    severity = 'MINOR'
                else:
                    severity = 'WARNING'
                
                degradations.append({
                    'node': node,
                    'start_timestamp': start_time,
                    'end_timestamp': end_time,
                    'min_value': min_value,
                    'baseline_value': threshold,
                    'duration_minutes': duration,
                    'severity': severity,
                    'deviation_percent': deviation_pct,
                    'readings_count': len(group_df)
                })
        
        if not degradations:
            return pd.DataFrame(columns=[
                'node', 'start_timestamp', 'end_timestamp', 'min_value',
                'baseline_value', 'duration_minutes', 'severity',
                'deviation_percent', 'readings_count'
            ])
        
        result_df = pd.DataFrame(degradations)
        result_df = result_df.sort_values(['node', 'start_timestamp']).reset_index(drop=True)
        
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
        for node in df['node'].unique():
            node_data = df[df['node'] == node]['rrc_sr'].dropna()
            
            if len(node_data) == 0:
                continue
            
            stats.append({
                'node': node,
                'count': len(node_data),
                'mean': node_data.mean(),
                'median': node_data.median(),
                'std': node_data.std(),
                'min': node_data.min(),
                'max': node_data.max(),
                'p5': np.percentile(node_data, 5),
                'p10': np.percentile(node_data, 10),
                'p25': np.percentile(node_data, 25),
                'p75': np.percentile(node_data, 75),
                'p90': np.percentile(node_data, 90),
                'p95': np.percentile(node_data, 95),
            })
        
        return pd.DataFrame(stats)
