# RRC SR Degradation Detection and Alarm Correlation System - Comprehensive Documentation

## Table of Contents

1. [Overview](#overview)
2. [Use Case and Goals](#use-case-and-goals)
3. [System Architecture](#system-architecture)
4. [Application Components](#application-components)
5. [Degradation Detection Algorithm](#degradation-detection-algorithm)
6. [Alarm Correlation](#alarm-correlation)
7. [LLM-Based Analysis](#llm-based-analysis)
8. [User Interface Components](#user-interface-components)
9. [Configuration Parameters](#configuration-parameters)
10. [Data Formats](#data-formats)
11. [Workflow](#workflow)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The RRC SR (Radio Resource Control Success Rate) Degradation Detection and Alarm Correlation System is an AI-powered solution designed for telecommunications network operators to automatically detect KPI degradations, correlate them with Fault Management (FM) alarms, and provide intelligent analysis with remediation recommendations.

This system helps Network Operations Centers (NOCs) and network engineers quickly identify service-affecting issues, understand root causes, and take appropriate remediation actions.

---

## Use Case and Goals

### Use Case

Telecommunications networks generate vast amounts of Performance Management (PM) and Fault Management (FM) data. When network performance degrades, operators need to:

1. **Detect degradations** in critical KPIs (like RRC Success Rate) quickly
2. **Correlate degradations** with relevant alarms to identify root causes
3. **Determine causality** - distinguish between alarms that caused the degradation versus coincidental alarms
4. **Get actionable recommendations** for remediation

Manual analysis of this data is time-consuming and error-prone. This system automates the entire process.

### Goals

1. **Automated Degradation Detection**: Continuously monitor RRC SR KPI and automatically detect degradations using statistical methods
2. **Intelligent Alarm Correlation**: Find and correlate FM alarms within configurable time windows around degradation periods
3. **Causal Analysis**: Use AI to evaluate whether alarms are causal, possible, coincidental, or unrelated to degradations
4. **Actionable Insights**: Provide specific remediation recommendations based on analysis
5. **Comprehensive Visualization**: Present results in an intuitive, interactive web interface

---

## System Architecture

The system consists of several interconnected components:

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web UI (app.py)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐  │
│  │Overview  │  │   EDA    │  │  Threshold  │  │Degradation│  │  Node    │  │
│  │  Tab     │  │   Tab    │  │  Settings   │  │  Details  │  │ Analysis │  │
│  └──────────┘  └──────────┘  └──────────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Processing Pipeline (pipeline.py)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Data Loader   │  │ Degradation  │  │   Alarm      │    │
│  │              │  │  Detector    │  │  Correlator   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                            │                                │
│                            ▼                                │
│              ┌──────────────────────────┐                  │
│              │      LLM Agent           │                  │
│              │   (OpenAI Integration)   │                  │
│              └──────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources                              │
│  ┌──────────────┐              ┌──────────────┐            │
│  │  KPI Excel    │              │  Alarms JSON │            │
│  │     File     │              │     File     │            │
│  └──────────────┘              └──────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## Application Components

### 1. Data Loader (`src/data_loader.py`)

**Purpose**: Loads and standardizes KPI and alarm data from various file formats.

#### KPI Data Loading

- **Input**: Excel file with columns for node, date/hour (or timestamp), and RRC SR
- **Process**:
  1. Automatically detects column names (case-insensitive)
  2. Handles multiple date formats (separate date/hour columns or combined timestamp)
  3. Converts hour format (handles 1-24 hour format, converting 24 to 0 of next day)
  4. Standardizes to DataFrame with columns: `node`, `timestamp`, `rrc_sr`
  5. Removes rows with missing critical data
  6. Sorts by node and timestamp

#### Alarm Data Loading

- **Input**: JSON file (array format or line-delimited JSON)
- **Process**:
  1. Parses JSON (supports both array and line-delimited formats)
  2. Extracts node identifiers from:
     - `managedObjectClass` (e.g., "PLMN-PLMN/MRBTS-685256/...")
     - `nbiOptionalInformation` (e.g., "NEName=EMH229|siteObjName=...")
  3. Extracts **canonical node ID** (`node_id`) from `managedObjectClass` as the numeric part of `MRBTS-X` or `BSC-X` (e.g. `1900` from `MRBTS-1900`). Used for same-node correlation with KPI data.
  4. Parses timestamps from `alarmRaisedTime`, `alarmClearedTime`, or `nbiEventTime`
  5. Standardizes to DataFrame with columns: `alarm_id`, `node`, `node_id`, `timestamp`, `perceived_severity`, `alarm_type`, `specific_problem`, `probable_cause`, etc.
  6. Removes rows with missing timestamps
  7. Sorts by timestamp

### 2. Degradation Detector (`src/degradation_detector.py`)

**Purpose**: Detects degradation periods in RRC SR KPI data using **median-based plus static thresholds**. A reading is degraded only if **both** conditions are met: RRC SR is below (median × percentage) and below the static threshold.

#### Key Methods

- **`get_node_medians(df)`**: Computes the median RRC SR for each node
- **`detect_degradations(df, node_config, ...)`**: Main method; accepts per-node config (`median_percentage`, `static_threshold`) and identifies periods where readings are below both the dynamic threshold (median × percentage) and the static threshold
- **`get_node_statistics(df)`**: Computes statistical summaries per node

### 3. Alarm Correlator (`src/alarm_correlator.py`)

**Purpose**: Correlates alarms with degradation periods based on same-node matching and time windows, then consolidates by alarm ID so each unique alarm is represented once with its full status lifecycle.

#### Key Features

- **Node Matching**: Same-node matching via canonical node ID from `managedObjectClass` (numeric part of MRBTS-X or BSC-X). Only alarms on the same node as the KPI degradation are correlated.
- **Time Window**: Configurable time window (before and after degradation period)
- **Temporal Relationships**: Classifies alarms as BEFORE, DURING, or AFTER degradation (based on the earliest event in the window for each alarm)
- **Consolidation by Alarm ID**: Within each degradation's time window, alarm events are grouped by `alarm_id`. Each alarm may have multiple status events (raised, severity changes, cleared). The correlator outputs **one row per unique alarm ID** with a **status timeline**: a chronological list of events (timestamp, perceived severity, cleared flag) so downstream analysis and the LLM see the full lifespan of each alarm

### 4. LLM Agent (`src/llm_agent.py`)

**Purpose**: Uses OpenAI's LLM to evaluate correlations and determine causality, with lifespan-aware analysis and concrete remediation recommendations.

#### Key Features

- **Prompt Engineering**: Builds comprehensive prompts with degradation details and consolidated alarms including a **status timeline** (chronological status events) per alarm so the LLM can reason about alarm lifespan (raised, severity changes, cleared)
- **Lifespan-Aware Analysis**: Instructs the LLM to note whether each alarm was cleared in the time window or still active, and to use this when judging causality
- **JSON Response**: Structured JSON with verdicts, confidence score, **root_cause_analysis** (optional), per-alarm **lifespan_note** and **suggested_fix** / **remediation_steps**, top reasons, ordered recommended actions, and analysis summary that references alarm lifespans
- **Error Handling**: Robust error handling with retries and fallback responses

### 5. Processing Pipeline (`src/pipeline.py`)

**Purpose**: Orchestrates the complete processing workflow.

#### Workflow Steps

1. Load KPI and alarm data
2. Detect degradations
3. Correlate alarms with degradations
4. Evaluate correlations with LLM (optional)
5. Return comprehensive results dictionary

### 6. Streamlit UI (`app.py`)

**Purpose**: Provides interactive web interface for configuration, visualization, and analysis.

#### Main Tabs

1. **Overview**: Summary statistics and high-level visualizations
2. **EDA**: Exploratory Data Analysis for KPI and alarms data
3. **Threshold Settings**: Per-node degradation thresholds (median percentage and static threshold); line chart with median and two horizontal reference lines
4. **Degradation Details**: Detailed view of individual degradations
5. **Node Analysis**: Node-specific analysis and timelines
6. **Alarms Summary**: Summary of all correlated alarms

---

## Degradation Detection Algorithm

### Threshold Calculation

The system uses **median-based plus static thresholds** to detect degradations. Settings are **per node** and configurable in the **Threshold Settings** tab. A reading is considered degraded only if **both** of the following conditions are met:

1. **Dynamic condition**: `rrc_sr < (median_percentage / 100) × median` — the value is below a given percentage of the node’s median RRC SR.
2. **Static condition**: `rrc_sr < static_threshold` — the value is below an absolute RRC SR floor (e.g. 95%).

#### How Thresholds Are Set

1. **Per-Node Median**: For each node, the median of all RRC SR values is computed.
2. **Per-Node Configuration**: Each node has:
   - **Median percentage** (e.g. 90): Dynamic threshold = median × (percentage / 100). Lower percentage = stricter (more degradations).
   - **Static threshold** (e.g. 95): Absolute RRC SR %; readings must be below this as well.
3. **Both conditions required**: A point is degraded only if it is below **both** the dynamic threshold and the static threshold. This avoids flagging “normal” low values that are still above the static bar.
4. **Defaults**: If a node has no saved settings, default median percentage (e.g. 90) and default static threshold (e.g. 95) from config are used.

#### Example

Node "1900" has median RRC SR = 98.5%, median percentage = 90%, static threshold = 95%.

- Dynamic threshold = 98.5 × 0.90 = 88.65%
- A reading of 94% is below static (95%) but above dynamic (88.65%) → **not** degraded (only one condition met).
- A reading of 88% is below both 88.65% and 95% → **degraded**.

### Degradation Detection Process

#### Step 1: Compute Medians and Thresholds

For each node:
1. Compute median of RRC SR values.
2. Get per-node config (median_percentage, static_threshold) or use defaults.
3. Dynamic threshold = median × (median_percentage / 100).
4. Effective baseline (for severity) = min(dynamic_threshold, static_threshold).

#### Step 2: Identify Degraded Readings

For each node:
1. Mark a reading as degraded if `rrc_sr < dynamic_threshold` **and** `rrc_sr < static_threshold`.

#### Step 3: Group Consecutive Degradations

1. Group consecutive degraded readings together.
2. Each group is a candidate degradation period.

#### Step 4: Calculate Degradation Periods

For each group of consecutive degraded readings:

1. **Start Time**: Minimum timestamp in the group
2. **End Time**: Maximum timestamp in the group
3. **Minimum Value**: Lowest RRC SR value during the period
4. **Duration**: Same as before (multiple readings: end − start + median interval; single: time to next or 1 hour)
5. **Baseline Value**: The effective threshold (min of dynamic and static) used for deviation
6. **Deviation Percent**: `((effective_threshold - min_value) / effective_threshold) × 100`

#### Step 5: Filter by Minimum Duration

- Default minimum duration: 5 minutes.
- Periods shorter than this are filtered out.

#### Step 6: Assign Severity

Based on deviation from the effective threshold:

- **CRITICAL**: Deviation > 50% below threshold
- **MAJOR**: Deviation > 25% below threshold
- **MINOR**: Deviation > 10% below threshold
- **WARNING**: Deviation ≤ 10% below threshold

### Example Degradation Detection

**Scenario**: Node "1900", median = 98.5%, median percentage = 90%, static = 95%. Dynamic = 88.65%, effective = 88.65%.

**Readings**:
- 10:00 - 98.5% (normal)
- 11:00 - 87% (degraded: below both 88.65 and 95)
- 12:00 - 86% (degraded)
- 13:00 - 87.5% (degraded)
- 14:00 - 96% (normal: below static but above dynamic, so not degraded)

**Result**:
- Degradation period: 11:00 to 13:00
- Minimum value: 86%
- Deviation: ((88.65 - 86) / 88.65) × 100 ≈ 2.99%
- Severity: WARNING

---

## Alarm Correlation

### Time Window Configuration

For each detected degradation, the system searches for alarms within a configurable time window:

- **Time Before**: Minutes before degradation start (default: 30 minutes)
- **Time After**: Minutes after degradation end (default: 30 minutes)

**Example**: If degradation occurs from 10:00 to 11:00:
- Window start: 09:30 (30 minutes before)
- Window end: 11:30 (30 minutes after)
- Alarms between 09:30 and 11:30 are considered

### Node Matching

Correlation uses **same-node matching** via a canonical node ID derived from `managedObjectClass`:

- **Canonical node ID**: The numeric part of `MRBTS-X` or `BSC-X` in the alarm's `managedObjectClass` (e.g. `"PLMN-PLMN/MRBTS-1900/EQM_R-4/..."` → `1900`). This must match the node identifier used in the KPI data for the degradation.
- **Strict same-node filter**: For each degradation, only alarms whose canonical node ID **equals** the degradation's node ID are considered. There is no fuzzy or cross-node matching.
- **Alarms without MRBTS/BSC**: Alarms whose `managedObjectClass` contains neither `MRBTS-` nor `BSC-` have no canonical node ID and are **not** correlated to any degradation by node.

### Temporal Relationship Classification

Alarms are classified based on their timing relative to the degradation:

- **BEFORE**: Alarm occurred before degradation start
- **DURING**: Alarm occurred during the degradation period
- **AFTER**: Alarm occurred after degradation end

**Rationale**: Alarms that occur BEFORE or DURING are more likely to be causal.

### Consolidation by Alarm ID

Within the time window for each degradation, the system **consolidates alarm events by alarm ID**:

- **Input**: Raw alarm events (one row per event; the same `alarm_id` can appear multiple times with different timestamps and severities, e.g. raised, updated, cleared).
- **Output**: One row per unique alarm ID. Each consolidated alarm includes:
  - Identity and static fields (alarm_id, node, alarm_type, specific_problem, probable_cause, etc.)
  - Temporal relationship and time offset from degradation start (from the **earliest** event in the window)
  - **Status timeline**: A chronological list of events, each with timestamp, perceived severity, and a cleared flag. This allows the LLM and UI to reason about the alarm's full lifespan (e.g. raised then cleared during the window vs. still active at the end).

So instead of e.g. five correlated "alarms" that are really three unique alarm IDs with multiple events, the system presents three consolidated alarms, each with a full status timeline.

### Correlation Output

For each degradation, the system provides:
- List of **consolidated** correlated alarms (one per unique alarm ID)
- For each alarm: temporal relationship, time offset from degradation start, and **status timeline** (chronological list of status events)
- All alarm details (severity, type, problem description, etc.)

---

## LLM-Based Analysis

### Purpose

The LLM agent evaluates correlations to determine:
1. Whether alarms are **causal** (directly caused the degradation)
2. Whether alarms are **possibly related** (some evidence but not definitive)
3. Whether alarms are **coincidental** (unrelated, just happened at the same time)
4. Whether there's **no correlation** (no relevant alarms found)

### Analysis Process

#### Step 1: Build Comprehensive Prompt

The prompt includes:
- Degradation details (node, timestamps, duration, severity, deviation)
- All correlated alarms (consolidated by alarm ID) with full details and a **status timeline** (chronological list of status events: timestamp, severity, cleared) per alarm so the LLM knows each alarm's lifespan
- Context about RRC SR and common causes
- Guidelines for evaluation, including use of alarm lifespan (cleared vs. still active) when judging causality

#### Step 2: LLM Evaluation

The LLM analyzes:
- **Temporal correlation**: When alarms occurred relative to degradation
- **Spatial correlation**: Whether alarms are from the same node
- **Alarm types**: Whether alarm types typically affect RRC SR
- **Alarm severity**: Critical alarms are more likely to be causal
- **Service impact**: Whether alarms are service-affecting
- **Alarm lifespan**: From each alarm's status timeline, whether it was **cleared** within the time window or **still active** at the end; this is used when judging causality (e.g. cleared during degradation may suggest a transient issue or that the condition was resolved)

#### Step 3: Structured Response

The LLM returns JSON with:
- **Overall Verdict**: causal | possible | coincidental | no_correlation
- **Confidence Score**: 0.0 to 1.0
- **Root Cause Analysis** (optional): Short paragraph on likely root cause(s) and how alarm lifespans support or contradict that
- **Per-Alarm Analysis**: For each alarm: relevance score, is_causal, reasoning; **lifespan_note** (e.g. "Cleared during window at 14:18:15" or "Still active at end of time window"); **suggested_fix** or **remediation_steps** (1–3 concrete steps to address that alarm, based on alarm type, specific problem, and probable cause)
- **Top Reasons**: Key factors supporting the verdict
- **Recommended Actions**: Specific, ordered remediation steps (e.g. "Isolate and restart BBU for node X", "Collect traces if degradation persists")
- **Analysis Summary**: Detailed explanation that explicitly references alarm lifespans where relevant (e.g. "Alarm A was cleared at 14:20; Alarm B remained active")

### Alarm Lifespan and Enriched Output

The LLM is instructed to observe each alarm's **status timeline** and to:
- Note whether each alarm was **cleared** in the time window (last event is CLEARED) or **still active** at the end, and mention this in the analysis
- Use lifespan when judging causality (e.g. alarm cleared during degradation vs. still active)
- Provide **per-alarm suggested fixes** (1–3 concrete steps) based on alarm type, specific problem, and probable cause
- Provide a **root cause analysis** paragraph when relevant, and make **recommended actions** specific and ordered

### Verdict Categories

1. **Causal**: Strong evidence that alarms directly caused the degradation
   - Example: Hardware failure alarm 5 minutes before degradation starts
   
2. **Possible**: Some evidence of correlation but not definitive
   - Example: Minor alarm during degradation, but other factors possible
   
3. **Coincidental**: Alarms present but unlikely to be related
   - Example: Unrelated alarm type (e.g., billing system alarm)
   
4. **No Correlation**: No alarms found or alarms clearly unrelated
   - Example: Degradation with no alarms in time window

### Recommended Actions

Based on the analysis, the LLM suggests actions such as:
- Hardware repair (BBU/RRU replacement)
- Transport link investigation
- Parameter tuning
- Reboot procedures
- Escalation to NOC
- Further PM analysis
- Packet trace collection
- Field inspection

---

## User Interface Components

### Sidebar Configuration

**Logo and Branding**:
- Qeema logo at the top (centered)
- Copyright notice

**Data Files Section**:
- KPI Excel file uploader
- Alarms JSON file uploader
- Option to use default sample files

**Processing Parameters**:
- **Time Before** (0-120 minutes, default: 30): Minutes before degradation to search for alarms
- **Time After** (0-120 minutes, default: 30): Minutes after degradation to search for alarms
- **Use LLM Analysis**: Toggle to enable/disable AI analysis
- **LLM Model**: Select OpenAI model (gpt-4o-mini, gpt-4o, gpt-3.5-turbo)

Per-node degradation thresholds (median percentage and static threshold) are set in the **Threshold Settings** tab, not in the sidebar.

### Main Tabs

#### 1. Overview Tab

**Summary Metrics**:
- Total degradations detected
- Affected nodes count
- Total correlated alarms
- Degradations with alarms
- LLM verdict distribution (if LLM enabled)

**Filters**:
- Filter by node
- Filter by severity

**Visualizations**:
- Degradations over time (scatter plot)
- Degradations per node (bar chart)
- Degradations table

#### 2. EDA (Exploratory Data Analysis) Tab

**KPI Data Sub-Tab**:
- **Filters**: Node selection, date range, optional hour range
- **Statistics**: Total readings, unique nodes, mean/median/min/max/std, date range
- **Visualizations**:
  - Time series plot (RRC SR over time)
  - Distribution histogram
  - Node comparison box plots
  - Statistical summary table by node
  - Temporal patterns (hourly averages, daily trends)

**Alarms Data Sub-Tab**:
- **Filters**: Node, date range, severity, alarm type, specific problem text search
- **Statistics**: Total alarms, unique IDs, unique nodes, date range, counts by severity/type
- **Visualizations**:
  - Alarm timeline (scatter plot)
  - Severity distribution (pie chart)
  - Alarm type distribution (bar chart)
  - Node analysis (alarms per node, severity by node)
  - Temporal patterns (hourly frequency, daily trends)
  - Top problems tables
  - Alarms table

#### 3. Threshold Settings Tab

**Purpose**: Configure per-node degradation thresholds used when running **Process Data**. A reading is degraded only if it is below **both** the dynamic threshold (median × percentage) and the static threshold.

**Features**:
- **Node selector**: Dropdown of all nodes present in the loaded KPI data
- **Per-node controls** (stored in session and used on Process Data):
  - **Median percentage** (e.g. 50–100%, default 90): Dynamic threshold = median × (percentage / 100). Updated as soon as the user changes the value.
  - **Static threshold** (e.g. 0–100%, default 95): Absolute RRC SR %; readings must be below this to count as degraded
- **Line chart** for the selected node:
  - RRC SR time series
  - **Median** horizontal line (gray)
  - **Dynamic threshold** horizontal line (orange), recomputed when median percentage changes
  - **Static threshold** horizontal line (red)
- **Apply to all nodes**: Button to copy the current node’s median percentage and static threshold to every other node
- Settings are persisted in session state and applied when the user clicks **Process Data**; nodes without saved settings use default median percentage and static threshold from config

#### 4. Degradation Details Tab

**Features**:
- Select specific degradation from dropdown
- View detailed degradation information
- See all correlated alarms (consolidated by alarm ID; one row per unique alarm with a **Status Timeline** column showing the chronological status events, e.g. "14:18:14 CRITICAL; 14:18:15 CLEARED")
- Review LLM analysis (if enabled):
  - Overall verdict and confidence
  - Top reasons
  - Root cause analysis (when present)
  - Per-alarm analysis: relevance, is causal, reasoning; **lifespan note** (cleared in window vs. still active); **suggested fix / remediation steps** (when present)
  - Recommended actions
  - Detailed analysis summary

#### 5. Node Analysis Tab

**Features**:
- Select node from dropdown
- View all degradations for selected node
- Timeline visualization showing:
  - Degradation periods
  - RRC SR values over time
- Degradations table for the node

#### 6. Alarms Summary Tab

**Features**:
- Summary statistics (total correlated alarms—unique by alarm ID—unique types, unique severities)
- Alarm type frequency (pie chart)
- Severity distribution (bar chart)
- Most correlated alarm types table
- All correlated alarms table (one row per unique alarm ID; optional **Status Timeline** column with compact timeline string when present)

---

## Configuration Parameters

### Degradation Detection Parameters

| Parameter | Scope | Range/Default | Description |
|-----------|--------|----------------|-------------|
| Median percentage | Per node (Threshold Settings tab) | Default 90 | Dynamic threshold = median × (this / 100). Lower = stricter. Set per node in Threshold Settings. |
| Static threshold | Per node (Threshold Settings tab) | Default 95 (%) | Absolute RRC SR floor. A reading is degraded only if below both this and the dynamic threshold. Set per node in Threshold Settings. |
| Min Duration (minutes) | Global | 1+, default 5 | Minimum duration for a degradation period to be reported. |

### Alarm Correlation Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| Time Before (minutes) | 0-120 | 30 | Minutes before degradation start to search for alarms. |
| Time After (minutes) | 0-120 | 30 | Minutes after degradation end to search for alarms. |

### LLM Analysis Parameters

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| Use LLM Analysis | True/False | True | Enable/disable AI-powered correlation analysis. |
| LLM Model | gpt-4o-mini, gpt-4o, gpt-3.5-turbo | gpt-4o-mini | OpenAI model to use. gpt-4o-mini is faster and cheaper, gpt-4o is more accurate. |

---

## Data Formats

### KPI Excel File Format

**Required Columns** (case-insensitive):
- **Node**: Node/site identifier (numeric or string)
- **Date/Timestamp**: Date of reading (or combined timestamp)
- **Hour**: Hour of day (1-24) - Optional if using combined timestamp
- **RRC SR**: RRC Success Rate value (percentage, numeric)

**Supported Formats**:
1. Separate `date` and `hour` columns (combined automatically)
2. Single `timestamp` column with full datetime
3. Column names are auto-detected (case-insensitive)

**Example**:
```
| date       | hour | node  | RRC SR |
|------------|------|-------|--------|
| 2025-09-08 | 1    | 1900  | 98.91  |
| 2025-09-08 | 2    | 1900  | 99.51  |
| 2025-09-08 | 3    | 1900  | 98.23  |
```

### Alarms JSON File Format

**Supported Formats**:
1. **JSON Array**: `[{...}, {...}]`
2. **Line-delimited JSON**: One JSON object per line

**Required Fields**:
- `alarmId`: Unique alarm identifier
- `alarmRaisedTime` or `nbiEventTime`: Timestamp (format: "YYYY-M-D,HH:MM:SS.s,+T:0")
- `managedObjectClass`: Managed object path (e.g., "PLMN-PLMN/MRBTS-685256/..."). The numeric part of `MRBTS-X` or `BSC-X` is used as the canonical node ID for same-node correlation with KPI data.
- `perceivedSeverity`: Alarm severity (CRITICAL, MAJOR, MINOR, WARNING, CLEARED)
- `alarmType`: Type of alarm (QUALITY_OF_SERVICE_ALARM, COMMUNICATIONS_ALARM, etc.)
- `specificProblem`: Specific problem description

**Optional Fields** (recommended):
- `nbiOptionalInformation`: Additional info with node names (e.g., "NEName=EMH229|siteObjName=...")
- `probableCause`: Probable cause description
- `additionalText`: Additional alarm text

**Example**:
```json
{
  "alarmId": "328226801",
  "alarmRaisedTime": "2025-9-10,14:18:14.0,+3:0",
  "nbiEventTime": "2025-9-10,14:18:18.0,+3:0",
  "managedObjectClass": "PLMN-PLMN/MRBTS-685256/LNBTS-685256/...",
  "perceivedSeverity": "CRITICAL",
  "alarmType": "QUALITY_OF_SERVICE_ALARM",
  "specificProblem": "RRC Connection Establishment Failure",
  "nbiOptionalInformation": "NEName=EMH229|siteObjName=EMH229_TWL|..."
}
```

---

## Workflow

### Complete Processing Workflow

1. **Data Loading**
   - User uploads or selects KPI Excel file
   - User uploads or selects Alarms JSON file
   - System loads and standardizes both datasets

2. **Configuration**
   - User sets per-node thresholds in the **Threshold Settings** tab (median percentage and static threshold; optional, defaults used if not set)
   - User sets time window parameters (default: 30 minutes before/after)
   - User enables/disables LLM analysis
   - User selects LLM model

3. **Processing**
   - User clicks "Process Data" button
   - System detects degradations:
     - Computes median per node; applies per-node config (or defaults)
     - Marks readings degraded only if below both dynamic (median × percentage) and static threshold
     - Groups consecutive degradations
     - Calculates degradation periods
     - Assigns severity levels
   - System correlates alarms:
     - For each degradation, finds alarms in time window
     - Matches alarms to nodes
     - Classifies temporal relationships
   - System evaluates with LLM (if enabled):
     - For each degradation, builds prompt
     - Calls OpenAI API
     - Parses JSON response
     - Stores analysis results

4. **Visualization and Analysis**
   - Results displayed in multiple tabs
   - User can explore degradations, alarms, and correlations
   - User can view LLM analysis and recommendations
   - User can export or drill down into specific cases

### EDA Workflow (Before Processing)

1. **Data Loading**
   - System loads KPI and alarms data directly (no processing needed)
   - Data available immediately in EDA tab

2. **Exploration**
   - User applies filters (nodes, dates, etc.)
   - System displays statistics and visualizations
   - User can explore data patterns before running full analysis

---

## Troubleshooting

### Common Issues

#### No Degradations Detected

**Possible Causes**:
- Median percentage too low or static threshold too high (thresholds too loose)
- Data doesn't contain values below both thresholds
- Minimum duration filter too strict

**Solutions**:
- In **Threshold Settings**, lower the median percentage (e.g. 85 or 80) or lower the static threshold so more readings can qualify as degraded
- Check data quality and range
- Verify timestamps are correctly parsed

#### Alarms Not Correlating

**Possible Causes**:
- Canonical node ID mismatch: KPI node does not match the numeric part of `MRBTS-X` or `BSC-X` in alarm `managedObjectClass`, or alarms lack MRBTS/BSC in `managedObjectClass`
- Time window too narrow
- Alarms outside time window

**Solutions**:
- Ensure KPI node matches the numeric part of MRBTS/BSC in alarm `managedObjectClass`; check node identifiers in both datasets
- Increase time window (time before/after)
- Verify alarm timestamps are correct

#### LLM Analysis Errors

**Possible Causes**:
- OpenAI API key not set
- API key invalid or expired
- Network connectivity issues
- Rate limiting

**Solutions**:
- Verify `.env` file contains `OPENAI_API_KEY`
- Check API key is valid and has credits
- Check network connection
- Wait and retry if rate limited

#### Data Loading Errors

**Possible Causes**:
- Incorrect file format
- Missing required columns
- Invalid timestamps
- Corrupted files

**Solutions**:
- Verify file format matches requirements
- Check column names are present
- Validate timestamp formats
- Try with sample data files first

---

## Best Practices

### Threshold Selection

- **Start with defaults** (e.g. median percentage 90, static threshold 95): Good balance between sensitivity and false positives
- **Lower median percentage or static threshold for more sensitivity**: More readings will fall below both bars and be flagged as degraded
- **Raise median percentage or static threshold for fewer false positives**: Stricter bars mean fewer degradations reported
- Use the **Threshold Settings** tab to tune per node and to see the median and both threshold lines on the chart

### Time Window Configuration

- **Default (30 minutes)**: Works well for most cases
- **Increase for delayed alarms**: Some alarm systems have delays, increase time before
- **Decrease for real-time analysis**: If alarms are immediate, can reduce window

### LLM Model Selection

- **gpt-4o-mini**: Fast, cost-effective, good for most cases
- **gpt-4o**: More accurate, use for critical analysis
- **gpt-3.5-turbo**: Legacy option, less recommended

### Data Quality

- **Ensure complete data**: Missing timestamps or values can cause issues
- **Validate node alignment**: KPI node identifiers should match the numeric part of `MRBTS-X` or `BSC-X` in alarm `managedObjectClass` so same-node correlation works (e.g. KPI node `1900` with alarms on `MRBTS-1900`).
- **Check date ranges**: Ensure KPI and alarm data overlap in time

---

## Technical Details

### Performance Considerations

- **Large datasets**: System handles large datasets efficiently using pandas
- **LLM calls**: Each degradation requires one LLM API call (can be slow for many degradations)
- **Caching**: Consider implementing caching for repeated analyses

### Scalability

- **Current design**: Processes data in-memory (suitable for moderate datasets)
- **Future enhancements**: Could add database backend, batch processing, or streaming

### Extensibility

The system is designed to be extensible:
- **Additional KPIs**: Can be added by modifying data loader and detector
- **Additional detection methods**: Can implement z-score, EWMA, ML-based methods
- **Additional LLM providers**: Can add support for other LLM APIs
- **Custom visualizations**: Streamlit makes it easy to add new charts

---

## Conclusion

This system provides a comprehensive solution for detecting RRC SR degradations and correlating them with FM alarms. The combination of statistical detection, intelligent correlation, and AI-powered analysis provides network operators with actionable insights to quickly resolve service-affecting issues.

For questions or issues, please refer to the project repository or contact the development team.

---

**Document Version**: 1.2  
**Last Updated**: February 2026  
**Maintained by**: Qeema Development Team
