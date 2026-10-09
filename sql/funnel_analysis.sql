-- Day 3 funnel analysis for the Digital Behavior Observatory
-- Expected source: data/processed/events_processed.csv and session_features.csv
-- SQL dialect: DuckDB-compatible SQL (read_csv_auto and simple aggregates)

CREATE OR REPLACE VIEW session_features AS
SELECT *
FROM read_csv_auto('data/processed/session_features.csv', header = true,
                  columns = {
                      session_id: 'VARCHAR',
                      user_id: 'VARCHAR',
                      source_session_id: 'VARCHAR',
                      session_start: 'TIMESTAMP',
                      session_end: 'TIMESTAMP',
                      event_count: 'BIGINT',
                      unique_event_count: 'BIGINT',
                      unique_page_count: 'BIGINT',
                      unique_action_count: 'BIGINT',
                      navigation_depth: 'BIGINT',
                      repeated_action_count: 'BIGINT',
                      first_event: 'VARCHAR',
                      last_event: 'VARCHAR',
                      device_type: 'VARCHAR',
                      platform: 'VARCHAR',
                      browser: 'VARCHAR',
                      transaction_count: 'BIGINT',
                      entry_page: 'VARCHAR',
                      exit_page: 'VARCHAR',
                      converted: 'BOOLEAN',
                      session_duration_seconds: 'DOUBLE',
                      events_per_minute: 'DOUBLE',
                      session_date: 'DATE',
                      hour: 'BIGINT',
                      day_of_week: 'BIGINT',
                      week: 'BIGINT',
                      month: 'BIGINT',
                      is_weekend: 'BOOLEAN',
                      time_of_day: 'VARCHAR'
                  });

CREATE OR REPLACE VIEW events_processed AS
SELECT *
FROM read_csv_auto('data/processed/events_processed.csv', header = true,
                  columns = {
                      user_id: 'VARCHAR',
                      source_session_id: 'VARCHAR',
                      event_date: 'VARCHAR',
                      hit_number: 'BIGINT',
                      event_type: 'VARCHAR',
                      page_path: 'VARCHAR',
                      event_category: 'VARCHAR',
                      event_action: 'VARCHAR',
                      event_label: 'VARCHAR',
                      hit_time_ms: 'BIGINT',
                      device_type: 'VARCHAR',
                      platform: 'VARCHAR',
                      browser: 'VARCHAR',
                      transactions: 'BIGINT',
                      session_start_timestamp: 'TIMESTAMP',
                      event_timestamp: 'TIMESTAMP',
                      session_id: 'VARCHAR',
                      source_event_date: 'VARCHAR',
                      hour: 'BIGINT',
                      day_of_week: 'BIGINT',
                      week: 'BIGINT',
                      month: 'BIGINT',
                      is_weekend: 'BOOLEAN',
                      time_of_day: 'VARCHAR',
                      event_name: 'VARCHAR'
                  });

-- Funnel stage counts for the natural journey: product discovery -> add to cart -> checkout -> purchase.
WITH funnel AS (
    SELECT
        session_id,
        MAX(CASE WHEN page_path LIKE '%google+redesign%' OR page_path = '/store.html' OR page_path = '/asearch.html' OR event_name IN ('Product Click', 'Quickview Click') THEN 1 ELSE 0 END) AS product_discovery,
        MAX(CASE WHEN event_name = 'Add to Cart' OR page_path = '/basket.html' THEN 1 ELSE 0 END) AS add_to_cart,
        MAX(CASE WHEN page_path IN ('/signin.html', '/myaccount.html?mode=billingaddress', '/myaccount.html?mode=vieworder', '/myaccount.html?mode=vieworderdetail') THEN 1 ELSE 0 END) AS checkout,
        MAX(CASE WHEN page_path = '/ordercompleted.html' OR transactions > 0 THEN 1 ELSE 0 END) AS purchase
    FROM events_processed
    GROUP BY session_id
)
SELECT
    SUM(product_discovery) AS sessions_product_discovery,
    SUM(add_to_cart) AS sessions_add_to_cart,
    SUM(checkout) AS sessions_checkout,
    SUM(purchase) AS sessions_purchase
