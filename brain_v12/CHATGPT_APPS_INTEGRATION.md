# ChatGPT Apps integration — implementation and release boundary

## What this branch adds

- An MCP Apps widget resource at ui://widget/electronic-brain-chat.html.
- The brain.open_chat_widget render tool with both the standard _meta.ui.resourceUri and ChatGPT-compatible openai/outputTemplate metadata.
- resources/list and resources/read support on the existing /mcp JSON-RPC endpoint.
- Persistent chat-session creation and message tools used by the widget.
- Idempotency for repeated session-creation keys and message request IDs.
- An Arabic RTL widget with sequential ع cycles, a five-cycle maximum, pause/resume/stop controls, and visible error handling.
- Tests for resource discovery, widget metadata, session idempotency, message idempotency, and safe unapproved chat behavior.

## Important release blocker: ChatGPT authentication

The existing MCP wrapper protects /mcp with the static BRAIN_MCP_TOKEN bearer value. That is not a completed ChatGPT Apps authentication integration: ChatGPT's Apps SDK OAuth flow expects an OAuth 2.1 authorization-code flow with PKCE, protected-resource metadata, authorization-server discovery, dynamic client registration, and access-token validation. ChatGPT does not support supplying an arbitrary custom API key as a substitute for that flow.

This branch deliberately does not remove the existing token check, make the MCP endpoint anonymous, or invent an identity provider. The widget source and MCP resource/tool contract can be reviewed and tested, but connecting it to ChatGPT is blocked until an actual OAuth identity provider is configured and implemented.

## Required before ChatGPT can connect

1. Choose/configure an OAuth 2.1 identity provider that supports authorization-code + PKCE (S256) and dynamic client registration.
2. Register the ChatGPT redirect URIs required by the current OpenAI Apps SDK documentation.
3. Publish /.well-known/oauth-protected-resource on the MCP resource origin and OAuth authorization-server discovery metadata on the identity-provider origin.
4. Validate token signature, issuer, audience, expiry, and scopes on every MCP request; include the appropriate WWW-Authenticate challenge and tool-level securitySchemes metadata.
5. Store credentials only in server-side environment variables or the identity provider; never in widget HTML.
6. Deploy the reviewed branch to a stable HTTPS endpoint, then add that endpoint as an app in ChatGPT Developer Mode and test tool discovery, widget rendering, mobile layout, authentication, and a complete cycle.
7. Submit for review only after the real ChatGPT client flow and security checks pass.

## Validation boundary

Repository unit tests prove local protocol/tool behavior only. They do not prove that ChatGPT has registered this app, completed OAuth, rendered the widget, or can reach the deployed MCP server. Do not claim production integration until those checks are performed against ChatGPT itself.