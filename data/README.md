# Data documentation

## Selected dataset

Google Analytics sample dataset (public BigQuery dataset)

## Why this dataset was selected

This dataset is a strong match for the project because it captures digital interaction at a realistic product and user journey level. It includes meaningful session-level and event-level information including:

- user activity across sessions
- time-based engagement patterns
- device and browser context
- traffic source and acquisition channel
- geolocation information
- conversion and behavior signals

## Initial schema profile

The public dataset exposes session and event-like fields commonly used in digital analytics, including but not limited to:

- fullVisitorId / visitor identifier
- visitId / session identifier
- visitNumber
- visitStartTime
- date
- totals
- trafficSource
- device
- geoNetwork
- customDimensions
- hits / event-level arrays

## Initial quality checks to perform

During the acquisition and exploration phase, the project will verify:

- missing values and null rates
- duplicate session identifiers
- date range coverage
- device and source distributions
- event completeness
- conversion and non-conversion mix

## Important caveat

This repository does not yet include the full raw dataset files. The project will load the public dataset through a documented acquisition path in later stages. The current deliverable is the dataset rationale and the project foundation for the analysis pipeline.
