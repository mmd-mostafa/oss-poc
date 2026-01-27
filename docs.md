Goal:
Build an AI agent that continuously monitors PM and FM Hive tables, detects degradations in KPIs (example KPI: RRC Success Rate), correlates degradations with FM alarms/events, determines whether an alarm is relevant (causal) or coincidental, and provides recommended remediation steps. If no correlation is found, flag the degradation and note no FM correlation.


Project Requirements:
Functional requirements
1. KPI monitoring & degradation detection
Continuously detect degradations for selected KPIs (start with RRC Success Rate).
Support configurable detection methods: rule-based thresholds, statistical anomaly detection (z-score, EWMA), and ML-based change point detection.
Provide: detection timestamp, affected entity (site/cell), baseline KPI, observed KPI, magnitude & duration of degradation, confidence score, and historical context.
2. Temporal correlation with FM alarms
For each detected degradation, retrieve FM alarms within a configurable time window (e.g., T_before minutes before onset to T_after after onset).
Compute temporal overlap and sequence relationships (alarms preceding, during, or after degradation).
Support both exact and fuzzy time matching (account for clock skew, delayed reporting).
3. Relevance (causal vs coincidental) assessment
Score each candidate alarm for relevance using features including:
Alarms description : does alarm is service affecting fault ? (e.g., specific alarm types typically cause RRC issues)
Spatial match (same site/cell or related managed objects)
Alarm type/severity and historical correlation patterns
Alarm duration vs degradation duration
Co-occurrence frequency in historical labeled incidents for same or different nodes
Output per-alarm relevance score and an overall correlation verdict: correlated causal, correlated possible, coincidental, no correlation found.
Explainability: provide top features/reasons supporting the relevance decision (timestamps, fields, historical examples).
4. Root-cause suggestions & recommended actions
Map likely causal alarm types to recommended actions (investigate BBU/RRU, check transport link, reboot, parameter tuning, escalate to NOC, etc.).
If no FM correlation: recommend further actions such as deeper PM analysis, cross-KPI correlation, packet traces, or field inspection.
5. Reporting and alerts
Option A : degradation detected in node X with no correlation with FM .
Option B : Degredation detected in node X correlating with alarm ( Alarm X ) – Proposed Action : HW repair/ MW Link adjustment , etc 