# Stratum V1 protocol foundation

This module adds a testable, fail-closed JSON-RPC protocol state machine. It models subscribe, authorize, difficulty/job notifications, share-request formatting, and pool responses without opening a network connection.

## Scope and current gate
- Protocol messages and request/response correlation: implemented.
- Pool socket/TLS transport and endpoint configuration: not implemented.
- Complete coinbase/extranonce/merkle-root/header assembly: not implemented.
- SHA-256d target comparison and nonce search over valid pool work: not implemented.
- Accepted-share responses can only be recorded from protocol fixtures until a real transport is separately implemented and configured.
- Wallet access and payout verification: not implemented.

Never store a pool password in source control or logs. Configure it through a secret manager/environment integration when transport is implemented. Use a pool account/worker credential, not a wallet private key.

## Truthful evidence
A successful unit test proves protocol-state logic against test messages. It does not prove a pool connection, real work, accepted shares, mining revenue, or an on-chain payout.
