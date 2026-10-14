// SHA256d of an 80-byte serialized Bitcoin block header.
// header_i is the exact 80-byte wire serialization, first byte at [639:632].
// digest_o is the SHA-256 digest in conventional big-endian word order.
// Bitcoin block explorers display this digest with its bytes reversed.
module brain_bitcoin_header_sha256d (
    input  logic [639:0] header_i,
    output logic [255:0] digest_o
);
    localparam logic [255:0] SHA256_IV = {
        32'h6a09e667, 32'hbb67ae85, 32'h3c6ef372, 32'ha54ff53a,
        32'h510e527f, 32'h9b05688c, 32'h1f83d9ab, 32'h5be0cd19
    };

    logic [511:0] block0;
    logic [511:0] block1;
    logic [255:0] state1;
    logic [255:0] state2;
    logic [511:0] block2;
    logic [255:0] hash1;
    logic [511:0] block3;

    assign block0 = header_i[639:128];
    // 16 remaining header bytes + SHA padding + 64-bit message length (640 bits).
    assign block1 = {header_i[127:0], 8'h80, 312'b0, 64'd640};
    // SHA-256 of the first 256-bit digest.
    assign block2 = {state2, 8'h80, 184'b0, 64'd256};
    // SHA-256 of the second 256-bit digest.
    assign block3 = {hash1, 8'h80, 184'b0, 64'd256};

    brain_sha256_compress compress0 (
        .block_i(block0), .state_i(SHA256_IV), .state_o(state1)
    );
    brain_sha256_compress compress1 (
        .block_i(block1), .state_i(state1), .state_o(state2)
    );
    brain_sha256_compress compress2 (
        .block_i(block2), .state_i(SHA256_IV), .state_o(hash1)
    );
    brain_sha256_compress compress3 (
        .block_i(block3), .state_i(SHA256_IV), .state_o(digest_o)
    );
endmodule
