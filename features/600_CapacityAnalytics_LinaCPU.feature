Feature: Capacity Analytics
  # This feature contains the sanity test for forecast insight generation of the lina CPU metric
  # The relevant metric is backfilled with appropriate data
  # Forecast workflow is triggered and insight generation is verified
  Background:
    Given the tenant onboard state is ONBOARD_SUCCESS

  Scenario: Test forecast insight generation for Lina CPU metric
    Then backfill metrics for a suitable device over 2160 hour(s)
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes | seasonality_period_hours | amplitude |
      | cpu                    | cpu=lina_dp_avg                           | 15.25       | 60.72     | 0                  | 129600                 | 24                       | 9.25      |
    Then wait for 5 minutes
    Then trigger capacity analytics workflow
    Then verify if an CPU_LINA_THRESHOLD_FORECAST_BREACH insight with state ACTIVE is created with a timeout of 60 minute(s)