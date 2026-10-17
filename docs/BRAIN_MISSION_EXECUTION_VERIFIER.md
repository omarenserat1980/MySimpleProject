# Brain Mission Execution Verifier

Runs one authorized Android capability task through the Brain device bridge and verifies the returned result. It never accepts enqueue success as execution proof: only COMPLETED is success.

Usage in the user's Termux environment:
`bash tools/brain_verify_android_mission.sh`

The script uses the existing local Brain runtime and environment variables; it does not print secret values.
