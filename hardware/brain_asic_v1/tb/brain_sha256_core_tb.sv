module brain_sha256_core_tb;
  logic clk=0, rst_n=0, start=0;
  logic [255:0] midstate;
  logic [31:0] tail_w0, tail_w1, target;
  logic busy, found;
  logic [31:0] nonce;

  brain_sha256_core dut(.*);

  always #5 clk = ~clk;

  initial begin
    midstate = 256'h0000000810000007100000061000000510000004100000031000000210000001;
    tail_w0 = 32'h20000000;
    tail_w1 = 32'h30000000;
    target  = 32'hffffffff;

    #12 rst_n = 1;
    #10 start = 1;
    #10 start = 0;
    wait(!busy);
    #10;
    if (!found) $fatal(1, "ASIC control-path smoke test failed");
    $display("BRAIN_ASIC_V1_SMOKE=PASS");
    $finish;
  end

  initial begin
    #1000;
    $fatal(1, "ASIC control-path smoke test timed out");
  end
endmodule
