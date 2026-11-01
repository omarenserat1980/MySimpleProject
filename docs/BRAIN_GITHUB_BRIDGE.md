# BRAIN GitHub Bridge

This helper uses the user's existing GitHub CLI login on the authorized Termux device.
It does not store, print, create, or transmit credentials.

## Commands

- \`bash tools/brain_github_bridge.sh status\` — show the authenticated identity and repository write access.
- \`bash tools/brain_github_bridge.sh select-owner\` — select the repository owner account in GitHub CLI and configure Git credential integration.
- \`bash tools/brain_github_bridge.sh push\` — push only the clean \`brain/honda-android-network-sqlite\` branch.

The push command refuses to push \`main\`, any other branch, or a dirty worktree.
It cannot grant permissions to the ChatGPT GitHub integration or change GitHub App installation permissions. Those permissions remain controlled by the GitHub App owner and repository owner.

## Safety model

- Uses the GitHub CLI credential store already configured by the user.
- Verifies the authenticated GitHub username and repository permissions through the GitHub API.
- Never requests or echoes a token.
- Push is restricted to one named development branch.
- Does not merge or modify \`main\`.
