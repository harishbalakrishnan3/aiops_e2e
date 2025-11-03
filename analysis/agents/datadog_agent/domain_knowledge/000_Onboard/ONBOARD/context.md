## Expected functional flow

When onboard is triggered, the following is expected to happen:
1. Onboard readiness is evaluated by checking if the tenant has a cdFMC
2. Data store is initialized
3. FMCs are onboarded through a statemachine
4. Data store migration is triggered
5. Module settings are saved and the metrics generator is notified of the same
6. Apps are onboarded

If any of the first 5 steps fail, then primary rollback is triggered. If it fails on the 6th step, then AIOps is partially onboarded.