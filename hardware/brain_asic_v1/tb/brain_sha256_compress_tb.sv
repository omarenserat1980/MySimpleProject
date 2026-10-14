module brain_sha256_compress_tb;
  logic [255:0] state_in;
  logic [511:0] block_in;
  logic [255:0] state_out;

  brain_sha256_compress dut(.state_in(state_in), .block_in(block_in), .state_out(state_out));

  initial begin
    state_in = {
      32'h6a09e667, 32'hbb67ae85, 32'h3c6ef372, 32'ha54ff53a,
      32'h510e527f, 32'h9b05688c, 32'h1f83d9ab, 32'h5be0cd19
    };
    // SHA-256 padding for the empty message: 0x80, zeros, 64-bit bit length 0.
    block_in = {8'h80, 440'd0, 64'd0};
    #1;
    if (state_out !== {
      32'he3b0c442, 32'h98fc1c14, 32'h9afbf4c8, 32'h996fb924,
      32'h27ae41e4, 32'h649b934c, 32'ha495991b, 32'h7852b855
    }) begin
      $display("SHA256_COMPRESS=FAIL digest=%h", state_out);
      $fatal(1);
    end
    $display("BRAIN_SHA256_COMPRESS_VECTOR=PASS");
    $finish;
  end
endmodule
