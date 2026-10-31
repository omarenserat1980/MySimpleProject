# Brain / HeadSwap integration record

- Upstream: https://github.com/YegorkaPomidorka/headswap
- Upstream project license: GPL-3.0; `pc-headunit/proto/*.proto` has separate AGPL-3.0 provenance per upstream README.
- Integration strategy: keep HeadSwap as an isolated upstream project under `third_party/headswap`; communicate through a narrow Brain adapter in a later stage.
- Branding overlay: `scripts/apply_brain_headswap_branding.py`; changes only the app label and debug application ID suffix `.brain`. It does not alter protocol code, release signing, or permissions.
- Do not treat a successful APK build as vehicle compatibility proof. The upstream README reports selected Chinese-market head units, including Honda Vezel 2022–2024, but that does not verify a different Honda model/market/firmware.
- Android Auto head-unit server must be enabled manually by the user. No automated settings changes are attempted.
- Debug APK is intended for controlled testing and side-by-side installation. It is not a production release.


## Android Auto TLS test credentials

- HeadSwap upstream README documents that the Android Auto head-unit certificate is intentionally not shipped in its source tree and names the JVC Kenwood pair from opencardev/aasdk as a supported source.
- CI fetches cert/headunit.crt and cert/headunit.key from AASDK commit 9bf6adf933665dee26532201719fac14a047ccf1 into the ignored/generated path android/app/src/main/assets/aa/jvc/.
- AASDK cert/README.md describes this default JVC certificate/key as publicly available and not confidential. The AASDK project is GPL-3.0; preserve its notices when redistributing derived source/assets.
- The workflow validates PEM parsing and verifies that the certificate public key matches the private key before Gradle runs. The key is a published test credential, not a production/private user key. It is fetched at build time and is not committed to this repository.
- This only enables the Android Auto TLS test path to be exercised. It does not establish that Google services, the phone, or a particular vehicle/head unit will accept the handshake, nor does it prove physical projection compatibility.
