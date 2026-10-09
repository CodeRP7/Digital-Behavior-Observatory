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

## Current status

Completed:

- repository initialization
- project structure
- dataset selection rationale
- data documentation foundation
- reproducible Day 2 data-quality, cleaning, timestamp, session, and behavioral-feature pipeline
- Day 3 user journey and funnel analysis with dataset-grounded outputs, SQL, notebook, and tests

### Run the Day 2 pipeline

Place the CSV export described in [data/README.md](data/README.md) in `data/raw/`, then run these commands from the repository root:

```bash
python -m src.preprocessing
python -m unittest discover -s tests
```

The pipeline creates `data/processed/events_processed.csv`, `data/processed/session_features.csv`, and `reports/day2_data_quality.md`. Generated CSV files and chart images are intentionally ignored by Git; regenerate them from the raw export as needed. Open and run `notebooks/02_session_analysis.ipynb` after running the pipeline.

The full analytical workflow, notebooks, and modeling work will continue in subsequent day-by-day milestones after this foundation is confirmed.
