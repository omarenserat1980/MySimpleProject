# Brain AI Model Routing

Brain AI now has a provider registry and deterministic fallback layer.

## Routing contract

- Providers expose `respond()` and optionally `status()`.
- A default provider is used when configured.
- Providers can advertise capabilities such as `multimodal`.
- A request may explicitly select a capability.
- If the selected provider fails, Brain tries registered fallback providers.
- Successful fallback responses include `route_reason=fallback` and provider errors encountered before recovery.
- If every provider fails, Brain returns `ALL_MODEL_PROVIDERS_FAILED` instead of claiming success.

This keeps model choice replaceable and provides a stable integration point for later multimodal providers without exposing credentials to the client.
