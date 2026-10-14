`timescale 1ns/1ps
module tb_bitcoin_nonce_sweep;
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
    header_prefix=512'b0;
    header_tail=128'b0;
    target_be={256{1'b1}}; // Deliberately easy target for a deterministic control test.
    nonce_start=32'd42;
    max_attempts=32'd4;
    repeat(2) @(negedge clk);
    rst_n=1;
    @(negedge clk); start=1;
    @(negedge clk); start=0;
    wait(done);
    #1;
    if (!found || found_nonce !== 32'd42 || attempts !== 32'd1) begin
      $display("FAIL bounded sweep found=%b nonce=%0d attempts=%0d",found,found_nonce,attempts);
      $fatal(1);
    end
    if (busy) $fatal(1,"busy remained high after finding a candidate");
    $display("PASS BOUNDED_NONCE_SWEEP_EASY_TARGET");
    $display("ALL_NONCE_SWEEP_TESTS_PASSED");
    $finish;
  end
endmodule
