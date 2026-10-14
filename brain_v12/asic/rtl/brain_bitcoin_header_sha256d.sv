// SHA256d of an 80-byte serialized Bitcoin block header.
// header_i is the exact 80-byte wire serialization, first byte at [639:632].
// digest_o is the raw SHA-256 digest in big-endian word order; Bitcoin's
// displayed block hash reverses the digest bytes.
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
    logic [255:0] first_digest;
    logic [511:0] second_hash_block;

    assign block0 = header_i[639:128];
    // Remaining 16 bytes + 0x80 + 39 zero bytes + 640-bit length.
    assign block1 = {header_i[127:0], 8'h80, 312'b0, 64'd640};
    // SHA-256 of the first 256-bit digest: exactly one final compression.
    assign second_hash_block = {first_digest, 8'h80, 184'b0, 64'd256};

    brain_sha256_compress compress0 (
        .block_i(block0), .state_i(SHA256_IV), .state_o(state1)
    );
    brain_sha256_compress compress1 (
        .block_i(block1), .state_i(state1), .state_o(first_digest)
    );
    brain_sha256_compress compress2 (
        .block_i(second_hash_block), .state_i(SHA256_IV), .state_o(digest_o)
    );
endmodule
