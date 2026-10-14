// Bitcoin proof-of-work target comparison.
// digest_i is the raw SHA-256d output (big-endian digest bytes).
// Bitcoin interprets the digest as a little-endian 256-bit integer, so reverse
// the bytes before comparing against target_i (numeric big-endian target).
module brain_bitcoin_target_check (
    input  logic [255:0] digest_i,
    input  logic [255:0] target_i,
    output logic [255:0] hash_value_o,
    output logic         meets_target_o
);
    genvar i;
    generate
        for (i = 0; i < 32; i = i + 1) begin : reverse_digest_bytes
            assign hash_value_o[255-(i*8) -: 8] = digest_i[(i*8) +: 8];
        end
    endgenerate

    assign meets_target_o = (hash_value_o <= target_i);
endmodule
