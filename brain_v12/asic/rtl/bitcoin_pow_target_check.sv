// Compare a raw SHA-256 digest against a Bitcoin-style target.
// raw_digest is the 32-byte SHA digest in conventional printed hex byte order.
// Bitcoin PoW interprets the digest as a little-endian integer, so bytes are reversed
// before unsigned comparison with target_be (the target as a conventional 256-bit integer).
module bitcoin_pow_target_check (
  input  logic [255:0] raw_digest,
  input  logic [255:0] target_be,
  output logic [255:0] digest_numeric,
  output logic         meets_target
);
  integer i;
  always_comb begin
    for (i=0; i<32; i=i+1)
      digest_numeric[255-(i*8) -: 8] = raw_digest[i*8 +: 8];
    meets_target = (digest_numeric <= target_be);
  end
endmodule
