"""
LLM Agent module for evaluating alarm-degradation correlations.
"""
import os
import json
from typing import Dict, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMAgent:
    """Uses OpenAI API to evaluate correlations between degradations and alarms."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize LLM Agent.
        
        Args:
            model: OpenAI model to use (default: gpt-4o-mini)
            api_key: OpenAI API key (if None, loads from OPENAI_API_KEY env var)
        """
        self.model = model
        api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in .env file or pass api_key parameter.")
        
        self.client = OpenAI(api_key=api_key)
    
    def build_prompt(self, degradation: Dict, alarms: List[Dict]) -> str:
        """
        Build prompt for LLM analysis.
        
        Args:
            degradation: Degradation dictionary
            alarms: List of alarm dictionaries
            
        Returns:
            Formatted prompt string
        """
        # Format degradation information
        degradation_info = f"""
Degradation Details:
- Node: {degradation.get('node', 'Unknown')}
- Start Time: {degradation.get('start_timestamp', 'Unknown')}
- End Time: {degradation.get('end_timestamp', 'Unknown')}
- Duration: {degradation.get('duration_minutes', 0):.1f} minutes
- Minimum RRC SR Value: {degradation.get('min_value', 0):.2f}%
- Baseline (Threshold): {degradation.get('baseline_value', 0):.2f}%
- Deviation: {degradation.get('deviation_percent', 0):.1f}%
- Severity: {degradation.get('severity', 'Unknown')}
"""
        
        # Format alarm information
        alarms_info = "\nRelated Alarms (one entry per unique alarm ID; each may have multiple status events in the time window):\n"
        if alarms:
            for i, alarm in enumerate(alarms, 1):
                ts = alarm.get('timestamp', 'Unknown')
                if hasattr(ts, 'isoformat'):
                    ts = ts.isoformat()
                elif ts != 'Unknown':
                    ts = str(ts)
                block = f"""
Alarm {i}:
- Alarm ID: {alarm.get('alarm_id', 'Unknown')}
- First event in window - Temporal Relationship: {alarm.get('temporal_relationship', 'Unknown')}
- Time from Degradation Start: {float(alarm.get('time_from_degradation_start') or 0):.1f} minutes
- Alarm Type: {alarm.get('alarm_type', 'Unknown')}
- Specific Problem: {alarm.get('specific_problem', 'Unknown')}
- Probable Cause: {alarm.get('probable_cause', 'Unknown')}
- Additional Text: {alarm.get('additional_text', 'N/A')[:200] if alarm.get('additional_text') else 'N/A'}...
- Managed Object: {(alarm.get('managed_object_class') or 'Unknown')[:100]}...
"""
                status_timeline = alarm.get('status_timeline')
                if status_timeline and isinstance(status_timeline, list):
                    timeline_parts = []
                    for ev in status_timeline:
                        t = ev.get('timestamp', 'unknown')
                        sev = ev.get('perceived_severity', 'unknown')
                        cleared = ev.get('cleared', False)
                        label = "cleared" if cleared else "raised/updated"
                        timeline_parts.append(f"{t} - {sev} ({label})")
                    block += "- Status timeline (chronological): " + "; ".join(timeline_parts) + "\n"
                else:
                    block += f"- Severity: {alarm.get('perceived_severity', 'Unknown')}\n"
                    block += f"- Timestamp: {ts}\n"
                alarms_info += block
        else:
            alarms_info += "No alarms found in the time window.\n"
        
        prompt = f"""You are a telecommunications network expert analyzing RRC (Radio Resource Control) Success Rate (SR) KPI degradations and their correlation with Fault Management (FM) alarms.

RRC SR is a critical KPI that measures the success rate of RRC connection establishment attempts. Degradations in RRC SR can be caused by:
- Hardware failures (BBU, RRU, antennas)
- Transport link issues
- Radio interference
- Configuration problems
- Software bugs
- Power issues
- Environmental factors

{degradation_info}

{alarms_info}

Please analyze the correlation between the degradation and the alarms. For each alarm, infer from its Status timeline whether it was CLEARED within the time window (last event is CLEARED) or STILL ACTIVE at the end; mention this in your analysis and use it when judging causality (e.g. cleared during degradation may suggest a transient issue or that the condition was resolved).

Provide your analysis in the following JSON format. Include the optional fields when relevant.

{{
    "overall_verdict": "causal" | "possible" | "coincidental" | "no_correlation",
    "confidence_score": 0.0-1.0,
    "root_cause_analysis": "optional: short paragraph on likely root cause(s) and how alarm lifespans support or contradict that",
    "alarm_analysis": [
        {{
            "alarm_id": "string",
            "relevance_score": 0.0-1.0,
            "is_causal": true/false,
            "reasoning": "explanation",
            "lifespan_note": "optional: e.g. Cleared during window at 14:18:15 or Still active at end of time window",
            "suggested_fix": ["optional: 1-3 concrete steps to address this alarm, e.g. Verify RU link", "Restart affected sector"]
        }}
    ],
    "top_reasons": [
        "reason 1",
        "reason 2",
        "reason 3"
    ],
    "recommended_actions": [
        "specific, ordered action 1 (e.g. Isolate and restart BBU for node X)",
        "specific action 2 (e.g. Collect traces if degradation persists)"
    ],
    "analysis_summary": "detailed explanation that explicitly references alarm lifespans where relevant (e.g. Alarm A was cleared at 14:20; Alarm B remained active)"
}}

Guidelines:
- "causal": Strong evidence that alarms directly caused the degradation
- "possible": Some evidence of correlation but not definitive
- "coincidental": Alarms present but unlikely to be related
- "no_correlation": No alarms or alarms clearly unrelated

Consider:
1. Temporal correlation (alarms before/during degradation are more relevant)
2. Spatial correlation (same node/cell)
3. Alarm types that typically affect RRC SR (service affecting, radio issues, hardware failures)
4. Alarm severity and duration
5. Historical patterns
6. Alarm lifespan: from each alarm's Status timeline, note if it was cleared in the window or still active. Mention this in analysis_summary and in each alarm's lifespan_note. Use it to judge causality (e.g. alarm cleared during degradation vs still active at end).
7. Remediation: for each alarm provide 1-3 concrete suggested_fix steps based on alarm type, specific problem, and probable cause. recommended_actions should be specific and ordered (what to do, in what order; prefer e.g. Check X, Restart Y, Replace Z over vague advice).

If no alarms are found, recommend further investigation steps."""
        
        return prompt
    
    def evaluate_correlation(
        self,
        degradation: Dict,
        alarms: List[Dict],
        max_retries: int = 3
    ) -> Dict:
        """
        Evaluate correlation between degradation and alarms using LLM.
        
        Args:
            degradation: Degradation dictionary
            alarms: List of alarm dictionaries (can be empty)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with correlation analysis
        """
        prompt = self.build_prompt(degradation, alarms)
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a telecommunications network expert specializing in KPI degradation analysis and alarm correlation. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                # Parse JSON response
                content = response.choices[0].message.content
                result = json.loads(content)
                
                # Add metadata
                result['degradation_node'] = degradation.get('node')
                result['degradation_start'] = str(degradation.get('start_timestamp'))
                result['alarms_count'] = len(alarms)
                
                return result
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    continue
                # Fallback response if JSON parsing fails
                return {
                    "overall_verdict": "no_correlation",
                    "confidence_score": 0.0,
                    "root_cause_analysis": "",
                    "alarm_analysis": [],
                    "top_reasons": ["Failed to parse LLM response"],
                    "recommended_actions": ["Review LLM response manually"],
                    "analysis_summary": f"Error parsing LLM response: {str(e)}",
                    "error": str(e)
                }
            except Exception as e:
                if attempt < max_retries - 1:
                    continue
                return {
                    "overall_verdict": "no_correlation",
                    "confidence_score": 0.0,
                    "root_cause_analysis": "",
                    "alarm_analysis": [],
                    "top_reasons": ["LLM API error"],
                    "recommended_actions": ["Check API key and network connection"],
                    "analysis_summary": f"Error calling LLM API: {str(e)}",
                    "error": str(e)
                }
        
        # Should not reach here, but just in case
        return {
            "overall_verdict": "no_correlation",
            "confidence_score": 0.0,
            "root_cause_analysis": "",
            "alarm_analysis": [],
            "top_reasons": ["Unknown error"],
            "recommended_actions": ["Retry analysis"],
            "analysis_summary": "Failed to get LLM response after multiple attempts"
        }
