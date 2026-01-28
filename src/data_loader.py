"""
Data loading module for KPI and alarm data.
"""
import pandas as pd
import json
import re
from datetime import datetime
from dateutil import parser
from typing import Optional


def parse_alarm_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse alarm timestamp from format like "2025-9-10,14:18:14.0,+3:0"
    
    Args:
        timestamp_str: Timestamp string from alarm data
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not timestamp_str or timestamp_str.strip() == "":
        return None
    
    try:
        # Handle format: "2025-9-10,14:18:14.0,+3:0"
        # Split by comma to separate date, time, and timezone
        parts = timestamp_str.split(',')
        if len(parts) >= 2:
            date_part = parts[0]
            time_part = parts[1]
            # Combine date and time
            dt_str = f"{date_part} {time_part.split('.')[0]}"  # Remove milliseconds
            dt = parser.parse(dt_str)
            return dt
        else:
            # Try standard parsing
            return parser.parse(timestamp_str)
    except Exception as e:
        print(f"Warning: Could not parse timestamp '{timestamp_str}': {e}")
        return None


def extract_node_from_managed_object(managed_object: str) -> Optional[str]:
    """
    Extract node identifier from managedObjectClass.
    
    Examples:
        "PLMN-PLMN/MRBTS-685256/..." -> "MRBTS-685256"
        "PLMN-PLMN/BSC-388042/..." -> "BSC-388042"
    """
    if not managed_object:
        return None
    
    try:
        parts = managed_object.split('/')
        for part in parts:
            if part.startswith('MRBTS-') or part.startswith('BSC-'):
                return part
        # If no MRBTS/BSC found, return the first meaningful part after PLMN
        if len(parts) > 1:
            return parts[1] if parts[1] != 'PLMN-PLMN' else (parts[2] if len(parts) > 2 else None)
    except Exception:
        pass
    return None


def extract_node_id_from_managed_object(managed_object: str) -> Optional[str]:
    """
    Extract canonical node ID (numeric part) from managedObjectClass.
    Used for same-node matching with KPI data.

    Examples:
        "PLMN-PLMN/MRBTS-1900/..." -> "1900"
        "PLMN-PLMN/BSC-388042/..." -> "388042"
    """
    if not managed_object:
        return None
    match = re.search(r'(?:MRBTS-|BSC-)(\d+)', managed_object)
    return match.group(1) if match else None


def normalize_to_node_id(node: str) -> str:
    """
    Normalize a node identifier to canonical node ID for matching.
    If node is MRBTS-X or BSC-X, return the numeric part; otherwise return as-is.

    Examples:
        "MRBTS-1900" -> "1900"
        "BSC-388042" -> "388042"
        "1900" -> "1900"
    """
    if not node:
        return ""
    s = str(node).strip()
    match = re.search(r'(?:MRBTS-|BSC-)(\d+)', s)
    return match.group(1) if match else s


def extract_node_from_nbi_info(nbi_info: str) -> Optional[str]:
    """
    Extract node identifier from nbiOptionalInformation.
    
    Format: "NEName=EMH229|siteObjName=EMH229_TWL|..."
    """
    if not nbi_info:
        return None
    
    try:
        # Look for NEName first
        if 'NEName=' in nbi_info:
            parts = nbi_info.split('NEName=')
            if len(parts) > 1:
                node = parts[1].split('|')[0].strip()
                if node:
                    return node
        
        # Fallback to siteObjName
        if 'siteObjName=' in nbi_info:
            parts = nbi_info.split('siteObjName=')
            if len(parts) > 1:
                node = parts[1].split('|')[0].strip()
                if node:
                    return node
    except Exception:
        pass
    return None


