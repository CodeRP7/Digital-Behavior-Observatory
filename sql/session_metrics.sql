-- Day 2 session metrics
-- Expected source: data/processed/session_features.csv
-- SQL dialect: DuckDB (PERCENTILE_CONT and boolean columns are used).
--
-- Expected columns:
-- session_id, user_id, source_session_id, session_start, session_end,
-- session_duration_seconds, event_count, unique_event_count,
-- unique_page_count, unique_action_count, navigation_depth,
-- repeated_action_count, first_event, last_event, entry_page, exit_page,
-- device_type, platform, browser, transaction_count, converted,
-- events_per_minute, session_date, hour, day_of_week, week, month,
-- is_weekend, time_of_day.

CREATE OR REPLACE VIEW session_features AS
SELECT *
FROM read_csv_auto('data/processed/session_features.csv', header = true);

-- Total number of sessions.
SELECT COUNT(*) AS total_sessions
FROM session_features;

-- Average and median duration, in seconds.
SELECT
    AVG(session_duration_seconds) AS average_duration_seconds,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY session_duration_seconds
    ) AS median_duration_seconds
FROM session_features;

-- Average event count and page-navigation depth per session.
SELECT
    AVG(event_count) AS average_events_per_session,
    AVG(navigation_depth) AS average_page_hits_per_session
FROM session_features;

-- Sessions and conversion rate by device category.
SELECT
    device_type,
    COUNT(*) AS sessions,
    AVG(CASE WHEN converted THEN 1.0 ELSE 0.0 END) AS conversion_rate
FROM session_features
GROUP BY device_type
ORDER BY sessions DESC;

-- Sessions by UTC session-start date.
SELECT
    session_date,
    COUNT(*) AS sessions
FROM session_features
GROUP BY session_date
ORDER BY session_date;

-- Overall observed conversion rate.
SELECT
    COUNT(*) AS total_sessions,
    SUM(CASE WHEN converted THEN 1 ELSE 0 END) AS converted_sessions,
    AVG(CASE WHEN converted THEN 1.0 ELSE 0.0 END) AS conversion_rate
FROM session_features;

-- Most common entry pages.
SELECT
    entry_page,
    COUNT(*) AS sessions
FROM session_features
WHERE entry_page IS NOT NULL
GROUP BY entry_page
ORDER BY sessions DESC
LIMIT 10;

-- Most common exit pages.
SELECT
    exit_page,
    COUNT(*) AS sessions
FROM session_features
WHERE exit_page IS NOT NULL
GROUP BY exit_page
ORDER BY sessions DESC
LIMIT 10;

-- Most common first event names.
SELECT
    first_event,
    COUNT(*) AS sessions
FROM session_features
GROUP BY first_event
ORDER BY sessions DESC
LIMIT 10;
