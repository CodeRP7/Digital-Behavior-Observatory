# Data profile summary

## Selected dataset

Google Analytics sample dataset (public BigQuery public dataset)

## Main strength

This dataset is appropriate for a digital behavior observatory because it represents realistic anonymized website behavior, including session-level engagement, user acquisition patterns, device context, and conversion signals.

## Observed structure from public schema documentation

- session identifiers and visit counts
- timestamp fields for event chronology
- totals for page views, hits, and transaction signals
- device/browser/platform attributes
- geography and traffic source dimensions
- event arrays capturing user actions and interactions

## Planned Day 1 validation steps

1. Confirm public access path and legal usage.
2. Inspect schema and field availability.
3. Check for missing / malformed records.
4. Profile session coverage and date ranges.
5. Document any data limitations before modeling.

## Decision

We are choosing a real public digital interaction dataset instead of generating synthetic data because the project is meant to simulate a portfolio-quality analytics workflow grounded in realistic behavior.
