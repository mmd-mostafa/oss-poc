"""
Alarm correlation module for finding alarms within degradation time windows.
"""
import pandas as pd
from datetime import timedelta
from typing import List, Dict, Optional
import re


class AlarmCorrelator:
    """Correlates alarms with degradation periods based on node and time windows."""
    
    def __init__(self):
        self.node_mapping: Dict[str, List[str]] = {}
    
    def extract_node_from_alarm(self, alarm: Dict) -> Optional[str]:
        """
        Extract node identifier from alarm data.
        
        Args:
            alarm: Alarm dictionary with managedObjectClass and nbiOptionalInformation
            
        Returns:
            Node identifier or None
        """
        # Try managedObjectClass first
        managed_object = alarm.get('managed_object_class', '') or alarm.get('managedObjectClass', '')
        if managed_object:
            # Extract MRBTS or BSC identifier
            match = re.search(r'(MRBTS-\d+|BSC-\d+)', managed_object)
            if match:
                return match.group(1)
            
            # Extract site name from path
            parts = managed_object.split('/')
            for part in parts:
                if part.startswith('MRBTS-') or part.startswith('BSC-') or part.startswith('SITE-'):
                    return part
        
        # Try nbiOptionalInformation
        nbi_info = alarm.get('nbi_optional_info', '') or alarm.get('nbiOptionalInformation', '')
        if nbi_info:
            # Extract NEName
            match = re.search(r'NEName=([^|]+)', nbi_info)
            if match:
                return match.group(1).strip()
            
            # Extract siteObjName
            match = re.search(r'siteObjName=([^|]+)', nbi_info)
            if match:
                return match.group(1).strip()
        
        return None
    
    def normalize_node_name(self, node: str) -> str:
        """
        Normalize node name for matching (remove common suffixes/prefixes).
        
        Args:
            node: Node identifier
            
        Returns:
            Normalized node name
        """
        if not node:
            return ""
        
        # Remove common suffixes
        node = re.sub(r'_TWL$', '', node)
        node = re.sub(r'_ZH$', '', node)
        node = re.sub(r'_OD$', '', node)
        
        return node.strip().upper()
    
    def build_node_mapping(self, kpi_nodes: List[str], alarm_df: pd.DataFrame):
        """
        Build mapping between KPI nodes and alarm nodes for fuzzy matching.
        
        Args:
            kpi_nodes: List of node identifiers from KPI data
            alarm_df: DataFrame with alarm data
        """
        kpi_normalized = {self.normalize_node_name(node): node for node in kpi_nodes}
        alarm_nodes = set()
        
        for _, alarm in alarm_df.iterrows():
            node = self.extract_node_from_alarm(alarm.to_dict())
            if node:
                alarm_nodes.add(node)
        
        alarm_normalized = {self.normalize_node_name(node): node for node in alarm_nodes}
        
        # Create mapping
        mapping = {}
        for norm_kpi, kpi in kpi_normalized.items():
            # Exact match
            if norm_kpi in alarm_normalized:
                mapping[kpi] = [alarm_normalized[norm_kpi]]
            else:
                # Partial match (contains)
                matches = [alarm for norm_alarm, alarm in alarm_normalized.items() 
                          if norm_kpi in norm_alarm or norm_alarm in norm_kpi]
                if matches:
                    mapping[kpi] = matches
                else:
                    # Try to match MRBTS/BSC numbers
                    kpi_match = re.search(r'(\d+)', kpi)
                    if kpi_match:
                        kpi_num = kpi_match.group(1)
                        matches = [alarm for alarm in alarm_nodes if kpi_num in str(alarm)]
                        if matches:
                            mapping[kpi] = matches
        
        self.node_mapping = mapping
    
    def find_alarms_in_window(
        self,
        degradation: Dict,
        alarms_df: pd.DataFrame,
        time_before_min: int = 30,
        time_after_min: int = 30
    ) -> pd.DataFrame:
        """
        Find alarms within time window around degradation period.
        
        Args:
            degradation: Degradation dictionary with node, start_timestamp, end_timestamp
            alarms_df: DataFrame with alarm data
            time_before_min: Minutes before degradation start to search
            time_after_min: Minutes after degradation end to search
            
        Returns:
            DataFrame with matched alarms and temporal relationship
        """
        node = degradation['node']
        start_time = degradation['start_timestamp']
        end_time = degradation['end_timestamp']
        
        # Calculate time window
        window_start = start_time - timedelta(minutes=time_before_min)
        window_end = end_time + timedelta(minutes=time_after_min)
        
        # Get potential matching nodes
        matching_nodes = [node]
        if node in self.node_mapping:
            matching_nodes.extend(self.node_mapping[node])
        
        # Filter alarms by node and time window
        matched_alarms = []
        
        for _, alarm in alarms_df.iterrows():
            alarm_node = self.extract_node_from_alarm(alarm.to_dict())
            alarm_time = alarm['timestamp']
            
            # Check if node matches
            node_match = False
            if alarm_node:
                # Direct match
                if alarm_node == node or alarm_node in matching_nodes:
                    node_match = True
                # Normalized match
                elif (self.normalize_node_name(alarm_node) == self.normalize_node_name(node) or
                      any(self.normalize_node_name(alarm_node) == self.normalize_node_name(n) 
                          for n in matching_nodes)):
                    node_match = True
                # Partial match (node identifier in alarm node or vice versa)
                elif (node in str(alarm_node) or str(alarm_node) in node):
                    node_match = True
            
            # Check if time is within window
            if node_match and window_start <= alarm_time <= window_end:
                # Determine temporal relationship
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
        # Build node mapping
        self.build_node_mapping(kpi_nodes, alarms_df)
        
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
