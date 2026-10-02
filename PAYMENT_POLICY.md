# BRAIN Payment Policy v1

## Principle
Payment receipt and payment verification are separate events.

## Lifecycle
PAYMENT_PENDING → PAYMENT_RECEIVED → PAYMENT_VERIFICATION → PAYMENT_VERIFIED → REVENUE_REALIZED

Failure exits include FAILED, REVERSED, REFUNDED, and DISPUTED.

## Evidence
Verification may use provider confirmation, verified bank/settlement evidence, or another approved evidence source. A customer-uploaded receipt can be an input for review but is not automatically proof of settlement.

## Payment adapters
Each adapter defines provider, method, currency support, fees, transaction ID, webhook/confirmation mechanism, settlement state, refund capability, and evidence requirements.

## Security
Brain must not store card PAN, CVV, or equivalent sensitive payment credentials. Tokenization/provider-hosted collection should be used where applicable.

## Reconciliation
A verified payment must reconcile to customer/order, amount, currency, transaction identifier, and expected invoice/quote before revenue recognition.
