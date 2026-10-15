`timescale 1ns/1ps
module tb_bitcoin_pow_target_check;
  logic [255:0] raw_digest, target_be, digest_numeric;
  logic meets_target;
  bitcoin_pow_target_check dut(.*);
  initial begin
    // Bitcoin mainnet genesis block digest and target decoded from nBits=0x1d00ffff.
    raw_digest = 256'h6fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000;
    target_be = 256'h00000000ffff0000000000000000000000000000000000000000000000000000;
    #1;
    if (digest_numeric !== 256'h000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f) begin
      $display("FAIL digest byte order: %064h", digest_numeric); $fatal(1);
    end
    if (meets_target !== 1'b1) begin $display("FAIL genesis target compare"); $fatal(1); end
    $display("PASS GENESIS_TARGET_ACCEPTED");

    raw_digest = 256'hffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff;
    #1;
    if (meets_target !== 1'b0) begin $display("FAIL above-target digest accepted"); $fatal(1); end
    $display("PASS ABOVE_TARGET_REJECTED");
    $display("ALL_BITCOIN_TARGET_CHECK_TESTS_PASSED");
    $finish;
  end
endmodule
