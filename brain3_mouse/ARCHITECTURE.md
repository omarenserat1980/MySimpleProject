# Brain 3 architecture boundary

```text
Brain 3
  └── Mouse (local GitHub API emulator)
       ├── In-memory repository catalogue
       ├── In-memory issue tracker
       ├── Simulated branches and workflow list
       └── Local health endpoint
```

Mouse is a development/test adapter, not a real GitHub client. It never proxies to GitHub and does not run GitHub Actions. No Render adapter exists in this Brain 3 package. The default network listener is loopback-only. Its health response is an emulator status only, never a claim that Brain 3 has production access or is ready for deployment.

Future expansion must keep the provider boundary explicit: if a real provider is ever added, it must be a separate adapter behind an explicit opt-in; it must not silently replace Mouse or call Render.
