# C++ Family Growth Simulator

This is a software-only simulation of the Electronic Brain virtual family. It creates no real people, contacts no external services, and performs no real-world matchmaking, marriage, or reproduction.

## Build and run

From the repository root, with a C++17 compiler:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -pedantic brain_v12/cpp/family_simulator.cpp brain_v12/cpp/test_family_simulator.cpp -o /tmp/family-simulator-test
/tmp/family-simulator-test
```

Expected output: `family simulator checks passed; descendants=2`.

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

## Persistent child memory

`FamilyMemoryStore` appends each virtual child's identity, name, both parent IDs, and birth-cycle number to a file, then can restore the records after process restart. It rejects duplicate child IDs and protects in-process access with a mutex. The caller must choose a path on genuinely persistent writable storage and call `restore()` during worker startup before processing new events; an ephemeral container filesystem does not guarantee survival across redeploys.

Build and run its test:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread brain_v12/cpp/family_memory_store.cpp brain_v12/cpp/test_family_memory_store.cpp -o /tmp/family-memory-test
/tmp/family-memory-test
```

## Family cloud worker harness

`FamilyCloudWorker` restores the file-backed memory before starting the dedicated timer thread. Every cycle (90 seconds by default), it records one virtual descendant for each registered pair only when both consent flags are true and a required eligibility callback returns true. The callback is the integration point for current Brain family-policy checks such as adult status, simulated marriage, and prohibited-kinship rules. The worker refuses to start without a callback and fails closed if that callback throws; a false result skips that pair for the cycle. Tests cover missing policy, ineligible pairs, consent gating, memory recovery, and write errors.

Build and run:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread brain_v12/cpp/birth_thread.cpp brain_v12/cpp/family_memory_store.cpp brain_v12/cpp/family_cloud_worker.cpp brain_v12/cpp/test_family_cloud_worker.cpp -o /tmp/family-cloud-worker-test
/tmp/family-cloud-worker-test
```

This worker harness is source code in the open draft PR, not an activated cloud process. The test's eligibility callback is only a stand-in, not a production family-policy integration. To retain memories across container replacement, configure its memory path to a storage location that is already persistent in the deployment environment; no such runtime configuration or production activation is asserted here.
