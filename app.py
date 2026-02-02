"""
Streamlit UI for RRC SR Degradation Detection and Alarm Correlation System.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import numpy as np
import base64
from src.pipeline import ProcessingPipeline
from src.data_loader import load_kpi_data, load_alarms_data


def _format_status_timeline_short(timeline) -> str:
    """Format status_timeline list as compact string for display (e.g. '14:18:14 CRITICAL; 14:18:15 CLEARED')."""
    if not timeline or not isinstance(timeline, list):
        return "-"
    parts = []
    for ev in timeline:
        ts = ev.get("timestamp", "") or ""
        if "T" in str(ts):
            ts = str(ts).split("T")[-1][:8]
        elif len(str(ts)) > 8:
            ts = str(ts)[:8]
        sev = ev.get("perceived_severity", "") or ""
        parts.append(f"{ts} {sev}".strip())
    return "; ".join(parts) if parts else "-"


# Page configuration
st.set_page_config(
    page_title="RRC SR Degradation Analysis",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'pipeline' not in st.session_state:
    st.session_state.pipeline = None


def main():
    st.title("📊 RRC SR Degradation Detection and Alarm Correlation")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        # Logo at the top, centered
        logo_path = "assets/Qeema_logo.png"
        if os.path.exists(logo_path):
            # Use HTML/CSS for perfect centering
            with open(logo_path, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode()
            st.markdown(
                f'<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 10px;">'
                f'<img src="data:image/png;base64,{img_base64}" style="max-width: 40px; height: auto;">'
                '</div>',
                unsafe_allow_html=True
            )
            # All rights reserved text with transparency
            st.markdown(
                '<p style="text-align: center; color: rgba(128, 128, 128, 0.6); font-size: 0.8em; margin-top: -10px;">© Qeema. All rights reserved.</p>',
                unsafe_allow_html=True
            )
        st.markdown("---")
        
        st.header("Configuration")
        
        # File inputs
        st.subheader("Data Files")
        kpi_file = st.file_uploader(
            "Upload KPI Excel File",
            type=['xlsx', 'xls'],
            help="Excel file containing RRC SR KPI data with node, timestamp, and RRC SR columns"
        )
        
        alarms_file = st.file_uploader(
            "Upload Alarms JSON File",
            type=['json'],
            help="JSON file containing alarm data (one JSON object per line)"
        )
        
        # Use default files if available
        use_defaults = st.checkbox("Use default data files", value=True)
        
        if use_defaults:
            default_kpi_path = "data/Fake data.xlsx"
            default_alarms_path = "data/Fake alarms.json"
            if os.path.exists(default_kpi_path) and os.path.exists(default_alarms_path):
                kpi_path = default_kpi_path
                alarms_path = default_alarms_path
            else:
                st.warning("Default files not found. Please upload files.")
                kpi_path = None
                alarms_path = None
        else:
            if kpi_file:
                # Save uploaded file temporarily
                kpi_path = f"/tmp/{kpi_file.name}"
                with open(kpi_path, "wb") as f:
                    f.write(kpi_file.getbuffer())
            else:
                kpi_path = None
            
            if alarms_file:
                alarms_path = f"/tmp/{alarms_file.name}"
                with open(alarms_path, "wb") as f:
                    f.write(alarms_file.getbuffer())
            else:
                alarms_path = None
        
        st.markdown("---")
        
        # Processing parameters
        st.subheader("Processing Parameters")
        percentile = st.slider(
            "Percentile Threshold",
            min_value=5,
            max_value=25,
            value=10,
            help="Readings below this percentile are considered degraded"
        )
        
        time_before = st.number_input(
            "Time Before (minutes)",
            min_value=0,
            max_value=120,
            value=30,
            help="Minutes before degradation start to search for alarms"
        )
        
        time_after = st.number_input(
            "Time After (minutes)",
            min_value=0,
            max_value=120,
            value=30,
            help="Minutes after degradation end to search for alarms"
        )
        
        use_llm = st.checkbox(
            "Use LLM Analysis",
            value=True,
            help="Enable AI-powered correlation analysis (requires OpenAI API key in .env)"
        )
        
        llm_model = st.selectbox(
            "LLM Model",
            ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            index=0,
            help="OpenAI model to use for analysis"
        )
        
        st.markdown("---")
        st.info("💡 OpenAI API key should be set in `.env` file as `OPENAI_API_KEY`")
        
        # Process button
        process_button = st.button("🚀 Process Data", type="primary", use_container_width=True)
    
    # Main content area
    if process_button:
        if not kpi_path or not alarms_path:
            st.error("Please provide both KPI and Alarms data files.")
            return
        
        if use_llm and not os.getenv('OPENAI_API_KEY'):
            st.error("OpenAI API key not found. Please set OPENAI_API_KEY in .env file.")
            return
        
        # Initialize pipeline
        with st.spinner("Processing data..."):
            try:
                pipeline = ProcessingPipeline(
                    percentile=percentile,
                    time_before_min=time_before,
                    time_after_min=time_after,
                    llm_model=llm_model
                )
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def progress_callback(current, total):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(f"Processing degradation {current}/{total}...")
                
                # Process data
                results = pipeline.process(
                    kpi_path,
                    alarms_path,
                    use_llm=use_llm,
                    progress_callback=progress_callback if use_llm else None
                )
                
                # Debug: Show what was detected
                degradations_count = len(results.get('degradations', pd.DataFrame()))
                st.info(f"🔍 Debug: {degradations_count} degradations detected")
                
                st.session_state.results = results
                st.session_state.pipeline = pipeline
                
                progress_bar.empty()
                status_text.empty()
                st.success("✅ Processing complete!")
                
            except Exception as e:
                st.error(f"Error during processing: {str(e)}")
                st.exception(e)
                return
    
    # Get file paths for EDA (works even without processing)
    # Use the same paths determined above
    kpi_path_for_eda = kpi_path
    alarms_path_for_eda = alarms_path
    
    # Display results
    if st.session_state.results:
        results = st.session_state.results
        pipeline = st.session_state.pipeline
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Overview",
            "📊 EDA",
            "🔍 Degradation Details",
            "🏢 Node Analysis",
            "🚨 Alarms Summary"
        ])
        
        with tab1:
            show_overview(results, pipeline)
        
        with tab2:
            show_eda_page(results, pipeline, kpi_path_for_eda, alarms_path_for_eda)
        
        with tab3:
            show_degradation_details(results, pipeline)
        
        with tab4:
            show_node_analysis(results, pipeline)
        
        with tab5:
            show_alarms_summary(results, pipeline)
    else:
        # Show EDA tab even if data hasn't been processed
        if kpi_path_for_eda and alarms_path_for_eda:
            tab1, tab2 = st.tabs([
                "📊 EDA",
                "ℹ️ Info"
            ])
            
            with tab1:
                show_eda_page(None, None, kpi_path_for_eda, alarms_path_for_eda)
            
            with tab2:
                st.info("👈 Configure parameters and click 'Process Data' to begin analysis.")
        else:
            st.info("👈 Configure parameters and click 'Process Data' to begin analysis.")


def show_overview(results: dict, pipeline: ProcessingPipeline):
    """Display overview tab."""
    st.header("Degradations Overview")
    
    degradations_df = results.get('degradations', pd.DataFrame())
    
    # Handle case where degradations_df might be None or empty
    if degradations_df is None or (isinstance(degradations_df, pd.DataFrame) and len(degradations_df) == 0):
        st.warning("No degradations detected.")
        st.info("💡 Try adjusting the percentile threshold (lower values = more sensitive detection)")
        return
    
    # Summary statistics
    summary = pipeline.get_results_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Degradations", summary['total_degradations'])
    with col2:
        st.metric("Affected Nodes", summary['affected_nodes'])
    with col3:
        st.metric("Correlated Alarms", summary['total_correlated_alarms'])
    with col4:
        st.metric("Degradations with Alarms", summary['degradations_with_alarms'])
    
    if results.get('llm_analyses'):
        st.subheader("LLM Analysis Verdicts")
        verdicts = summary.get('llm_verdicts', {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Causal", verdicts.get('causal', 0))
        with col2:
            st.metric("Possible", verdicts.get('possible', 0))
        with col3:
            st.metric("Coincidental", verdicts.get('coincidental', 0))
        with col4:
            st.metric("No Correlation", verdicts.get('no_correlation', 0))
    
    st.markdown("---")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        nodes = ['All'] + sorted(degradations_df['node'].unique().tolist())
        selected_node = st.selectbox("Filter by Node", nodes)
    with col2:
        severities = ['All'] + sorted(degradations_df['severity'].unique().tolist())
        selected_severity = st.selectbox("Filter by Severity", severities)
    
    # Filter data
    filtered_df = degradations_df.copy()
    if selected_node != 'All':
        filtered_df = filtered_df[filtered_df['node'] == selected_node]
    if selected_severity != 'All':
        filtered_df = filtered_df[filtered_df['severity'] == selected_severity]
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Degradations Over Time")
        if len(filtered_df) > 0:
            fig = px.scatter(
                filtered_df,
                x='start_timestamp',
                y='min_value',
                color='severity',
                size='duration_minutes',
                hover_data=['node', 'duration_minutes', 'deviation_percent'],
                title="Degradations Timeline"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to display with current filters.")
    
    with col2:
        st.subheader("Degradations per Node")
        if len(filtered_df) > 0:
            node_counts = filtered_df['node'].value_counts().head(10)
            fig = px.bar(
                x=node_counts.index,
                y=node_counts.values,
                labels={'x': 'Node', 'y': 'Count'},
                title="Top 10 Nodes by Degradation Count"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to display with current filters.")
    
    # Table
    st.subheader("Degradations Table")
    display_df = filtered_df[[
        'node', 'start_timestamp', 'end_timestamp', 'min_value',
        'baseline_value', 'duration_minutes', 'severity', 'deviation_percent'
    ]].copy()
    display_df['start_timestamp'] = display_df['start_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df['end_timestamp'] = display_df['end_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
    st.dataframe(display_df, use_container_width=True, height=400)


def show_degradation_details(results: dict, pipeline: ProcessingPipeline):
    """Display degradation details tab."""
    st.header("Degradation Details")
    
    degradations_df = results['degradations']
    correlations = results['correlations']
    llm_analyses = results.get('llm_analyses', {})
    
    if len(degradations_df) == 0:
        st.warning("No degradations detected.")
        return
    
    # Select degradation
    degradation_options = []
    for idx, row in degradations_df.iterrows():
        label = f"{row['node']} - {row['start_timestamp'].strftime('%Y-%m-%d %H:%M:%S')} ({row['severity']})"
        degradation_options.append((idx, label))
    
    selected_idx = st.selectbox(
        "Select Degradation",
        range(len(degradation_options)),
        format_func=lambda x: degradation_options[x][1]
    )
    
    actual_idx = degradation_options[selected_idx][0]
    degradation = degradations_df.loc[actual_idx]
    
    st.markdown("---")
    
    # Degradation details
    st.subheader("Degradation Information")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Node", degradation['node'])
    with col2:
        st.metric("Severity", degradation['severity'])
    with col3:
        st.metric("Duration", f"{degradation['duration_minutes']:.1f} min")
    with col4:
        st.metric("Deviation", f"{degradation['deviation_percent']:.1f}%")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Start Time:**", degradation['start_timestamp'])
        st.write("**End Time:**", degradation['end_timestamp'])
    with col2:
        st.write("**Min RRC SR Value:**", f"{degradation['min_value']:.2f}%")
        st.write("**Baseline (Threshold):**", f"{degradation['baseline_value']:.2f}%")
    
    st.markdown("---")
    
    # Correlated alarms (consolidated by alarm_id; one row per unique alarm)
    st.subheader("Correlated Alarms")
    alarms_df = correlations.get(actual_idx, pd.DataFrame())
    
    if len(alarms_df) == 0:
        st.info("No alarms found in the time window for this degradation.")
    else:
        st.write(f"Found {len(alarms_df)} unique alarm(s) in the time window (consolidated by alarm ID):")
        
        display_cols = [
            'alarm_id', 'timestamp', 'temporal_relationship', 'perceived_severity',
            'alarm_type', 'specific_problem', 'probable_cause'
        ]
        display_alarms = alarms_df[[c for c in display_cols if c in alarms_df.columns]].copy()
        if 'timestamp' in display_alarms.columns:
            try:
                if pd.api.types.is_datetime64_any_dtype(display_alarms['timestamp']):
                    display_alarms['timestamp'] = display_alarms['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    display_alarms['timestamp'] = display_alarms['timestamp'].astype(str)
            except (TypeError, AttributeError):
                display_alarms['timestamp'] = display_alarms['timestamp'].astype(str)
        if 'status_timeline' in alarms_df.columns:
            display_alarms['Status Timeline'] = alarms_df['status_timeline'].map(_format_status_timeline_short)
        display_alarms.columns = [col.replace('_', ' ').title() for col in display_alarms.columns]
        st.dataframe(display_alarms, use_container_width=True)
    
    st.markdown("---")
    
    # LLM Analysis
    if actual_idx in llm_analyses:
        st.subheader("🤖 LLM Correlation Analysis")
        analysis = llm_analyses[actual_idx]
        
        verdict = analysis.get('overall_verdict', 'unknown')
        confidence = analysis.get('confidence_score', 0.0)
        
        col1, col2 = st.columns(2)
        with col1:
            verdict_color = {
                'causal': '🟢',
                'possible': '🟡',
                'coincidental': '🟠',
                'no_correlation': '🔴'
            }.get(verdict, '⚪')
            st.metric("Verdict", f"{verdict_color} {verdict.upper()}")
        with col2:
            st.metric("Confidence", f"{confidence:.1%}")
        
        # Top reasons
        if analysis.get('top_reasons'):
            st.write("**Top Reasons:**")
            for i, reason in enumerate(analysis['top_reasons'], 1):
                st.write(f"{i}. {reason}")
        
        # Root cause analysis (optional)
        if analysis.get('root_cause_analysis'):
            st.write("**Root Cause Analysis:**")
            st.info(analysis['root_cause_analysis'])
        
        # Alarm analysis
        if analysis.get('alarm_analysis'):
            st.write("**Per-Alarm Analysis:**")
            for alarm_analysis in analysis['alarm_analysis']:
                with st.expander(f"Alarm {alarm_analysis.get('alarm_id', 'Unknown')} - Relevance: {alarm_analysis.get('relevance_score', 0):.1%}"):
                    st.write(f"**Is Causal:** {alarm_analysis.get('is_causal', False)}")
                    st.write(f"**Reasoning:** {alarm_analysis.get('reasoning', 'N/A')}")
                    if alarm_analysis.get('lifespan_note'):
                        st.write(f"**Lifespan:** {alarm_analysis['lifespan_note']}")
                    steps = alarm_analysis.get('suggested_fix') or alarm_analysis.get('remediation_steps')
                    if steps and isinstance(steps, list):
                        st.write("**Suggested fix / Remediation:**")
                        for step in steps:
                            st.write(f"- {step}")
        
        # Recommended actions
        if analysis.get('recommended_actions'):
            st.write("**Recommended Actions:**")
            for i, action in enumerate(analysis['recommended_actions'], 1):
                st.write(f"{i}. {action}")
        
        # Analysis summary
        if analysis.get('analysis_summary'):
            st.write("**Detailed Analysis:**")
            st.info(analysis['analysis_summary'])
    else:
        st.info("LLM analysis not available for this degradation.")


def show_node_analysis(results: dict, pipeline: ProcessingPipeline):
    """Display node analysis tab."""
    st.header("Node Analysis")
    
    degradations_df = results['degradations']
    kpi_df = results['kpi_data']
    
    if len(degradations_df) == 0:
        st.warning("No degradations detected.")
        return
    
    # Select node
    nodes = sorted(degradations_df['node'].unique().tolist())
    selected_node = st.selectbox("Select Node", nodes)
    
    st.markdown("---")
    
    # Node degradations
    node_degradations = degradations_df[degradations_df['node'] == selected_node]
    st.subheader(f"Degradations for {selected_node}")
    st.write(f"Total degradations: {len(node_degradations)}")
    
    if len(node_degradations) > 0:
        # Timeline
        fig = go.Figure()
        
        for idx, deg in node_degradations.iterrows():
            fig.add_trace(go.Scatter(
                x=[deg['start_timestamp'], deg['end_timestamp']],
                y=[deg['min_value'], deg['min_value']],
                mode='lines+markers',
                name=f"Degradation {idx}",
                line=dict(width=3),
                marker=dict(size=10)
            ))
        
        # Add KPI data
        node_kpi = kpi_df[kpi_df['node'] == selected_node]
        if len(node_kpi) > 0:
            fig.add_trace(go.Scatter(
                x=node_kpi['timestamp'],
                y=node_kpi['rrc_sr'],
                mode='lines',
                name='RRC SR Values',
                line=dict(color='lightblue', width=1),
                opacity=0.5
            ))
        
        fig.update_layout(
            title=f"Timeline for {selected_node}",
            xaxis_title="Time",
            yaxis_title="RRC SR (%)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Degradations table
        display_df = node_degradations[[
            'start_timestamp', 'end_timestamp', 'min_value',
            'duration_minutes', 'severity', 'deviation_percent'
        ]].copy()
        display_df['start_timestamp'] = display_df['start_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df['end_timestamp'] = display_df['end_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info(f"No degradations found for node {selected_node}")


def show_alarms_summary(results: dict, pipeline: ProcessingPipeline):
    """Display alarms summary tab."""
    st.header("Alarms Summary")
    
    correlations = results['correlations']
    alarms_df = results['alarms_data']
    
    # Collect all correlated alarms
    all_correlated_alarms = []
    for idx, alarms in correlations.items():
        if len(alarms) > 0:
            all_correlated_alarms.append(alarms)
    
    if not all_correlated_alarms:
        st.info("No alarms found in degradation windows.")
        return
    
    correlated_alarms_df = pd.concat(all_correlated_alarms).drop_duplicates(subset=['alarm_id'])
    
    st.subheader("Summary Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Correlated Alarms", len(correlated_alarms_df))
    with col2:
        st.metric("Unique Alarm Types", correlated_alarms_df['alarm_type'].nunique())
    with col3:
        st.metric("Unique Severities", correlated_alarms_df['perceived_severity'].nunique())
    
    st.markdown("---")
    
    # Alarm frequency
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Alarm Types Frequency")
        alarm_type_counts = correlated_alarms_df['alarm_type'].value_counts()
        fig = px.pie(
            values=alarm_type_counts.values,
            names=alarm_type_counts.index,
            title="Distribution of Alarm Types"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Severity Distribution")
        severity_counts = correlated_alarms_df['perceived_severity'].value_counts()
        fig = px.bar(
            x=severity_counts.index,
            y=severity_counts.values,
            labels={'x': 'Severity', 'y': 'Count'},
            title="Alarm Severity Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Most common alarm types
    st.subheader("Most Correlated Alarm Types")
    alarm_type_counts = correlated_alarms_df['alarm_type'].value_counts().head(10)
    st.dataframe(
        pd.DataFrame({
            'Alarm Type': alarm_type_counts.index,
            'Count': alarm_type_counts.values
        }),
        use_container_width=True
    )
    
    st.markdown("---")
    
    # Alarms table (consolidated by alarm_id)
    st.subheader("All Correlated Alarms")
    summary_cols = [
        'alarm_id', 'node', 'timestamp', 'temporal_relationship',
        'perceived_severity', 'alarm_type', 'specific_problem'
    ]
    display_df = correlated_alarms_df[[c for c in summary_cols if c in correlated_alarms_df.columns]].copy()
    if 'timestamp' in display_df.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(display_df['timestamp']):
                display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                display_df['timestamp'] = display_df['timestamp'].astype(str)
        except (TypeError, AttributeError):
            display_df['timestamp'] = display_df['timestamp'].astype(str)
    if 'status_timeline' in correlated_alarms_df.columns:
        display_df['Status Timeline'] = correlated_alarms_df['status_timeline'].map(_format_status_timeline_short)
    display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
    st.dataframe(display_df, use_container_width=True, height=400)


def load_data_for_eda(results: dict, kpi_path: str, alarms_path: str) -> tuple:
    """
    Load KPI and alarms data for EDA.
    
    Args:
        results: Results dict from processing (may be None)
        kpi_path: Path to KPI Excel file
        alarms_path: Path to alarms JSON file
        
    Returns:
        Tuple of (kpi_df, alarms_df)
    """
    if results and 'kpi_data' in results and 'alarms_data' in results:
        return results['kpi_data'], results['alarms_data']
    
    if not kpi_path or not alarms_path:
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        kpi_df = load_kpi_data(kpi_path)
        alarms_df = load_alarms_data(alarms_path)
        return kpi_df, alarms_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()


def filter_kpi_data(df: pd.DataFrame, selected_nodes: list, start_date: datetime, end_date: datetime, start_hour: int = None, end_hour: int = None) -> pd.DataFrame:
    """Apply filters to KPI DataFrame."""
    filtered = df.copy()
    
    if selected_nodes and 'All' not in selected_nodes:
        filtered = filtered[filtered['node'].isin(selected_nodes)]
    
    if start_date:
        filtered = filtered[filtered['timestamp'] >= start_date]
    
    if end_date:
        # Add one day to include the entire end date
        end_date_inclusive = end_date + pd.Timedelta(days=1)
        filtered = filtered[filtered['timestamp'] < end_date_inclusive]
    
    if start_hour is not None:
        filtered = filtered[filtered['timestamp'].dt.hour >= start_hour]
    
    if end_hour is not None:
        filtered = filtered[filtered['timestamp'].dt.hour <= end_hour]
    
    return filtered


def filter_alarms_data(df: pd.DataFrame, selected_nodes: list, start_date: datetime, end_date: datetime, 
                       selected_severities: list, selected_alarm_types: list, specific_problem_filter: str = None) -> pd.DataFrame:
    """Apply filters to alarms DataFrame."""
    filtered = df.copy()
    
    if selected_nodes and 'All' not in selected_nodes:
        # Convert node column to string for comparison
        filtered['node'] = filtered['node'].astype(str)
        filtered = filtered[filtered['node'].isin(selected_nodes)]
    
    if start_date:
        filtered = filtered[filtered['timestamp'] >= start_date]
    
    if end_date:
        end_date_inclusive = end_date + pd.Timedelta(days=1)
        filtered = filtered[filtered['timestamp'] < end_date_inclusive]
    
    if selected_severities and 'All' not in selected_severities:
        filtered = filtered[filtered['perceived_severity'].isin(selected_severities)]
    
    if selected_alarm_types and 'All' not in selected_alarm_types:
        filtered = filtered[filtered['alarm_type'].isin(selected_alarm_types)]
    
    if specific_problem_filter:
        filtered = filtered[filtered['specific_problem'].str.contains(specific_problem_filter, case=False, na=False)]
    
    return filtered


def calculate_kpi_statistics(df: pd.DataFrame) -> dict:
    """Calculate summary statistics for KPI data."""
    if len(df) == 0:
        return {}
    
    return {
        'total_readings': len(df),
        'unique_nodes': df['node'].nunique(),
        'date_range_start': df['timestamp'].min(),
        'date_range_end': df['timestamp'].max(),
        'mean_rrc_sr': df['rrc_sr'].mean(),
        'median_rrc_sr': df['rrc_sr'].median(),
        'min_rrc_sr': df['rrc_sr'].min(),
        'max_rrc_sr': df['rrc_sr'].max(),
        'std_rrc_sr': df['rrc_sr'].std(),
    }


def calculate_alarms_statistics(df: pd.DataFrame) -> dict:
    """Calculate summary statistics for alarms data."""
    if len(df) == 0:
        return {}
    
    stats = {
        'total_alarms': len(df),
        'unique_alarm_ids': df['alarm_id'].nunique(),
        'unique_nodes': df['node'].nunique(),
        'date_range_start': df['timestamp'].min(),
        'date_range_end': df['timestamp'].max(),
    }
    
    if 'perceived_severity' in df.columns:
        stats['severity_counts'] = df['perceived_severity'].value_counts().to_dict()
    
    if 'alarm_type' in df.columns:
        stats['alarm_type_counts'] = df['alarm_type'].value_counts().to_dict()
    
    return stats


def show_eda_page(results: dict, pipeline: ProcessingPipeline, kpi_path: str, alarms_path: str):
    """Display EDA page with KPI and Alarms sub-tabs."""
    st.header("Exploratory Data Analysis")
    
    # Load data
    kpi_df, alarms_df = load_data_for_eda(results, kpi_path, alarms_path)
    
    if len(kpi_df) == 0 and len(alarms_df) == 0:
        st.warning("No data available. Please ensure data files are loaded.")
        return
    
    # Create sub-tabs
    eda_tab1, eda_tab2 = st.tabs(["📈 KPI Data", "🚨 Alarms Data"])
    
    with eda_tab1:
        show_kpi_eda(kpi_df)
    
    with eda_tab2:
        show_alarms_eda(alarms_df)


def show_kpi_eda(kpi_df: pd.DataFrame):
    """Display KPI data EDA sub-tab."""
    st.subheader("KPI Data Exploration")
    
    if len(kpi_df) == 0:
        st.warning("No KPI data available.")
        return
    
    # Filters section
    st.markdown("### Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        all_nodes = sorted(kpi_df['node'].unique().tolist())
        selected_nodes = st.multiselect(
            "Select Nodes",
            options=['All'] + all_nodes,
            default=['All'],
            help="Select nodes to filter. 'All' shows all nodes."
        )
    
    with col2:
        min_date = kpi_df['timestamp'].min().date()
        max_date = kpi_df['timestamp'].max().date()
        start_date = st.date_input(
            "Start Date",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )
    
    with col3:
        end_date = st.date_input(
            "End Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )
    
    with col4:
        use_hour_filter = st.checkbox("Filter by Hour Range")
        if use_hour_filter:
            start_hour = st.slider("Start Hour", 0, 23, 0)
            end_hour = st.slider("End Hour", 0, 23, 23)
        else:
            start_hour = None
            end_hour = None
    
    # Apply filters
    filtered_kpi = filter_kpi_data(
        kpi_df,
        selected_nodes,
        pd.Timestamp(start_date),
        pd.Timestamp(end_date),
        start_hour,
        end_hour
    )
    
    if len(filtered_kpi) == 0:
        st.warning("No data matches the selected filters.")
        return
    
    st.markdown("---")
    
    # Statistics section
    st.markdown("### Summary Statistics")
    stats = calculate_kpi_statistics(filtered_kpi)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Readings", stats.get('total_readings', 0))
    with col2:
        st.metric("Unique Nodes", stats.get('unique_nodes', 0))
    with col3:
        st.metric("Mean RRC SR", f"{stats.get('mean_rrc_sr', 0):.2f}%")
    with col4:
        st.metric("Median RRC SR", f"{stats.get('median_rrc_sr', 0):.2f}%")
    with col5:
        st.metric("Std Dev", f"{stats.get('std_rrc_sr', 0):.2f}%")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Min RRC SR", f"{stats.get('min_rrc_sr', 0):.2f}%")
    with col2:
        st.metric("Max RRC SR", f"{stats.get('max_rrc_sr', 0):.2f}%")
    with col3:
        date_start = stats.get('date_range_start', None)
        date_end = stats.get('date_range_end', None)
        if date_start and date_end:
            date_range_str = f"{date_start.strftime('%Y-%m-%d')} to {date_end.strftime('%Y-%m-%d')}"
        else:
            date_range_str = "N/A"
        st.metric("Date Range", date_range_str)
    
    st.markdown("---")
    
    # Visualizations
    st.markdown("### Visualizations")
    
    # Time series plot
    st.markdown("#### Time Series Plot")
    plot_nodes = selected_nodes if selected_nodes and 'All' not in selected_nodes else all_nodes[:10]  # Limit to 10 nodes for performance
    
    if len(plot_nodes) > 0:
        fig = px.line(
            filtered_kpi[filtered_kpi['node'].isin(plot_nodes)],
            x='timestamp',
            y='rrc_sr',
            color='node',
            title="RRC SR Over Time",
            labels={'timestamp': 'Time', 'rrc_sr': 'RRC SR (%)'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Distribution and comparison plots
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Distribution")
        fig = px.histogram(
            filtered_kpi,
            x='rrc_sr',
            nbins=50,
            title="RRC SR Distribution",
            labels={'rrc_sr': 'RRC SR (%)', 'count': 'Frequency'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Node Comparison (Box Plot)")
        if len(plot_nodes) > 0:
            fig = px.box(
                filtered_kpi[filtered_kpi['node'].isin(plot_nodes)],
                x='node',
                y='rrc_sr',
                title="RRC SR by Node",
                labels={'rrc_sr': 'RRC SR (%)', 'node': 'Node'}
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    # Node statistics table
    st.markdown("#### Statistical Summary by Node")
    node_stats_list = []
    for node in sorted(filtered_kpi['node'].unique()):
        node_data = filtered_kpi[filtered_kpi['node'] == node]['rrc_sr']
        node_stats_list.append({
            'Node': node,
            'Count': len(node_data),
            'Mean': node_data.mean(),
            'Median': node_data.median(),
            'Std Dev': node_data.std(),
            'Min': node_data.min(),
            'Max': node_data.max(),
            'P5': np.percentile(node_data, 5),
            'P10': np.percentile(node_data, 10),
            'P25': np.percentile(node_data, 25),
            'P75': np.percentile(node_data, 75),
            'P90': np.percentile(node_data, 90),
            'P95': np.percentile(node_data, 95),
        })
    
    node_stats_df = pd.DataFrame(node_stats_list)
    st.dataframe(node_stats_df, use_container_width=True, height=400)
    
    # Temporal patterns
    st.markdown("#### Temporal Patterns")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Hourly Average RRC SR")
        filtered_kpi['hour'] = filtered_kpi['timestamp'].dt.hour
        hourly_avg = filtered_kpi.groupby('hour')['rrc_sr'].mean().reset_index()
        fig = px.bar(
            hourly_avg,
            x='hour',
            y='rrc_sr',
            title="Average RRC SR by Hour of Day",
            labels={'hour': 'Hour', 'rrc_sr': 'Average RRC SR (%)'}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("##### Daily Trends")
        filtered_kpi['date'] = filtered_kpi['timestamp'].dt.date
        daily_avg = filtered_kpi.groupby('date')['rrc_sr'].mean().reset_index()
        daily_avg['date'] = pd.to_datetime(daily_avg['date'])
        fig = px.line(
            daily_avg,
            x='date',
            y='rrc_sr',
            title="Daily Average RRC SR",
            labels={'date': 'Date', 'rrc_sr': 'Average RRC SR (%)'}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)


def show_alarms_eda(alarms_df: pd.DataFrame):
    """Display alarms data EDA sub-tab."""
    st.subheader("Alarms Data Exploration")
    
    if len(alarms_df) == 0:
        st.warning("No alarms data available.")
        return
    
    # Filters section
    st.markdown("### Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        # Filter out NaN nodes and convert to string
        valid_nodes = alarms_df['node'].dropna().astype(str).unique()
        all_nodes = sorted([n for n in valid_nodes if n and n != 'nan'])
        selected_nodes = st.multiselect(
            "Select Nodes",
            options=['All'] + all_nodes,
            default=['All'],
            help="Select nodes to filter. 'All' shows all nodes."
        )
    
    with col2:
        min_date = alarms_df['timestamp'].min().date()
        max_date = alarms_df['timestamp'].max().date()
        start_date = st.date_input(
            "Start Date",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            key="alarms_start_date"
        )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        end_date = st.date_input(
            "End Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            key="alarms_end_date"
        )
    
    with col2:
        all_severities = sorted([s for s in alarms_df['perceived_severity'].dropna().unique() if pd.notna(s)])
        selected_severities = st.multiselect(
            "Select Severities",
            options=['All'] + all_severities,
            default=['All'],
            help="Filter by alarm severity"
        )
    
    with col3:
        all_alarm_types = sorted([t for t in alarms_df['alarm_type'].dropna().unique() if pd.notna(t)])
        selected_alarm_types = st.multiselect(
            "Select Alarm Types",
            options=['All'] + all_alarm_types,
            default=['All'],
            help="Filter by alarm type"
        )
    
    specific_problem_filter = st.text_input(
        "Filter by Specific Problem (text search)",
        value="",
        help="Enter text to search in specific_problem field"
    )
    
    # Apply filters
    filtered_alarms = filter_alarms_data(
        alarms_df,
        selected_nodes,
        pd.Timestamp(start_date),
        pd.Timestamp(end_date),
        selected_severities,
        selected_alarm_types,
        specific_problem_filter if specific_problem_filter else None
    )
    
    if len(filtered_alarms) == 0:
        st.warning("No alarms match the selected filters.")
        return
    
    st.markdown("---")
    
    # Statistics section
    st.markdown("### Summary Statistics")
    stats = calculate_alarms_statistics(filtered_alarms)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Alarms", stats.get('total_alarms', 0))
    with col2:
        st.metric("Unique Alarm IDs", stats.get('unique_alarm_ids', 0))
    with col3:
        st.metric("Unique Nodes", stats.get('unique_nodes', 0))
    with col4:
        date_start = stats.get('date_range_start', None)
        date_end = stats.get('date_range_end', None)
        if date_start and date_end:
            date_range_str = f"{date_start.strftime('%Y-%m-%d')} to {date_end.strftime('%Y-%m-%d')}"
        else:
            date_range_str = "N/A"
        st.metric("Date Range", date_range_str)
    
    st.markdown("---")
    
    # Visualizations
    st.markdown("### Visualizations")
    
    # Alarm timeline
    st.markdown("#### Alarm Timeline")
    plot_nodes = selected_nodes if selected_nodes and 'All' not in selected_nodes else all_nodes[:10]
    
    if len(plot_nodes) > 0:
        timeline_df = filtered_alarms[filtered_alarms['node'].astype(str).isin(plot_nodes)]
        if len(timeline_df) > 0:
            fig = px.scatter(
                timeline_df,
                x='timestamp',
                y='node',
                color='perceived_severity',
                size_max=10,
                title="Alarms Over Time",
                labels={'timestamp': 'Time', 'node': 'Node'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No alarms to display in timeline.")
    else:
        st.info("Please select nodes to view timeline.")
    
    # Distribution charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Severity Distribution")
        if 'perceived_severity' in filtered_alarms.columns:
            severity_counts = filtered_alarms['perceived_severity'].value_counts()
            fig = px.pie(
                values=severity_counts.values,
                names=severity_counts.index,
                title="Alarm Severity Distribution"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Alarm Type Distribution")
        if 'alarm_type' in filtered_alarms.columns:
            alarm_type_counts = filtered_alarms['alarm_type'].value_counts().head(10)
            fig = px.bar(
                x=alarm_type_counts.index,
                y=alarm_type_counts.values,
                labels={'x': 'Alarm Type', 'y': 'Count'},
                title="Top 10 Alarm Types"
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    # Node analysis
    st.markdown("#### Node Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Alarms per Node")
        node_counts = filtered_alarms['node'].value_counts().head(20)
        fig = px.bar(
            x=node_counts.index,
            y=node_counts.values,
            labels={'x': 'Node', 'y': 'Alarm Count'},
            title="Top 20 Nodes by Alarm Count"
        )
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("##### Severity by Node")
        if len(plot_nodes) > 0:
            plot_df = filtered_alarms[filtered_alarms['node'].astype(str).isin(plot_nodes)]
            if len(plot_df) > 0:
                severity_by_node = plot_df.groupby(['node', 'perceived_severity']).size().reset_index(name='count')
                fig = px.bar(
                    severity_by_node,
                    x='node',
                    y='count',
                    color='perceived_severity',
                    title="Alarm Severity by Node",
                    labels={'node': 'Node', 'count': 'Count'}
                )
                fig.update_layout(height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data to display.")
        else:
            st.info("Please select nodes to view chart.")
    
    # Temporal patterns
    st.markdown("#### Temporal Patterns")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Hourly Alarm Frequency")
        filtered_alarms['hour'] = filtered_alarms['timestamp'].dt.hour
        hourly_counts = filtered_alarms.groupby('hour').size().reset_index(name='count')
        fig = px.bar(
            hourly_counts,
            x='hour',
            y='count',
            title="Alarms by Hour of Day",
            labels={'hour': 'Hour', 'count': 'Alarm Count'}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("##### Daily Alarm Trends")
        filtered_alarms['date'] = filtered_alarms['timestamp'].dt.date
        daily_counts = filtered_alarms.groupby('date').size().reset_index(name='count')
        daily_counts['date'] = pd.to_datetime(daily_counts['date'])
        fig = px.line(
            daily_counts,
            x='date',
            y='count',
            title="Daily Alarm Count",
            labels={'date': 'Date', 'count': 'Alarm Count'}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Top problems
    st.markdown("#### Top Problems")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Most Frequent Specific Problems")
        if 'specific_problem' in filtered_alarms.columns:
            top_problems = filtered_alarms['specific_problem'].value_counts().head(10)
            top_problems_df = pd.DataFrame({
                'Specific Problem': top_problems.index,
                'Count': top_problems.values
            })
            st.dataframe(top_problems_df, use_container_width=True, height=300)
    
    with col2:
        st.markdown("##### Most Frequent Probable Causes")
        if 'probable_cause' in filtered_alarms.columns:
            top_causes = filtered_alarms['probable_cause'].value_counts().head(10)
            top_causes_df = pd.DataFrame({
                'Probable Cause': top_causes.index,
                'Count': top_causes.values
            })
            st.dataframe(top_causes_df, use_container_width=True, height=300)
    
    # Alarms table
    st.markdown("#### Alarms Table")
    display_cols = ['alarm_id', 'node', 'timestamp', 'perceived_severity', 'alarm_type', 'specific_problem']
    available_cols = [col for col in display_cols if col in filtered_alarms.columns]
    
    display_df = filtered_alarms[available_cols].copy()
    if 'node' in display_df.columns:
        display_df['node'] = display_df['node'].astype(str).replace('nan', 'N/A')
    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
    st.dataframe(display_df, use_container_width=True, height=400)


if __name__ == "__main__":
    main()
