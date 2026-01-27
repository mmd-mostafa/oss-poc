"""
Main processing pipeline for degradation detection and alarm correlation.
"""
import pandas as pd
from typing import Dict, Optional
from .data_loader import load_kpi_data, load_alarms_data
from .degradation_detector import DegradationDetector
from .alarm_correlator import AlarmCorrelator
from .llm_agent import LLMAgent


class ProcessingPipeline:
    """Orchestrates the complete processing workflow."""
    
    def __init__(
        self,
        percentile: float = 10,
        time_before_min: int = 30,
        time_after_min: int = 30,
        llm_model: str = "gpt-4o-mini",
        llm_api_key: Optional[str] = None
    ):
        """
        Initialize processing pipeline.
        
        Args:
            percentile: Percentile threshold for degradation detection
            time_before_min: Minutes before degradation to search for alarms
            time_after_min: Minutes after degradation to search for alarms
            llm_model: OpenAI model to use
            llm_api_key: OpenAI API key (if None, loads from env)
        """
        self.percentile = percentile
        self.time_before_min = time_before_min
        self.time_after_min = time_after_min
        
        self.detector = DegradationDetector()
        self.correlator = AlarmCorrelator()
        self.llm_agent = LLMAgent(model=llm_model, api_key=llm_api_key)
        
        self.kpi_df: Optional[pd.DataFrame] = None
        self.alarms_df: Optional[pd.DataFrame] = None
        self.degradations_df: Optional[pd.DataFrame] = None
        self.correlations: Dict[int, pd.DataFrame] = {}
        self.llm_analyses: Dict[int, Dict] = {}
        self._correlations_computed: bool = False
    
    def load_data(self, kpi_path: str, alarms_path: str):
        """
        Load KPI and alarm data.
        
        Args:
            kpi_path: Path to Excel file with KPI data
            alarms_path: Path to JSON file with alarm data
        """
        print("Loading KPI data...")
        self.kpi_df = load_kpi_data(kpi_path)
        print(f"Loaded {len(self.kpi_df)} KPI readings for {self.kpi_df['node'].nunique()} nodes")
        
        print("Loading alarm data...")
        self.alarms_df = load_alarms_data(alarms_path)
        print(f"Loaded {len(self.alarms_df)} alarms")
    
    def detect_degradations(self):
        """Detect degradations in KPI data."""
        if self.kpi_df is None:
            raise ValueError("KPI data not loaded. Call load_data() first.")
        
        print(f"Detecting degradations using {self.percentile}th percentile threshold...")
        self.degradations_df = self.detector.detect_degradations(
            self.kpi_df,
            percentile=self.percentile
        )
        print(f"Found {len(self.degradations_df)} degradation periods")
    
    def correlate_alarms(self):
        """Correlate alarms with degradation periods."""
        if self.degradations_df is None:
            raise ValueError("Degradations not detected. Call detect_degradations() first.")
        if self.alarms_df is None:
            raise ValueError("Alarm data not loaded. Call load_data() first.")
        
        if len(self.degradations_df) == 0:
            print("No degradations found. Skipping alarm correlation.")
            self.correlations = {}
            self._correlations_computed = True
            return
        
        print("Correlating alarms with degradations...")
        kpi_nodes = self.kpi_df['node'].unique().tolist()
        self.correlations = self.correlator.correlate_all_degradations(
            self.degradations_df,
            self.alarms_df,
            kpi_nodes,
            self.time_before_min,
            self.time_after_min
        )
        self._correlations_computed = True
        
        total_alarms = sum(len(df) for df in self.correlations.values())
        degradations_with_alarms = sum(1 for df in self.correlations.values() if len(df) > 0)
        print(f"Found {total_alarms} alarms correlated with {degradations_with_alarms} degradations")
    
    def evaluate_with_llm(self, progress_callback=None):
        """
        Evaluate correlations using LLM.
        
        Args:
            progress_callback: Optional callback function(progress, total) for progress updates
        """
        if not self._correlations_computed:
            raise ValueError("Alarms not correlated. Call correlate_alarms() first.")
        
        if self.degradations_df is None or len(self.degradations_df) == 0:
            print("No degradations to evaluate with LLM.")
            return
        
        print("Evaluating correlations with LLM...")
        total = len(self.degradations_df)
        
        for idx, degradation in self.degradations_df.iterrows():
            if progress_callback:
                progress_callback(idx + 1, total)
            
            alarms = self.correlations.get(idx, pd.DataFrame())
            alarms_list = alarms.to_dict('records') if len(alarms) > 0 else []
            
            degradation_dict = degradation.to_dict()
            analysis = self.llm_agent.evaluate_correlation(degradation_dict, alarms_list)
            self.llm_analyses[idx] = analysis
        
        print("LLM evaluation complete")
    
    def process(
        self,
        kpi_path: str,
        alarms_path: str,
        use_llm: bool = True,
        progress_callback=None
    ) -> Dict:
        """
        Run complete processing pipeline.
        
        Args:
            kpi_path: Path to Excel file with KPI data
            alarms_path: Path to JSON file with alarm data
            use_llm: Whether to use LLM for correlation evaluation
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with all results
        """
        # Load data
        self.load_data(kpi_path, alarms_path)
        
        # Detect degradations
        self.detect_degradations()
        
        # Correlate alarms
        self.correlate_alarms()
        
        # Evaluate with LLM
        if use_llm:
            self.evaluate_with_llm(progress_callback)
        
        return {
            'kpi_data': self.kpi_df,
            'alarms_data': self.alarms_df,
            'degradations': self.degradations_df,
            'correlations': self.correlations,
            'llm_analyses': self.llm_analyses if use_llm else {}
        }
    
    def get_results_summary(self) -> Dict:
        """
        Get summary statistics of processing results.
        
        Returns:
            Dictionary with summary statistics
        """
        if self.degradations_df is None:
            return {}
        
        total_degradations = len(self.degradations_df)
        affected_nodes = self.degradations_df['node'].nunique()
        
        total_alarms = sum(len(df) for df in self.correlations.values())
        degradations_with_alarms = sum(1 for df in self.correlations.values() if len(df) > 0)
        degradations_without_alarms = total_degradations - degradations_with_alarms
        
        # LLM analysis summary
        llm_summary = {}
        if self.llm_analyses:
            verdicts = [analysis.get('overall_verdict', 'unknown') 
                       for analysis in self.llm_analyses.values()]
            llm_summary = {
                'causal': verdicts.count('causal'),
                'possible': verdicts.count('possible'),
                'coincidental': verdicts.count('coincidental'),
                'no_correlation': verdicts.count('no_correlation')
            }
        
        return {
            'total_degradations': total_degradations,
            'affected_nodes': affected_nodes,
            'total_correlated_alarms': total_alarms,
            'degradations_with_alarms': degradations_with_alarms,
            'degradations_without_alarms': degradations_without_alarms,
            'llm_verdicts': llm_summary
        }


def process_degradations(
    kpi_path: str,
    alarms_path: str,
    percentile: float = 10,
    time_before: int = 30,
    time_after: int = 30,
    use_llm: bool = True,
    llm_model: str = "gpt-4o-mini",
    llm_api_key: Optional[str] = None
) -> Dict:
    """
    Convenience function to process degradations.
    
    Args:
        kpi_path: Path to Excel file with KPI data
        alarms_path: Path to JSON file with alarm data
        percentile: Percentile threshold for degradation detection
        time_before: Minutes before degradation to search
        time_after: Minutes after degradation to search
        use_llm: Whether to use LLM evaluation
        llm_model: OpenAI model to use
        llm_api_key: OpenAI API key (if None, loads from env)
        
    Returns:
        Dictionary with all results
    """
    pipeline = ProcessingPipeline(
        percentile=percentile,
        time_before_min=time_before,
        time_after_min=time_after,
        llm_model=llm_model,
        llm_api_key=llm_api_key
    )
    
    return pipeline.process(kpi_path, alarms_path, use_llm=use_llm)
