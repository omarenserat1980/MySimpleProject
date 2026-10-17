# BRAIN-ASIC-001 Physical Asset Register

The register at `physical_asset_register.json` starts empty intentionally. Do not add fictional donor, chip, serial, photo, valuation, or sale records.

Validate locally with:
```bash
python3 brain_v12/asic/unit_001/physical_asset_register.py
python3 -m unittest brain_v12.asic.unit_001.test_physical_asset_register -v
```

Only add an item after it is actually received. `PHYSICAL_OBSERVED` requires a receipt date and photo evidence URLs. Market valuation must be sourced and dated, and it is distinct from asking price and revenue. Revenue requires transaction/payment evidence. The tool does not buy, sell, contact donors, or enable financial execution.
