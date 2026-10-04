# Founder Identity Protection

## Purpose
Protect founder identity and other sensitive personal data from source control, CI logs, evidence artifacts, public pages, and outbound notifications.

## Rules
- The actual national identity number, passport number, bank-account identifier, payment destination, private email, or similar sensitive identifier MUST NOT be committed to this repository.
- Public code and evidence use opaque references such as `FOUNDER_IDENTITY_REF` and `FOUNDER_PAYMENT_DESTINATION_REF`.
- CI jobs MUST NOT print secret values or personal identifiers.
- Evidence records contain status, hashes, timestamps, and non-sensitive references only.
- Legal/estate workflows use an opaque identity reference and retrieve the underlying identity only from an authorized private store.
- Identity verification never authorizes a payment, contract, legal filing, or inheritance transfer by itself.
- Any future lawyer/estate handoff requires independent authority verification and an auditable human/legal handoff.

## Fail-closed behavior
If a workflow cannot prove that sensitive identity data is being handled through an approved private channel, it MUST block the affected operation rather than copying the data into source control, logs, artifacts, or email.

## Current public-repository status
The repository architecture uses opaque founder payment references and does not intentionally store the founder's actual identity value.
