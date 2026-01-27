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
        alarms_info = "\nRelated Alarms:\n"
        if alarms:
            for i, alarm in enumerate(alarms, 1):
                alarms_info += f"""
Alarm {i}:
- Alarm ID: {alarm.get('alarm_id', 'Unknown')}
- Timestamp: {alarm.get('timestamp', 'Unknown')}
- Temporal Relationship: {alarm.get('temporal_relationship', 'Unknown')}
- Time from Degradation Start: {alarm.get('time_from_degradation_start', 0):.1f} minutes
- Severity: {alarm.get('perceived_severity', 'Unknown')}
- Alarm Type: {alarm.get('alarm_type', 'Unknown')}
- Specific Problem: {alarm.get('specific_problem', 'Unknown')}
- Probable Cause: {alarm.get('probable_cause', 'Unknown')}
- Additional Text: {alarm.get('additional_text', 'N/A')[:200]}...
- Managed Object: {alarm.get('managed_object_class', 'Unknown')[:100]}...
"""
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

Please analyze the correlation between the degradation and the alarms. Provide your analysis in the following JSON format:

{{
    "overall_verdict": "causal" | "possible" | "coincidental" | "no_correlation",
    "confidence_score": 0.0-1.0,
    "alarm_analysis": [
        {{
            "alarm_id": "string",
            "relevance_score": 0.0-1.0,
            "is_causal": true/false,
            "reasoning": "explanation"
        }}
    ],
    "top_reasons": [
        "reason 1",
        "reason 2",
        "reason 3"
    ],
    "recommended_actions": [
        "action 1",
        "action 2",
        "action 3"
    ],
    "analysis_summary": "detailed explanation of the correlation analysis"
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
            "alarm_analysis": [],
            "top_reasons": ["Unknown error"],
            "recommended_actions": ["Retry analysis"],
            "analysis_summary": "Failed to get LLM response after multiple attempts"
        }
