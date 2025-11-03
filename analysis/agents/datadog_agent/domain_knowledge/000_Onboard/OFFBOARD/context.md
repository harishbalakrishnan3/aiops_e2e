## Expected functional flow

When offboard is triggered, the following is expected to happen:
1. Subscriber configs are deleted
2. Data store is deleted
3. FMCs are offboarded through a statemachine
4. Insights are deleted or marked as inactive
5. Apps are onboarded

An offboard is typically followed by an onboard. Summarize the observation only for the offboard scenario.