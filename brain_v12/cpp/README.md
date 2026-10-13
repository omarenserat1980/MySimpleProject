# C++ Family Growth Simulator

This is a software-only simulation of the Electronic Brain virtual family. It creates no real people, contacts no external services, and performs no real-world matchmaking, marriage, or reproduction.

## Build and run

From the repository root, with a C++17 compiler:

\`\`\`sh
g++ -std=c++17 -Wall -Wextra -Werror -pedantic brain_v12/cpp/family_simulator.cpp brain_v12/cpp/test_family_simulator.cpp -o /tmp/family-simulator-test
/tmp/family-simulator-test
\`\`\`

Expected output: \`family simulator checks passed; descendants=2\`.

## Behavior and safeguards

- Suggests unrelated, adult, unmarried candidates as possible friends; suggestions do not create a relationship.
- Friendship and simulated marriage require both adults to consent.
- Marriage requires a prior mutual friendship and blocks known shared ancestry.
- Simulated descendants are created only for an already-married pair after both explicitly consent.
- Each request is capped at eight simulated children.
- The simulation is in-memory only. It does not persist a real family tree or contact people.

## Dedicated birth-cycle thread

`BirthThread` emits a virtual birth-cycle event on a dedicated `std::thread` every 90 seconds by default. Its callback runs on that worker thread; the callback is where an application can process an eligible couple's simulated birth. The owner must ensure the callback safely synchronizes access to shared family state. The worker can be stopped promptly and is stopped by its destructor. Tests use a short interval to verify cycle delivery and shutdown without waiting 90 seconds.

Build and run the worker test:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread brain_v12/cpp/birth_thread.cpp brain_v12/cpp/test_birth_thread.cpp -o /tmp/birth-thread-test
/tmp/birth-thread-test
```

The worker does not independently select couples or mutate the family tree: the supplied callback owns that operation and must preserve mutual consent and thread safety. This avoids silently creating descendants for couples that have not opted in.

## Persistent child memory

`FamilyMemoryStore` appends each virtual child's identity, name, both parent IDs, and birth-cycle number to a file, then can restore the records after process restart. It rejects duplicate child IDs and protects in-process access with a mutex. The caller must choose a path on genuinely persistent writable storage and call `restore()` during worker startup before processing new events; an ephemeral container filesystem does not guarantee survival across redeploys.

Build and run its test:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread brain_v12/cpp/family_memory_store.cpp brain_v12/cpp/test_family_memory_store.cpp -o /tmp/family-memory-test
/tmp/family-memory-test
```

This is a reusable memory component, not proof that the deployed cloud worker currently uses it. Production activation requires an authorized deployment and a runtime read-back check.
