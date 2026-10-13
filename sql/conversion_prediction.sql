WITH session_model_input AS (
    SELECT
        s.session_id,
        s.user_id,
        s.device_type,
        s.platform,
        s.browser,
        s.time_of_day,
        s.event_count,
        s.navigation_depth,
        s.unique_action_count,
        s.session_duration_seconds,
        s.events_per_minute,
        s.converted,
        u.return_frequency,
        u.events_per_session,
        u.avg_navigation_depth
    FROM session_features s
    LEFT JOIN user_behavior_features u
        ON s.user_id = u.user_id
)
SELECT
    device_type,
    COUNT(*) AS sessions,
    AVG(CAST(converted AS INT)) AS conversion_rate,
    AVG(event_count) AS avg_event_count,
    AVG(navigation_depth) AS avg_navigation_depth,
    AVG(return_frequency) AS avg_return_frequency
FROM session_model_input
GROUP BY device_type
ORDER BY conversion_rate DESC;

WITH conversion_by_time AS (
    SELECT
        s.time_of_day,
        s.converted
    FROM session_features s
),
conversion_summary AS (
    SELECT
        time_of_day,
        COUNT(*) AS sessions,
        AVG(CAST(converted AS INT)) AS conversion_rate
    FROM conversion_by_time
    GROUP BY time_of_day
)
SELECT *
FROM conversion_summary
ORDER BY conversion_rate DESC;
