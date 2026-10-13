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
