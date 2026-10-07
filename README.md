# Digital Behavior Observatory

This repository is the Day 1 foundation for a production-style portfolio project focused on digital behavior analytics. The goal is to analyze anonymized user interactions to understand engagement, session dynamics, funnel performance, behavioral segments, anomalies, and conversion predictors.

## Day 1 milestone

The project begins with project setup and dataset selection. This repository currently contains the initial foundation only, not the full seven-day analysis pipeline.

## Project purpose

The project analyzes anonymized digital interaction data to answer questions such as:

- Which user journeys lead to conversion?
- Where do sessions drop off?
- Which behaviors indicate intent or friction?
- Which user groups behave differently?
- Which sessions may be anomalous or bot-like?
- Which behavioral features help predict conversion?

## Dataset decision

The strongest real dataset for this project is the public Google Analytics sample dataset available through Google BigQuery public datasets.

### Why this dataset is the best fit

- It represents real digital behavior at session and event granularity.
- It contains page/view event streams, user/session attributes, device information, geography, acquisition source, and conversion-related metrics.
- It supports user journey, funnel, segmentation, anomaly, and conversion modeling analysis.
- It is anonymized and publicly available for legal use in analytics learning and portfolio work.
- It aligns well with the project goal of studying digital engagement and conversion patterns.

### Dataset source

- Source: Google Analytics sample dataset in BigQuery public datasets
- Access type: public, research-friendly, anonymized
- Documentation: Google Cloud BigQuery public dataset documentation

### Primary use in project

This dataset will provide the basis for:

- sessionization
- event-level cleaning
- entry/exit behavior analysis
- funnel analysis
- behavioral segmentation
- anomaly detection
- conversion prediction

## Repository structure

Digital-Behavior-Observatory/
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
├── notebooks/
├── src/
├── sql/
├── visuals/
├── models/
├── reports/
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
└── .gitkeep placeholders for empty folders

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Requirements

This project will use:

- Python
- Pandas
- NumPy
- Matplotlib
- Plotly
- Scikit-learn
- SQL
- Jupyter
- Git/GitHub

## Data acquisition note

No synthetic or fabricated data is being used. The project intentionally starts with a real public dataset rather than a toy dataset so the analysis remains representative of real digital behavior patterns.

## Current status

This version contains the Day 1 setup milestone only:

- repository initialization
- project structure
- dataset selection rationale
- data documentation foundation
- initial requirements and ignore rules

The full analytical workflow, notebooks, and modeling work will continue in subsequent day-by-day milestones after this foundation is confirmed.
