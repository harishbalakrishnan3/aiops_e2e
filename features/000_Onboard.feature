Feature: Onboard and Offboard testing
  # This feature tests onboard and offboard scenarios

  Scenario: Test offboard
    Given the tenant onboard state is ONBOARDED
    When perform a tenant offboard
    Then verify if the onboard status changes to NOT_ONBOARDED with a timeout of 2 minute(s)
    And wait for 1 minute

  Scenario: Test onboard
    Given the tenant onboard state is NOT_ONBOARDED
    When perform a tenant onboard
    Then verify if the onboard status changes to ONBOARDED with a timeout of 5 minute(s)

  Scenario: No Insights Present
    Given the insights are cleared
    Then verify no insight is present with a timeout of 2 minute(s)