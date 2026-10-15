# Brain Phone Base: real local measurements

This module advances from simulated resource values to read-only measurements
collected by the Python process running on the phone/Termux host.

## Run on the Android phone

From the repository root in Termux:

```sh
python -m brain_phone_base.android_real_measurement --output evidence/phone-real-measurement.json
python -m unittest brain_phone_base.test_android_real_measurement -v
```

The JSON is written locally. It records CPU logical count, memory values from
`/proc/meminfo`, home-filesystem usage, runtime metadata, and Android properties
when `getprop` is available. Missing values remain null rather than being
invented. The collector deliberately does not query IMEI, serial number, account
tokens, or other unique identifiers.

## Evidence semantics and safety gates

- `local_measurement_unattested` means the local process recorded the values.
  It is **not** an independent proof of device identity, integrity, or truth.
- The collector makes no network requests and does not register or activate a node.
- `node_gate.trusted`, `active`, and `activation_allowed` remain false.
- Mining and mining-pool contact remain disabled.
- Do not promote the node until a separate verifier validates device identity and
  evidence, and a human explicitly approves activation.

A successful unit test proves the collector's software contract on the test host;
it does not prove that measurements have been captured from a physical Android
phone. The output file from a real phone run is required for that next claim.
