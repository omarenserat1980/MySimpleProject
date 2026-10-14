`timescale 1ns/1ps
module tb_sha256_compress;
  logic [511:0] block;
  logic [255:0] state_in, state_out;
  sha256_compress dut(.block(block), .state_in(state_in), .state_out(state_out));
  initial begin
    // SHA-256 padding block for the empty message: 0x80 then zeros, bit length 0.
    block = {8'h80, 440'b0, 64'b0};
    state_in = {32'h6a09e667,32'hbb67ae85,32'h3c6ef372,32'ha54ff53a,
                32'h510e527f,32'h9b05688c,32'h1f83d9ab,32'h5be0cd19};
    #1;
    if (state_out !== 256'he3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855) begin
      $display("FAIL empty-message SHA-256: %064h", state_out);
      $fatal(1);
    end
    $display("PASS SHA256_EMPTY_MESSAGE");
    $display("ALL_SHA256_RTL_TESTS_PASSED");
    $finish;
  end
endmodule
