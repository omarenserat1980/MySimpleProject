# Honda CONNECT App Manager

A safe GitHub-based manager for Honda CONNECT / Honda CONNECT Plus research and app packages.

## What it does
- Keeps a manifest of apps and official/vendor download sources.
- Checks whether an app is marked compatible with the target Honda CONNECT version.
- Downloads only explicitly configured public package URLs during a manual GitHub Actions run.
- Produces a SHA-256 manifest for downloaded files.
- Does **not** bypass Honda safety locks, DRM, authentication, or vehicle firmware security.

## Target
Honda NP1 2023 / Honda CONNECT.

## Important
A downloaded APK/package is not automatically installable on a Honda CONNECT head unit. Installation depends on the exact head-unit firmware and its supported package mechanism. Video playback should only be used when the vehicle is safely parked.

## GitHub Action
Use **Honda CONNECT App Manager** from Actions, choose an app ID, and run it manually.
