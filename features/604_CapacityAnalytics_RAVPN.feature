Feature: Capacity Analytics RAVPN
  # This feature contains the sanity test for forecast insight generation of the RAVPN metric
  # Both active and inactive RAVPN tunnel metrics are backfilled with appropriate data
  # Capacity analytics workflow is triggered and insight generation is verified
  Background:
    Given the tenant onboard state is ONBOARD_SUCCESS

  Scenario: Test forecast insight generation for RAVPN metric
    Then backfill metrics for a suitable device over 2160 hour(s)
      | metric_name            | label_values                              | start_value | end_value | start_spike_minute | spike_duration_minutes | seasonality_period_hours | amplitude |
      | vpn                    | vpn=active_ravpn_tunnels                  | 5           | 100       | 0                  | 129600                 | 24                       | 9.25      |
      | vpn                    | vpn=inactive_ravpn_tunnels                | 5           | 100       | 0                  | 129600                 | 24                       | 9.25      |
    Then wait for 5 minutes
    Then trigger capacity analytics workflow
    Then verify if an RAVPN_MAX_SESSIONS_BREACH_FORECAST insight with state ACTIVE is created with a timeout of 60 minute(s)
