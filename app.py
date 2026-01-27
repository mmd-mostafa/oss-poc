"""
Streamlit UI for RRC SR Degradation Detection and Alarm Correlation System.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from src.pipeline import ProcessingPipeline

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
    
    # Display results
    if st.session_state.results:
        results = st.session_state.results
        pipeline = st.session_state.pipeline
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Overview",
            "🔍 Degradation Details",
            "🏢 Node Analysis",
            "🚨 Alarms Summary"
        ])
        
        with tab1:
            show_overview(results, pipeline)
        
        with tab2:
            show_degradation_details(results, pipeline)
        
        with tab3:
            show_node_analysis(results, pipeline)
        
        with tab4:
            show_alarms_summary(results, pipeline)
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
    
    # Correlated alarms
    st.subheader("Correlated Alarms")
    alarms_df = correlations.get(actual_idx, pd.DataFrame())
    
    if len(alarms_df) == 0:
        st.info("No alarms found in the time window for this degradation.")
    else:
        st.write(f"Found {len(alarms_df)} alarm(s) in the time window:")
        
        display_alarms = alarms_df[[
            'alarm_id', 'timestamp', 'temporal_relationship', 'perceived_severity',
            'alarm_type', 'specific_problem', 'probable_cause'
        ]].copy()
        display_alarms['timestamp'] = display_alarms['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
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
        
        # Alarm analysis
        if analysis.get('alarm_analysis'):
            st.write("**Per-Alarm Analysis:**")
            for alarm_analysis in analysis['alarm_analysis']:
                with st.expander(f"Alarm {alarm_analysis.get('alarm_id', 'Unknown')} - Relevance: {alarm_analysis.get('relevance_score', 0):.1%}"):
                    st.write(f"**Is Causal:** {alarm_analysis.get('is_causal', False)}")
                    st.write(f"**Reasoning:** {alarm_analysis.get('reasoning', 'N/A')}")
        
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
    
    # Alarms table
    st.subheader("All Correlated Alarms")
    display_df = correlated_alarms_df[[
        'alarm_id', 'node', 'timestamp', 'temporal_relationship',
        'perceived_severity', 'alarm_type', 'specific_problem'
    ]].copy()
    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
    st.dataframe(display_df, use_container_width=True, height=400)


if __name__ == "__main__":
    main()