def load_kpi_data(excel_path: str) -> pd.DataFrame:
    """
    Load KPI data from Excel file.
    
    Args:
        excel_path: Path to Excel file
        
    Returns:
        DataFrame with columns: node, timestamp, rrc_sr
    """
    df = pd.read_excel(excel_path)
    
    # Try to identify columns (case-insensitive)
    node_col = None
    date_col = None
    hour_col = None
    timestamp_col = None
    rrc_sr_col = None
    
    for col in df.columns:
        col_lower = str(col).lower()
        if 'node' in col_lower or 'site' in col_lower or 'cell' in col_lower:
            node_col = col
        elif 'date' in col_lower:
            date_col = col
        elif 'hour' in col_lower:
            hour_col = col
        elif 'time' in col_lower or 'timestamp' in col_lower:
            timestamp_col = col
        elif 'rrc' in col_lower or 'sr' in col_lower or 'success' in col_lower:
            rrc_sr_col = col
    
    # If columns not found, try to infer from position
    if not node_col:
        node_col = df.columns[0]
    if not date_col and not timestamp_col:
        # Check if second column is date
        if len(df.columns) > 1:
            date_col = df.columns[1]
    if not hour_col:
        # Check if third column is hour
        if len(df.columns) > 2 and 'hour' in str(df.columns[2]).lower():
            hour_col = df.columns[2]
    if not rrc_sr_col:
        # Find RRC SR column
        for col in df.columns:
            if 'rrc' in str(col).lower() or 'sr' in str(col).lower():
                rrc_sr_col = col
                break
        if not rrc_sr_col and len(df.columns) > 3:
            rrc_sr_col = df.columns[3]
    
    # Create standardized DataFrame
    result_df = pd.DataFrame()
    result_df['node'] = df[node_col].astype(str)
    
    # Construct timestamp from date and hour if available
    if date_col and hour_col:
        # Combine date and hour columns
        try:
            # Parse date
            dates = pd.to_datetime(df[date_col], errors='coerce')
            # Handle hour (could be 0-23 or 1-24)
            hours = pd.to_numeric(df[hour_col], errors='coerce')
            # Adjust hour if it's 24 (should be 0 of next day)
            hours_adjusted = hours.copy()
            dates_adjusted = dates.copy()
            mask_24 = hours == 24
            if mask_24.any():
                hours_adjusted[mask_24] = 0
                dates_adjusted[mask_24] = dates_adjusted[mask_24] + pd.Timedelta(days=1)
            
            # Combine date and hour
            result_df['timestamp'] = dates_adjusted + pd.to_timedelta(hours_adjusted, unit='h')
        except Exception as e:
            print(f"Warning: Could not combine date and hour columns: {e}")
            # Fallback to just date
            result_df['timestamp'] = pd.to_datetime(df[date_col], errors='coerce')
    elif timestamp_col:
        # Use single timestamp column
        result_df['timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
    elif date_col:
        # Use only date column (no hour information)
        result_df['timestamp'] = pd.to_datetime(df[date_col], errors='coerce')
    else:
        raise ValueError("Could not find timestamp/date column in Excel file")
    
    if rrc_sr_col:
        result_df['rrc_sr'] = pd.to_numeric(df[rrc_sr_col], errors='coerce')
    else:
        raise ValueError("Could not find RRC SR column in Excel file")
    
    # Remove rows with missing data
    result_df = result_df.dropna(subset=['timestamp', 'rrc_sr', 'node'])
    
    # Sort by node and timestamp
    result_df = result_df.sort_values(['node', 'timestamp']).reset_index(drop=True)
    
    return result_df


def load_alarms_data(json_path: str) -> pd.DataFrame:
    """
    Load alarm data from JSON file.
    Supports both array format and line-delimited format.
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        DataFrame with standardized alarm columns
    """
    alarms = []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        
        # Try to parse as JSON array first
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                alarms = parsed
            else:
                alarms = [parsed]
        except json.JSONDecodeError:
            # If that fails, try line-delimited format
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                try:
                    alarm = json.loads(line)
                    alarms.append(alarm)
                except json.JSONDecodeError:
                    continue
    
    if not alarms:
        return pd.DataFrame()
    
    # Extract relevant fields
    alarm_records = []
    for alarm in alarms:
        # Extract node identifier
        node = None
        managed_object = alarm.get('managedObjectClass', '')
        nbi_info = alarm.get('nbiOptionalInformation', '')
        
        node = extract_node_from_managed_object(managed_object)
        if not node:
            node = extract_node_from_nbi_info(nbi_info)
        
        node_id = extract_node_id_from_managed_object(managed_object)
        
        # Parse timestamps
        alarm_raised = parse_alarm_timestamp(alarm.get('alarmRaisedTime', ''))
        alarm_cleared = parse_alarm_timestamp(alarm.get('alarmClearedTime', ''))
        event_time = parse_alarm_timestamp(alarm.get('nbiEventTime', ''))
        
        # Use event_time as primary timestamp if available
        primary_timestamp = event_time or alarm_raised
        
        alarm_records.append({
            'alarm_id': alarm.get('alarmId', ''),
            'node': node,
            'node_id': node_id,
            'timestamp': primary_timestamp,
            'alarm_raised_time': alarm_raised,
            'alarm_cleared_time': alarm_cleared,
            'event_time': event_time,
            'perceived_severity': alarm.get('perceivedSeverity', ''),
            'alarm_type': alarm.get('alarmType', ''),
            'specific_problem': alarm.get('specificProblem', ''),
            'probable_cause': alarm.get('probableCause', ''),
            'additional_text': alarm.get('additionalText', ''),
            'managed_object_class': managed_object,
            'nbi_optional_info': nbi_info,
            'event_type': alarm.get('EventType', ''),
        })
    
    df = pd.DataFrame(alarm_records)
    
    # Remove rows with missing timestamp
    df = df.dropna(subset=['timestamp'])
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df
