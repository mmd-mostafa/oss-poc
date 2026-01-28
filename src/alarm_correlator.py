"""
Alarm correlation module for finding alarms within degradation time windows.
"""
import pandas as pd
from datetime import timedelta
from typing import List, Dict, Optional

from .data_loader import (
    normalize_to_node_id,
    extract_node_id_from_managed_object,
)


class AlarmCorrelator:
    """Correlates alarms with degradation periods based on node and time windows."""
    
    def __init__(self):
        pass
    
    def _get_alarm_node_id(self, alarm: Dict) -> Optional[str]:
        """
        Get canonical node_id for an alarm (from pre-loaded node_id or managed_object_class).
        """
        raw = alarm.get('node_id')
        if raw is not None and pd.notna(raw):
            return str(raw)
        managed = alarm.get('managed_object_class', '') or alarm.get('managedObjectClass', '')
        node_id = extract_node_id_from_managed_object(managed)
        return str(node_id) if node_id else None
    
    def find_alarms_in_window(
        self,
        degradation: Dict,
        alarms_df: pd.DataFrame,
        time_before_min: int = 30,
        time_after_min: int = 30
    ) -> pd.DataFrame:
        """
        Find alarms within time window around degradation period.
        Only alarms on the same node (canonical node_id from managedObjectClass) are included.
        
        Args:
            degradation: Degradation dictionary with node, start_timestamp, end_timestamp
            alarms_df: DataFrame with alarm data (must include node_id when from managedObjectClass)
            time_before_min: Minutes before degradation start to search
            time_after_min: Minutes after degradation end to search
            
        Returns:
            DataFrame with matched alarms and temporal relationship
        """
        degradation_node_id = normalize_to_node_id(degradation['node'])
        start_time = degradation['start_timestamp']
        end_time = degradation['end_timestamp']
        
        window_start = start_time - timedelta(minutes=time_before_min)
        window_end = end_time + timedelta(minutes=time_after_min)
        
        matched_alarms = []
        
        for _, alarm in alarms_df.iterrows():
            alarm_node_id = self._get_alarm_node_id(alarm.to_dict())
            if alarm_node_id is None:
                continue
            if str(alarm_node_id) != str(degradation_node_id):
                continue
            
            alarm_time = alarm['timestamp']
            if not (window_start <= alarm_time <= window_end):
                continue
            
            if alarm_time < start_time:
                relationship = 'BEFORE'
            elif alarm_time > end_time:
                relationship = 'AFTER'
            else:
                relationship = 'DURING'
            
            alarm_dict = alarm.to_dict()
            alarm_dict['temporal_relationship'] = relationship
            alarm_dict['time_from_degradation_start'] = (alarm_time - start_time).total_seconds() / 60
            matched_alarms.append(alarm_dict)
        
        if not matched_alarms:
            return pd.DataFrame()
        
        result_df = pd.DataFrame(matched_alarms)
        result_df = result_df.sort_values('timestamp').reset_index(drop=True)
        return result_df
    
    def correlate_all_degradations(
        self,
        degradations_df: pd.DataFrame,
        alarms_df: pd.DataFrame,
        kpi_nodes: List[str],
        time_before_min: int = 30,
        time_after_min: int = 30
    ) -> Dict[int, pd.DataFrame]:
        """
        Correlate all degradations with alarms.
        
        Args:
            degradations_df: DataFrame with degradation periods
            alarms_df: DataFrame with alarm data
            kpi_nodes: List of node identifiers from KPI data
            time_before_min: Minutes before degradation start
            time_after_min: Minutes after degradation end
            
        Returns:
            Dictionary mapping degradation index to DataFrame of correlated alarms
        """
        correlations = {}
        
        for idx, degradation in degradations_df.iterrows():
            alarms = self.find_alarms_in_window(
                degradation.to_dict(),
                alarms_df,
                time_before_min,
                time_after_min
            )
            correlations[idx] = alarms
        
        return correlations
