# RRC SR Degradation Detection and Alarm Correlation System

An AI-powered system for detecting RRC (Radio Resource Control) Success Rate (SR) KPI degradations, correlating them with Fault Management (FM) alarms, and providing intelligent analysis and remediation recommendations.

## Features

- **Degradation Detection**: Automatically detects RRC SR degradations using configurable percentile-based thresholds
- **Alarm Correlation**: Finds and correlates FM alarms within configurable time windows around degradation periods
- **AI-Powered Analysis**: Uses OpenAI LLM to evaluate correlations and determine causal relationships
- **Interactive UI**: Streamlit-based web interface for visualization and analysis
- **Comprehensive Reporting**: Detailed analysis with recommended remediation actions

## Installation

### Prerequisites

- Python 3.8 or higher
- Conda environment (recommended) or virtual environment
- OpenAI API key (for LLM analysis)

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd tele-poc
   ```

2. **Activate the conda environment:**
   ```bash
   conda activate qeema-oss
   ```

3. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   - Copy the example environment file:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your OpenAI API key:
     ```
     OPENAI_API_KEY=your_actual_api_key_here
     ```
   - Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)

## Usage

### Running the Streamlit UI

1. **Start the Streamlit application:**
   ```bash
   streamlit run app.py
   ```

2. **Access the UI:**
   - The application will open in your default web browser
   - If not, navigate to `http://localhost:8501`

3. **Configure and process:**
   - Use the sidebar to configure processing parameters
   - Upload KPI Excel file and Alarms JSON file (or use default files)
   - Adjust percentile threshold and time windows
   - Click "Process Data" to run the analysis

### Data Format

#### KPI Excel File

The Excel file should contain columns for:
- **Node**: Node/site identifier
- **Timestamp**: Timestamp of the KPI reading
- **RRC SR**: RRC Success Rate value (percentage)

The system will automatically detect these columns by name (case-insensitive).

#### Alarms JSON File

The JSON file should contain one JSON object per line, with fields including:
- `alarmId`: Unique alarm identifier
- `alarmRaisedTime`: Timestamp when alarm was raised
- `alarmClearedTime`: Timestamp when alarm was cleared (if applicable)
- `nbiEventTime`: Event timestamp
- `managedObjectClass`: Managed object path (e.g., "PLMN-PLMN/MRBTS-685256/...")
- `nbiOptionalInformation`: Additional information with node names
- `perceivedSeverity`: Alarm severity (CRITICAL, MAJOR, MINOR, etc.)
- `alarmType`: Type of alarm
- `specificProblem`: Specific problem description

### Configuration Parameters

- **Percentile Threshold** (5-25, default: 10): Readings below this percentile are considered degraded
- **Time Before** (0-120 minutes, default: 30): Minutes before degradation start to search for alarms
- **Time After** (0-120 minutes, default: 30): Minutes after degradation end to search for alarms
- **LLM Model**: Choose between gpt-4o-mini, gpt-4o, or gpt-3.5-turbo

### Using the UI

#### Overview Tab
- View summary statistics
- See degradations over time
- Filter by node and severity
- View degradations table

#### Degradation Details Tab
- Select a specific degradation
- View detailed information
- See correlated alarms
- Review LLM analysis and recommendations

#### Node Analysis Tab
- Select a node
- View all degradations for that node
- See timeline visualization
- Analyze node-specific patterns

#### Alarms Summary Tab
- View summary of all correlated alarms
- See alarm type and severity distributions
- Identify most common alarm types
- Review all correlated alarms

## Project Structure

```
tele-poc/
├── data/                      # Data files
│   ├── Fake data.xlsx        # KPI data
│   └── Fake alarms.json      # Alarm data
├── src/                       # Source code modules
│   ├── __init__.py
│   ├── data_loader.py        # Data loading and parsing
│   ├── degradation_detector.py  # Degradation detection
│   ├── alarm_correlator.py   # Alarm correlation
│   ├── llm_agent.py          # LLM integration
│   └── pipeline.py           # Main processing pipeline
├── app.py                     # Streamlit UI application
├── config.py                  # Configuration settings
├── .env                       # Environment variables (not in git)
├── .env.example               # Environment variables template
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── docs.md                    # Project documentation
```

## How It Works

1. **Data Loading**: Loads KPI data from Excel and alarm data from JSON
2. **Degradation Detection**: 
   - Calculates percentile-based thresholds for each node
   - Identifies readings below threshold
   - Groups consecutive degraded readings into degradation periods
3. **Alarm Correlation**:
   - Extracts node identifiers from alarms
   - Matches alarms to degradations by node and time window
   - Determines temporal relationships (before, during, after)
4. **LLM Analysis**:
   - Builds comprehensive prompts with degradation and alarm details
   - Calls OpenAI API for correlation analysis
   - Evaluates causal vs coincidental relationships
   - Provides remediation recommendations
5. **Visualization**: Presents results in interactive Streamlit UI

## Troubleshooting

### OpenAI API Key Issues
- Ensure `.env` file exists and contains `OPENAI_API_KEY`
- Verify the API key is valid and has sufficient credits
- Check that `python-dotenv` is installed

### Data Loading Errors
- Verify Excel file format and column names
- Check JSON file format (one JSON object per line)
- Ensure timestamps are in a parseable format

### No Degradations Detected
- Try adjusting the percentile threshold (lower values = more sensitive)
- Verify KPI data contains valid RRC SR values
- Check that timestamps are correctly parsed

## License

This project is part of the Qeema OSS initiative.

## Support

For issues or questions, please refer to the project documentation in `docs.md`.
