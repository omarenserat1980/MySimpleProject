`timescale 1ns/1ps
module tb_brain_mac_accelerator;
  localparam int DATA_WIDTH = 8;
  localparam int ACC_WIDTH = 32;
  logic clk = 0;
  logic rst_n = 1;
  logic clear = 0;
  logic enable = 0;
  logic signed [DATA_WIDTH-1:0] operand_a = 0;
  logic signed [DATA_WIDTH-1:0] operand_b = 0;
  logic signed [ACC_WIDTH-1:0] accumulator;

  brain_mac_accelerator #(.DATA_WIDTH(DATA_WIDTH), .ACC_WIDTH(ACC_WIDTH)) dut (
    .clk(clk), .rst_n(rst_n), .clear(clear), .enable(enable),
    .operand_a(operand_a), .operand_b(operand_b), .accumulator(accumulator)
  );

  always #5 clk = ~clk;

  task automatic apply_mac(input integer a, input integer b, input integer expected);
    begin
      @(negedge clk);
      operand_a = a;
      operand_b = b;
      enable = 1;
      clear = 0;
      @(posedge clk); #1;
      if ($signed(accumulator) !== expected) begin
        $display("FAIL MAC a=%0d b=%0d got=%0d expected=%0d", a, b, $signed(accumulator), expected);
        $fatal(1);
      end
    end
  endtask

  initial begin
    #1 rst_n = 0;
    #2;
    if (accumulator !== 0) $fatal(1, "reset failed");
    rst_n = 1;

    apply_mac(3, 4, 12);
    apply_mac(-2, 5, 2);
    apply_mac(-7, -3, 23);
    apply_mac(127, 127, 16152);

    // Deterministic-length randomized differential sequence against integer reference.
    // Keep the expected value in a signed 32-bit testbench integer.
    begin : randomized_reference_checks
      integer expected_acc;
      integer rand_a;
      integer rand_b;
      integer i;
      expected_acc = 0;
      @(negedge clk);
      clear = 1;
      enable = 0;
      @(posedge clk); #1;
      if ($signed(accumulator) !== 0) $fatal(1, "random test initialization clear failed");
      for (i = 0; i < 128; i = i + 1) begin
        rand_a = $urandom_range(0, 255) - 128;
        rand_b = $urandom_range(0, 255) - 128;
        expected_acc = expected_acc + (rand_a * rand_b);
        apply_mac(rand_a, rand_b, expected_acc);
      end
    end

    // Restore a known baseline for the hold/clear tests below.
    @(negedge clk);
    clear = 1;
    enable = 0;
    @(posedge clk); #1;
    apply_mac(3, 4, 12);
    apply_mac(-2, 5, 2);
    apply_mac(-7, -3, 23);
    apply_mac(127, 127, 16152);

    // Disabled unit must hold the accumulated result.
    @(negedge clk);
    enable = 0;
    operand_a = 12;
    operand_b = 12;
    @(posedge clk); #1;
    if ($signed(accumulator) !== 16152) $fatal(1, "enable hold failed");

    // Clear takes priority over enable.
    @(negedge clk);
    clear = 1;
    enable = 1;
    @(posedge clk); #1;
    if ($signed(accumulator) !== 0) $fatal(1, "clear failed");

    // Asynchronous reset clears state without waiting for a clock edge.
    @(negedge clk);
    clear = 0;
    enable = 1;
    operand_a = -128;
    operand_b = 1;
    @(posedge clk); #1;
    rst_n = 0;
    #1;
    if ($signed(accumulator) !== 0) $fatal(1, "asynchronous reset failed");

    $display("ALL_MAC_TESTS_PASSED");
    $finish;
  end
endmodule
