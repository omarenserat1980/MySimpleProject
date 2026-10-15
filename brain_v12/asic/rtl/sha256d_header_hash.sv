// Bitcoin 80-byte header double-SHA256 datapath, combinational reference RTL.
// header_prefix = serialized header bytes 0..63 in wire order.
// header_tail = serialized header bytes 64..75 in bits [127:32]; nonce is supplied
// separately and inserted as four little-endian wire bytes.
// Output is the raw SHA-256 digest byte order (not the reversed block-explorer display).
// No nonce search, target compare, pool/network, or transaction validation here.
module sha256d_header_hash (
  input  logic [511:0] header_prefix,
  input  logic [127:0] header_tail,
  input  logic [31:0] nonce,
  output logic [255:0] digest
);
  localparam logic [255:0] IV = {
    32'h6a09e667,32'hbb67ae85,32'h3c6ef372,32'ha54ff53a,
    32'h510e527f,32'h9b05688c,32'h1f83d9ab,32'h5be0cd19
  };
  logic [255:0] state1, state2;
  logic [511:0] block2, block3;

  sha256_compress first_hash(
    .block(header_prefix), .state_in(IV), .state_out(state1)
  );

  // Remaining 16 bytes of the 80-byte header, followed by SHA-256 padding.
  // The final four serialized header bytes encode nonce least-significant byte first.
  always_comb begin
    block2 = {header_tail[127:32],
              nonce[7:0], nonce[15:8], nonce[23:16], nonce[31:24],
              8'h80, 312'b0, 64'd640};
    block3 = {state2, 8'h80, 184'b0, 64'd256};
  end

  sha256_compress second_hash(
    .block(block2), .state_in(state1), .state_out(state2)
  );
  sha256_compress final_hash(
    .block(block3), .state_in(IV), .state_out(digest)
  );
endmodule
