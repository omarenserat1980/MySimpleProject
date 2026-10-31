# Android foreground service classification

The BRAIN Phone Server is a user-started, loopback-only HTTP companion endpoint. It binds exclusively to 127.0.0.1 and is not a general data synchronization worker or a LAN server.

For Android 14+ the service declares the `specialUse` foreground-service type and describes the concrete local-only use case through `PROPERTY_SPECIAL_USE_FGS_SUBTYPE`. This avoids misclassifying a persistent local bridge as `dataSync`; Android 15 applies a six-hour-per-24-hour background limit to `dataSync` and `mediaProcessing` foreground services.

If this app is submitted to Google Play, the developer must also declare and justify this special-use foreground-service case in Play Console. Sideloaded builds do not complete that Play review step.
