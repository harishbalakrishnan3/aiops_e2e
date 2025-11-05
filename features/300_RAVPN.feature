Feature: Testing RA-VPN forecasting
  # This feature tests if the desired insights are created for various RA-VPN forecasting scenarios

  Scenario: Testing RA-VPN forecasting
    Given the tenant onboard state is ONBOARD_SUCCESS
    When backfill RAVPN metrics for a suitable device
    And trigger the RAVPN forecasting workflow
    Then verify if an RAVPN_MAX_SESSIONS_BREACH_FORECAST insight with state ACTIVE is created with a timeout of 40 minute(s)