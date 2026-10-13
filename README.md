# Digital Behavior Observatory

This repository is a day-by-day project focused on digital behavior analytics. The current completed milestones are dataset selection (Day 1) and a reproducible event-cleaning and sessionization pipeline (Day 2).

## Day 1 milestone

The project began with project setup and selection of the public Google Analytics Universal Analytics sample dataset.

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

No synthetic or fabricated data is being used. The raw export is local and is not committed. See [data/README.md](data/README.md) for the exact BigQuery table, export query, schema, and data handling notes.

## Day 3 milestone: user journey and funnel analysis

The Day 3 work focuses on behavioral sequence analysis using the actual cleaned GA export and the observed event taxonomy. The analysis is grounded in real user behaviors rather than generic e-commerce assumptions, so the funnel is defined from session evidence such as product-discovery pages, `Quickview Click`, `Product Click`, `Add to Cart`, checkout pages, and purchase confirmation pages.

### Day 3 outputs

- [src/journey_analysis.py](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/src/journey_analysis.py): reusable journey extraction, transition summaries, pattern analysis, and funnel logic
- [notebooks/03_user_journeys.ipynb](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/notebooks/03_user_journeys.ipynb): notebook walkthrough covering journey prep, transition analysis, pattern summaries, funnel stages, and drop-off analysis
- [sql/funnel_analysis.sql](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/sql/funnel_analysis.sql): SQL view/query patterns for funnel, conversion, and drop-off analysis
- [tests/test_day3_journey_analysis.py](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/tests/test_day3_journey_analysis.py): focused regression tests for ordered event sequences, transition probabilities, and funnel logic

### Observed findings

- 2,556 sessions analyzed
- 408 unique journey patterns observed
- The dominant session pattern is a repeated `PAGE` browsing flow, indicating that a large share of sessions are discovery-only rather than transaction-driven
- The strongest transition is `PAGE -> PAGE`, which confirms heavy browse behavior before purchase intent develops
- Funnel counts from the observed, ordered sequence were:
  - product discovery: 1,758 sessions
  - add to cart: 242 sessions
  - checkout: 130 sessions
  - purchase: 38 sessions
- The sharpest drop-off occurs between product discovery and add to cart, followed by a secondary decline between checkout and purchase

### Business interpretation

The evidence suggests that users browse extensively, but many sessions never move beyond discovery or cart-entry intent. The largest opportunity for conversion uplift is in reducing friction or increasing intent after product discovery, rather than in the purchase stage alone.

## Day 4 milestone: behavioral segmentation

The Day 4 workflow moves from session diagnostics to user-level audience segmentation. The analysis uses the real multi-session user behavior in the cleaned GA export rather than arbitrary business labels. The project therefore treats the user as the primary behavioral unit because repeated visitors are present in the data, and it builds a compact feature set based on engagement, navigation, return frequency, and action diversity.

### Day 4 outputs

- [src/feature_engineering.py](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/src/feature_engineering.py): reusable user-level behavioral feature generation, compact feature selection, and clustering preparation
- `data/processed/user_behavior_features.csv`: one row per user with behavior metrics used for segmentation
- `data/processed/user_behavior_matrix.csv`: scaled feature matrix for clustering
- `data/processed/user_segment_summary.csv`: cluster-level behavioral profiles

### Behavioral feature logic

The feature set is intentionally compact and grounded in the observed dataset. It includes user-level measures such as session count, average session duration, events per session, navigation depth, action diversity, and return frequency. Post-conversion metrics are intentionally excluded from the clustering matrix so the segmentation captures underlying behavioral patterns rather than a downstream outcome.

## Day 5 milestone: anomaly detection

The Day 5 workflow focuses on finding unusual behavioral patterns in the cleaned session-level data without assuming that unusual behavior is malicious. The session remains the primary unit of analysis because the project was built around session behavior and session features already derived from the event stream.

### Day 5 outputs

