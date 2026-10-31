# Brain / HeadSwap integration record

- Upstream: https://github.com/YegorkaPomidorka/headswap
- Upstream project license: GPL-3.0; `pc-headunit/proto/*.proto` has separate AGPL-3.0 provenance per upstream README.
- Integration strategy: keep HeadSwap as an isolated upstream project under `third_party/headswap`; communicate through a narrow Brain adapter in a later stage.
- Branding overlay: `scripts/apply_brain_headswap_branding.py`; changes only the app label and debug application ID suffix `.brain`. It does not alter protocol code, release signing, or permissions.
- Do not treat a successful APK build as vehicle compatibility proof. The upstream README reports selected Chinese-market head units, including Honda Vezel 2022–2024, but that does not verify a different Honda model/market/firmware.
- Android Auto head-unit server must be enabled manually by the user. No automated settings changes are attempted.
- Debug APK is intended for controlled testing and side-by-side installation. It is not a production release.
