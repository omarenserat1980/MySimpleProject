module brain_sha256d_header_tb;
  logic clk = 0;
  logic rst_n = 0;
  logic start = 0;
  logic [639:0] header_bits;
  logic busy, done;
  logic [255:0] digest;

  always #5 clk = ~clk;

  brain_sha256d_header dut(
    .clk(clk), .rst_n(rst_n), .start(start),
    .header_bits(header_bits), .busy(busy), .done(done), .digest(digest)
  );

  initial begin
    // Bitcoin mainnet genesis block header, bytes in serialized header order.
    header_bits = 640'h0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c;
    repeat (2) @(posedge clk);
    rst_n <= 1;
    @(posedge clk);
    start <= 1;
    @(posedge clk);
    start <= 0;
    wait(done);
    if (digest !== 256'h6fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000) begin
      $display("BRAIN_SHA256D_GENESIS=FAIL digest=%h", digest);
      $fatal(1);
    end
    $display("BRAIN_SHA256D_GENESIS=PASS");
    $finish;
  end
  initial begin
    #1000;
    $fatal(1, "timeout waiting for SHA256d result");
  end
endmodule