- [src/anomaly_detection.py](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/src/anomaly_detection.py): reusable session anomaly engineering, robust statistical checks, and Isolation Forest scoring
- `data/processed/session_anomaly_scores.csv`: session-level anomaly ranking and behavioral diagnostics
- `data/processed/session_anomaly_summary.csv`: aggregate profile of anomalous versus normal sessions

### Behavioral anomaly logic

The anomaly model uses interpretable session metrics already established in the project: session duration, event volume, navigation depth, unique action counts, repeated-action counts, and events per minute. The analysis does not treat user or session identifiers as features and intentionally avoids conversion or target labels because the goal is to identify unusual behavior patterns for investigation rather than automatic fraud labeling.

## Day 6 milestone: conversion prediction and behavioral modeling

The Day 6 workflow frames conversion as a session-level classification problem using the project’s real GA behavioral data. The target is the observed transaction flag already encoded in the cleaned session features, and the modeling dataset excludes identifiers and post-outcome signals so the model only uses information available before the conversion decision is known.

### Day 6 outputs

- [src/modeling.py](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/src/modeling.py): reusable conversion dataset builder, feature leakage audit, model comparison pipeline, and error analysis helpers
- [notebooks/06_conversion_prediction.ipynb](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/notebooks/06_conversion_prediction.ipynb): end-to-end conversion prediction notebook covering problem framing, leakage audit, model training, evaluation, and business interpretation
- [sql/conversion_prediction.sql](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/sql/conversion_prediction.sql): SQL patterns for conversion-rate summaries by device, behavior, and time-of-day context
- [tests/test_day6_conversion_modeling.py](C:/Users/rahul/OneDrive/Desktop/repos/Digital-Behavior-Observatory/tests/test_day6_conversion_modeling.py): regression tests for leakage safeguards, target definition, and model comparison behavior

### Modeling logic

The final prediction unit is the composite session (`user_id + source_session_id`), which aligns with the source schema and avoids leakage from multi-session user histories. Candidate features include session engagement depth, action diversity, page volume, dwell-time intensity, device/context variables, and pre-session user behavior measures such as return frequency. The leakage audit explicitly excludes `transaction_count`, `converted`, user IDs, source session IDs, and timestamps that would be unavailable at prediction time.

The comparison uses a validation split with class imbalance in mind and evaluates a small set of defensible models: logistic regression, random forest, and histogram gradient boosting. The logistic regression model performs best on validation average precision, which makes it both interpretable and operationally useful for identifying the most conversion-relevant behavioral signals.

### Business interpretation

The strongest conversion signals in this dataset are tied to intentional browsing and product discovery: deeper navigation, higher action diversity, and more purposeful exits or entry pages are associated with conversion probability. The evidence is consistent with the earlier Days 3–5 findings: conversion is not driven by isolated clicks alone, but by sustained, meaningful engagement that reflects shopper intent rather than passive browsing.

## Current status

Completed:

- repository initialization
- project structure
- dataset selection rationale
- data documentation foundation
- reproducible Day 2 data-quality, cleaning, timestamp, session, and behavioral-feature pipeline
- Day 3 user journey and funnel analysis with dataset-grounded outputs, SQL, notebook, and tests
- Day 4 user-level behavioral feature engineering and segmentation preparation with a compact clustering-ready feature set
- Day 5 anomaly detection and behavioral outlier diagnostics
- Day 6 conversion prediction and behavioral modeling with leakage audit, modeling pipeline, notebook, SQL, and tests

### Run the Day 2 pipeline

Place the CSV export described in [data/README.md](data/README.md) in `data/raw/`, then run these commands from the repository root:

```bash
python -m src.preprocessing
python -m unittest discover -s tests
```

The pipeline creates `data/processed/events_processed.csv`, `data/processed/session_features.csv`, and `reports/day2_data_quality.md`. Generated CSV files and chart images are intentionally ignored by Git; regenerate them from the raw export as needed. Open and run `notebooks/02_session_analysis.ipynb` after running the pipeline.

The full analytical workflow, notebooks, and modeling work will continue in subsequent day-by-day milestones after this foundation is confirmed.
