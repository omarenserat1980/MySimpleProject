// Double-SHA-256 primitive for a fixed 32-byte message.
// This is a deterministic SHA256d building block, not a Bitcoin header miner.
module brain_sha256d_256 (
    input  logic [255:0] message_i,
    output logic [255:0] digest_o
);
    localparam logic [255:0] SHA256_IV = {
        32'h6a09e667, 32'hbb67ae85, 32'h3c6ef372, 32'ha54ff53a,
        32'h510e527f, 32'h9b05688c, 32'h1f83d9ab, 32'h5be0cd19
    };

    logic [511:0] first_block;
    logic [255:0] first_digest;
    logic [511:0] second_block;

    assign first_block  = {message_i, 8'h80, 184'b0, 64'd256};
    assign second_block = {first_digest, 8'h80, 184'b0, 64'd256};

    brain_sha256_compress first_hash (
        .block_i(first_block),
        .state_i(SHA256_IV),
        .state_o(first_digest)
    );

    brain_sha256_compress second_hash (
        .block_i(second_block),
        .state_i(SHA256_IV),
        .state_o(digest_o)
    );
endmodule
