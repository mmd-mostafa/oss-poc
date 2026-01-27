# RRC SR Degradation Detection and Alarm Correlation System

An AI-powered system for detecting RRC (Radio Resource Control) Success Rate (SR) KPI degradations, correlating them with Fault Management (FM) alarms, and providing intelligent analysis and remediation recommendations.

## Overview

This system helps telecommunications network operators:
- **Detect KPI degradations** automatically using statistical methods
- **Correlate degradations with alarms** within configurable time windows
- **Analyze correlations** using AI to determine causal relationships
- **Get actionable recommendations** for remediation

Perfect for network operations centers (NOCs) and network engineers who need to quickly identify and resolve service-affecting issues.

## Features

- **Degradation Detection**: Automatically detects RRC SR degradations using configurable percentile-based thresholds
- **Alarm Correlation**: Finds and correlates FM alarms within configurable time windows around degradation periods
- **AI-Powered Analysis**: Uses OpenAI LLM to evaluate correlations and determine causal relationships
- **Interactive UI**: Streamlit-based web interface for visualization and analysis
- **Comprehensive Reporting**: Detailed analysis with recommended remediation actions

## Installation

### Prerequisites

- **Python 3.8 or higher** (Python 3.11 recommended)
- **pip** (Python package installer - usually comes with Python)
- **OpenAI API key** (for LLM analysis) - [Get one here](https://platform.openai.com/api-keys)
  - Free tier available for testing
  - Paid tier required for production use

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd oss-poc
   ```

2. **Create a virtual environment (recommended):**
   
   **Option A: Using venv (built-in with Python):**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```
   
   **Option B: Using conda:**
   ```bash
   conda create -n oss-poc python=3.11
   conda activate oss-poc
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
   - **Important**: Never commit the `.env` file to version control. It's already included in `.gitignore`.

5. **Verify installation:**
   ```bash
   python -c "import pandas, streamlit, openai; print('All packages installed successfully!')"
   ```

## Usage

### Quick Start

1. **Ensure your virtual environment is activated** (if using one)

2. **Start the Streamlit application:**
   ```bash
   streamlit run app.py
   ```

3. **Access the UI:**
   - The application will automatically open in your default web browser
   - If not, navigate to `http://localhost:8501`

4. **First-time setup:**
   - The app includes sample data files in the `data/` directory
   - Check "Use default data files" in the sidebar to use them
   - Or upload your own KPI Excel and Alarms JSON files

5. **Configure and process:**
   - Adjust processing parameters in the sidebar:
     - **Percentile Threshold**: Lower values detect more degradations (default: 10)
     - **Time Before/After**: Time window to search for alarms (default: 30 minutes)
     - **LLM Model**: Choose the OpenAI model for analysis
   - Click "🚀 Process Data" to run the analysis
   - Results will appear in the tabs below

### Data Format

#### KPI Excel File

The Excel file should contain columns for:
- **Node**: Node/site identifier (numeric or string)
- **Date**: Date of the KPI reading (or combined **Timestamp** column)
- **Hour**: Hour of the day (1-24) - *Optional if using combined Timestamp column*
- **RRC SR**: RRC Success Rate value (percentage)

**Supported formats:**
- Separate `date` and `hour` columns (will be combined automatically)
- Single `timestamp` column with full datetime
- Column names are detected automatically (case-insensitive)

**Example structure:**
| date | hour | node | RRC SR |
|------|------|------|--------|
| 2025-09-08 | 1 | 1900 | 98.91 |
| 2025-09-08 | 2 | 1900 | 99.51 |

#### Alarms JSON File

The JSON file can be in one of two formats:

**Format 1: JSON Array** (recommended)
```json
[
  {
    "alarmId": "328226801",
    "alarmRaisedTime": "2025-9-10,14:18:14.0,+3:0",
    "nbiEventTime": "2025-9-10,14:18:18.0,+3:0",
    "managedObjectClass": "PLMN-PLMN/MRBTS-685256/...",
    "perceivedSeverity": "CRITICAL",
    ...
  },
  ...
]
```

**Format 2: Line-delimited JSON** (one JSON object per line)
```json
{"alarmId": "328226801", "alarmRaisedTime": "...", ...}
{"alarmId": "328226802", "alarmRaisedTime": "...", ...}
```

**Required fields:**
- `alarmId`: Unique alarm identifier
- `alarmRaisedTime` or `nbiEventTime`: Timestamp (format: "YYYY-M-D,HH:MM:SS.s,+T:0")
- `managedObjectClass`: Managed object path (e.g., "PLMN-PLMN/MRBTS-685256/...")
- `nbiOptionalInformation`: Additional information with node names (optional but recommended)
- `perceivedSeverity`: Alarm severity (CRITICAL, MAJOR, MINOR, WARNING, CLEARED)
- `alarmType`: Type of alarm (QUALITY_OF_SERVICE_ALARM, COMMUNICATIONS_ALARM, etc.)
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
oss-poc/
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

### Installation Issues

**Package installation fails:**
- Ensure you're using Python 3.8 or higher: `python --version`
- Try upgrading pip: `pip install --upgrade pip`
- On some systems, you may need to install system dependencies for `openpyxl`:
  - Ubuntu/Debian: `sudo apt-get install python3-dev`
  - macOS: Usually not needed
  - Windows: Usually not needed

**Import errors after installation:**
- Ensure your virtual environment is activated
- Reinstall packages: `pip install -r requirements.txt --force-reinstall`

### OpenAI API Key Issues
- Ensure `.env` file exists in the project root and contains `OPENAI_API_KEY=your_key_here`
- Verify the API key is valid and has sufficient credits
- Check that `python-dotenv` is installed: `pip install python-dotenv`
- Test your API key: `python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"`

### Data Loading Errors

**Excel file issues:**
- Verify the file has columns for node, date/hour (or timestamp), and RRC SR
- Check that RRC SR values are numeric (not text)
- Ensure dates are in a standard format (YYYY-MM-DD or similar)

**JSON file issues:**
- Verify the JSON is valid (use a JSON validator)
- Check that required fields are present (alarmId, timestamps, managedObjectClass)
- The system supports both array format `[{...}]` and line-delimited format

**Timestamp parsing errors:**
- For alarms: Timestamps should be in format "YYYY-M-D,HH:MM:SS.s,+T:0"
- For KPI: Dates should be parseable by pandas (standard date formats work)

### No Degradations Detected
- **Try a lower percentile threshold** (e.g., 5 instead of 10) - this makes detection more sensitive
- Verify KPI data contains valid RRC SR values (check for NaN or invalid numbers)
- Check that timestamps are correctly parsed (look at the debug message after processing)
- Ensure you have enough data points per node (at least 10-20 readings recommended)
- Check the data range - degradations are relative to each node's historical performance

### Performance Issues
- **LLM analysis is slow**: This is normal - each degradation requires an API call
- **Large datasets**: Consider processing in batches or increasing timeout settings
- **Memory issues**: Close other applications or process smaller date ranges

## Development

### Project Structure

```
oss-poc/
├── data/                      # Sample data files
│   ├── Fake data.xlsx        # Sample KPI data
│   └── Fake alarms.json      # Sample alarm data
├── src/                       # Source code modules
│   ├── __init__.py
│   ├── data_loader.py        # Data loading and parsing
│   ├── degradation_detector.py  # Degradation detection
│   ├── alarm_correlator.py   # Alarm correlation
│   ├── llm_agent.py          # LLM integration
│   └── pipeline.py           # Main processing pipeline
├── app.py                     # Streamlit UI application
├── config.py                  # Configuration settings
├── .env.example               # Environment variables template
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── docs.md                    # Project documentation
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Commit your changes: `git commit -m 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

### Running Tests

Currently, manual testing is recommended. Test with the provided sample data files first, then with your own data.

## License

This project is part of the Qeema OSS initiative.

## Support

- For issues or questions, please refer to the project documentation in `docs.md`
- For bugs or feature requests, please open an issue on GitHub
- For detailed project requirements and goals, see `docs.md`