FROM funnel;

-- Stage conversion: passed stage / previous stage.
WITH funnel AS (
    SELECT
        session_id,
        MAX(CASE WHEN page_path LIKE '%google+redesign%' OR page_path = '/store.html' OR page_path = '/asearch.html' OR event_name IN ('Product Click', 'Quickview Click') THEN 1 ELSE 0 END) AS product_discovery,
        MAX(CASE WHEN event_name = 'Add to Cart' OR page_path = '/basket.html' THEN 1 ELSE 0 END) AS add_to_cart,
        MAX(CASE WHEN page_path IN ('/signin.html', '/myaccount.html?mode=billingaddress', '/myaccount.html?mode=vieworder', '/myaccount.html?mode=vieworderdetail') THEN 1 ELSE 0 END) AS checkout,
        MAX(CASE WHEN page_path = '/ordercompleted.html' OR transactions > 0 THEN 1 ELSE 0 END) AS purchase
    FROM events_processed
    GROUP BY session_id
)
SELECT
    'product_discovery' AS stage,
    SUM(product_discovery) AS stage_count,
    CAST(SUM(product_discovery) AS DOUBLE) / COUNT(*) AS stage_conversion
FROM funnel
UNION ALL
SELECT
    'add_to_cart' AS stage,
    SUM(add_to_cart) AS stage_count,
    CAST(SUM(add_to_cart) AS DOUBLE) / SUM(product_discovery) AS stage_conversion
FROM funnel
UNION ALL
SELECT
    'checkout' AS stage,
    SUM(checkout) AS stage_count,
    CAST(SUM(checkout) AS DOUBLE) / SUM(add_to_cart) AS stage_conversion
FROM funnel
UNION ALL
SELECT
    'purchase' AS stage,
    SUM(purchase) AS stage_count,
    CAST(SUM(purchase) AS DOUBLE) / SUM(checkout) AS stage_conversion
FROM funnel;

-- Cumulative conversion toward the final purchase stage.
WITH funnel AS (
    SELECT
        session_id,
        MAX(CASE WHEN page_path LIKE '%google+redesign%' OR page_path = '/store.html' OR page_path = '/asearch.html' OR event_name IN ('Product Click', 'Quickview Click') THEN 1 ELSE 0 END) AS product_discovery,
        MAX(CASE WHEN event_name = 'Add to Cart' OR page_path = '/basket.html' THEN 1 ELSE 0 END) AS add_to_cart,
        MAX(CASE WHEN page_path IN ('/signin.html', '/myaccount.html?mode=billingaddress', '/myaccount.html?mode=vieworder', '/myaccount.html?mode=vieworderdetail') THEN 1 ELSE 0 END) AS checkout,
        MAX(CASE WHEN page_path = '/ordercompleted.html' OR transactions > 0 THEN 1 ELSE 0 END) AS purchase
    FROM events_processed
    GROUP BY session_id
)
SELECT
    'product_discovery' AS stage,
    SUM(product_discovery) AS stage_count,
    CAST(SUM(product_discovery) AS DOUBLE) / (SELECT COUNT(*) FROM session_features) AS cumulative_conversion
FROM funnel
UNION ALL
SELECT
    'add_to_cart' AS stage,
    SUM(add_to_cart) AS stage_count,
    CAST(SUM(add_to_cart) AS DOUBLE) / (SELECT COUNT(*) FROM session_features) AS cumulative_conversion
FROM funnel
UNION ALL
SELECT
    'checkout' AS stage,
    SUM(checkout) AS stage_count,
    CAST(SUM(checkout) AS DOUBLE) / (SELECT COUNT(*) FROM session_features) AS cumulative_conversion
FROM funnel
UNION ALL
SELECT
    'purchase' AS stage,
    SUM(purchase) AS stage_count,
    CAST(SUM(purchase) AS DOUBLE) / (SELECT COUNT(*) FROM session_features) AS cumulative_conversion
FROM funnel;

