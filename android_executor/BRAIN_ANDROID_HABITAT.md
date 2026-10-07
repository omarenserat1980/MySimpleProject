# Brain Android Habitat v1

The Android Executor becomes the device body for Brain.

## Architecture

Brain V13/V14
-> Agent Gateway
-> redmi3-01
-> Brain Android Executor
-> Termux / Android APIs / Accessibility
-> device resources

## Cortex responsibilities

- represent local capabilities
- expose safe decisions to the UI
- show permission requirements
- keep execution and verification conceptually separate
- report device state back to Brain

## v1 scope

- Brain dashboard
- Cortex capability model
- constitution/policy
- existing Termux bridge
- existing Agent Gateway
- existing Executor service

## Not in v1

- automatic root
- bootloader unlocking
- ROM flashing
- unrestricted shell execution
- silent installation/removal of applications

Those operations require explicit, separately verified workflows.
