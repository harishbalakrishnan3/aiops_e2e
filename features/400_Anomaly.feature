Feature: Testing Anomaly Detection

  Scenario: Testing Anomaly Detection for Connection Stats
    Given the tenant onboard state is ONBOARDED
    Then backfill metrics for a suitable device over 792 hour(s)
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes | seasonality_period_hours |
      | conn_stats             | conn_stats=connection, description=in_use | 15          | 200       | 0                  | 47520                  | 6                        |
