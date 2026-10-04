# BRAIN Originals — Launch Gate

## What is live in source
Three original browser games are included:
- BRAIN: Neon Rift — $4.99
- BRAIN: Last Light — $6.99
- BRAIN: Drift Circuit — $7.99

Store: games-store.html
Playable builds: games/*.html
Checkout API: /api/games/checkout
Webhook: /api/games/webhook
Delivery verification: /api/games/orders/{order_id}/delivery?token=...

## Financial fail-closed rule
The store returns 503 PAYMENT_PROVIDER_NOT_CONFIGURED unless both are present on the server:
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET

Never place either secret in HTML, Git, chat, or client-side JavaScript.

## Required server configuration
Set:
- BRAIN_PUBLIC_ORIGIN=https://omarenserat1980.github.io/MySimpleProject
- STRIPE_SECRET_KEY=<merchant secret>
- STRIPE_WEBHOOK_SECRET=<webhook signing secret>

The backend must be reachable over HTTPS and expose:
- POST /api/games/checkout
- POST /api/games/webhook

Configure the Stripe webhook endpoint to the backend webhook URL and subscribe to checkout.session.completed.

## Purchase proof
A purchase is considered paid only after:
1. Stripe Checkout reports payment as paid.
2. The signed Stripe webhook is accepted.
3. Order amount and currency match the server catalog.
4. The order transitions to PAID.
5. The delivery token is validated.
6. Delivery is recorded as DELIVERED.

BRAIN must never mark revenue realized from a browser redirect alone.

## Current blocker
GitHub Pages can publish the storefront but cannot run the FastAPI checkout API. A real purchase therefore requires a running HTTPS backend plus a merchant account. This is an infrastructure/credential requirement, not a missing storefront feature.