`timescale 1ns/1ps
// Integrated known-answer search: begin one nonce before Bitcoin's genesis nonce,
// then prove the real genesis header meets the decoded mainnet difficulty target.
module tb_bitcoin_genesis_nonce_search;
  logic clk=0, rst_n=0, start=0;
  logic [511:0] header_prefix;
  logic [127:0] header_tail;
  logic [255:0] target_be;
  logic [31:0] nonce_start, max_attempts;
  logic busy, done, found;
  logic [31:0] found_nonce, attempts;

  bitcoin_nonce_sweep #(.HARD_MAX_ATTEMPTS(32'd16)) dut(.*);
  always #5 clk=~clk;

  initial begin
    // Serialized header: version, previous hash, first 28 merkle-root bytes.
    header_prefix = 512'h01000000
      0000000000000000000000000000000000000000000000000000000000000000
      3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa;
    // Remaining merkle-root bytes, timestamp, nBits; nonce is supplied separately.
    header_tail = 128'h4b1e5e4a29ab5f49ffff001d00000000;
    target_be = 256'h00000000ffff0000000000000000000000000000000000000000000000000000;
    nonce_start = 32'h7c2bac1c;
    max_attempts = 32'd2;

    repeat(2) @(negedge clk);
    rst_n=1;
    @(negedge clk); start=1;
    @(negedge clk); start=0;
    wait(done);
    #1;
    if (!found || found_nonce !== 32'h7c2bac1d || attempts !== 32'd2) begin
      $display("FAIL genesis nonce search found=%b nonce=%08x attempts=%0d",found,found_nonce,attempts);
      $fatal(1);
    end
    if (busy) $fatal(1,"busy remained high after genesis nonce match");
    $display("PASS BITCOIN_GENESIS_NONCE_FOUND nonce=%08x attempts=%0d",found_nonce,attempts);
    $display("ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED");
    $finish;
  end
endmodule
