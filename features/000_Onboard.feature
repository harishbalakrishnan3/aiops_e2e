Feature: Onboard and Offboard testing
  # This feature tests onboard and offboard scenarios

  Scenario: Test offboard
    Given the tenant onboard state is ONBOARD_SUCCESS
    When perform a tenant offboard
    Then verify if the onboard status changes to OFFBOARD_SUCCESS with a timeout of 2 minute(s)
    And wait for 1 minute

  Scenario: Test onboard
    Given the tenant onboard state is OFFBOARD_SUCCESS
    When perform a tenant onboard
    Then verify if the onboard status changes to ONBOARD_SUCCESS with a timeout of 5 minute(s)

  Scenario: No Insights Present
    Given the insights are cleared
    Then verify no insight is present with a timeout of 2 minute(s)
