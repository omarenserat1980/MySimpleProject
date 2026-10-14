# Bitcoin SHA-256 compression RTL prototype

This change adds a combinational SHA-256 compression function for one 512-bit block and a hosted Icarus Verilog test. The block is interpreted as sixteen big-endian 32-bit words; the input state is the eight standard SHA-256 chaining words.

## Verification gate
The test supplies the standard SHA-256 padding block for an empty message and the standard initial chaining state, then compares the compression output to the known SHA-256 empty-message digest. GitHub Actions retains the compile/simulation log.

## Scope limits
This is one compression block only. It is **not** a complete Bitcoin double-SHA-256 header/nonce scanner. It does not implement Bitcoin header construction, nonce iteration, target comparison, networking, pool submission, accepted shares, or payout accounting. RTL simulation is not FPGA execution, ASIC fabrication, or proof of mining revenue. Those require separate independently verifiable gates.