-- Drop-off counts and percentages for each funnel stage.
WITH funnel AS (
    SELECT
        session_id,
        MAX(CASE WHEN page_path LIKE '%google+redesign%' OR page_path = '/store.html' OR page_path = '/asearch.html' OR event_name IN ('Product Click', 'Quickview Click') THEN 1 ELSE 0 END) AS product_discovery,
        MAX(CASE WHEN event_name = 'Add to Cart' OR page_path = '/basket.html' THEN 1 ELSE 0 END) AS add_to_cart,
        MAX(CASE WHEN page_path IN ('/signin.html', '/myaccount.html?mode=billingaddress', '/myaccount.html?mode=vieworder', '/myaccount.html?mode=vieworderdetail') THEN 1 ELSE 0 END) AS checkout,
        MAX(CASE WHEN page_path = '/ordercompleted.html' OR transactions > 0 THEN 1 ELSE 0 END) AS purchase
    FROM events_processed
    GROUP BY session_id
)
SELECT
    'product_discovery' AS stage,
    SUM(product_discovery) AS stage_count,
    (SELECT COUNT(*) FROM session_features) - SUM(product_discovery) AS drop_off_count,
    ((SELECT COUNT(*) FROM session_features) - SUM(product_discovery)) / (SELECT COUNT(*) FROM session_features) AS drop_off_pct
FROM funnel
UNION ALL
SELECT
    'add_to_cart' AS stage,
    SUM(add_to_cart) AS stage_count,
    SUM(product_discovery) - SUM(add_to_cart) AS drop_off_count,
    (SUM(product_discovery) - SUM(add_to_cart)) / SUM(product_discovery) AS drop_off_pct
FROM funnel
UNION ALL
SELECT
    'checkout' AS stage,
    SUM(checkout) AS stage_count,
    SUM(add_to_cart) - SUM(checkout) AS drop_off_count,
    (SUM(add_to_cart) - SUM(checkout)) / SUM(add_to_cart) AS drop_off_pct
FROM funnel
UNION ALL
SELECT
    'purchase' AS stage,
    SUM(purchase) AS stage_count,
    SUM(checkout) - SUM(purchase) AS drop_off_count,
    (SUM(checkout) - SUM(purchase)) / SUM(checkout) AS drop_off_pct
FROM funnel;

-- Entry event distribution for the analyzed product journey.
SELECT
    first_event,
    COUNT(*) AS sessions,
    ROUND(CAST(COUNT(*) AS DOUBLE) / (SELECT COUNT(*) FROM session_features), 4) AS share_of_sessions
FROM session_features
GROUP BY first_event
ORDER BY sessions DESC;

-- Exit pages most commonly observed after a browsing session.
SELECT
    exit_page,
    COUNT(*) AS sessions,
    ROUND(CAST(COUNT(*) AS DOUBLE) / (SELECT COUNT(*) FROM session_features), 4) AS share_of_sessions
FROM session_features
WHERE exit_page IS NOT NULL
GROUP BY exit_page
ORDER BY sessions DESC
LIMIT 10;

-- Common transition pairs across events in ordered event sequences.
WITH ordered AS (
    SELECT
        session_id,
        hit_number,
        event_name,
        LAG(event_name) OVER (PARTITION BY session_id ORDER BY hit_number) AS previous_event
    FROM events_processed
)
SELECT
    previous_event AS previous_event,
    event_name AS next_event,
    COUNT(*) AS transition_count
FROM ordered
WHERE previous_event IS NOT NULL
GROUP BY previous_event, event_name
ORDER BY transition_count DESC
LIMIT 20;

-- Conversion by device type, a meaningful operational comparison.
SELECT
    device_type,
    COUNT(*) AS sessions,
    SUM(CASE WHEN converted THEN 1 ELSE 0 END) AS converted_sessions,
    ROUND(CAST(SUM(CASE WHEN converted THEN 1 ELSE 0 END) AS DOUBLE) / COUNT(*), 4) AS conversion_rate
FROM session_features
GROUP BY device_type
ORDER BY sessions DESC;
