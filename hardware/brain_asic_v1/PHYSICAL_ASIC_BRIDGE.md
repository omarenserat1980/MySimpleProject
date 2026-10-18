# Brain Physical ASIC Bridge

This read-only agent connects a user-owned cgminer-compatible ASIC on the private LAN to Brain Cloud. It does not configure pools, control firmware, start/stop miners, or request payouts.

## Status and proof boundary
- The cloud worker coordinates; it is not physical silicon.
- The agent collects telemetry from a real device API on the owner's private LAN.
- A report is `LIVE_DEVICE_TELEMETRY`, not proof of silicon provenance, accepted pool work, or revenue.
- Brain must enroll a unique device ID and validate a fresh challenge, HMAC, timestamp, and replay protection before assigning `PHYSICAL_ASIC`.

## Run on a trusted machine on the same LAN
Enable the miner's read-only cgminer-compatible API on the private LAN only; never expose TCP/4028 publicly.

```bash
export BRAIN_ASIC_HOST=192.168.1.50
export BRAIN_ASIC_PORT=4028
export BRAIN_ASIC_DEVICE_ID=brain-asic-owner-01
python3 tools/brain_physical_asic_agent.py
```

For cloud delivery, set `BRAIN_ASIC_INGEST_URL` to the HTTPS ingestion endpoint actually configured in Brain and `BRAIN_ASIC_HMAC_KEY` to a unique random key of at least 32 bytes. The endpoint must independently validate HMAC, freshness, enrollment and replay protection. No ingest endpoint is assumed or invented.

## Security
- Literal private IPv4 address only; no LAN scanning or hostnames.
- Read-only API request only.
- Cloud delivery requires HTTPS and HMAC.
- Secrets are not printed. Do not expose the miner API or shared secrets publicly.
