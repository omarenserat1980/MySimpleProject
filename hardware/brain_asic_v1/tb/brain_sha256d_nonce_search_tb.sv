module brain_sha256d_nonce_search_tb;
  logic clk = 0;
  logic rst_n = 0;
  logic start = 0;
  logic [639:0] header_template;
  logic [31:0] nonce_start;
  logic [255:0] target_be;
  logic busy, found, exhausted;
  logic [31:0] found_nonce;
  logic [255:0] found_digest;

  always #5 clk = ~clk;

  brain_sha256d_nonce_search dut(
    .clk(clk), .rst_n(rst_n), .start(start), .header_template(header_template),
    .nonce_start(nonce_start), .target_be(target_be), .busy(busy), .found(found),
    .found_nonce(found_nonce), .found_digest(found_digest), .exhausted(exhausted)
  );

  initial begin
    header_template = 640'h0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c;

    // Reject the final nonce against target=0 and prove the range terminates.
    nonce_start = 32'hffffffff;
    target_be = 256'd0;
    repeat (2) @(posedge clk);
    rst_n <= 1;
    @(posedge clk);
    start <= 1;
    @(posedge clk);
    start <= 0;
    wait(exhausted);
    if (found) $fatal(1, "target=0 must reject the candidate");
    $display("BRAIN_NONCE_TARGET_REJECT=PASS");

    // Reset and validate the known genesis nonce/hash with a permissive target.
    @(negedge clk);
    rst_n <= 0;
    start <= 0;
    repeat (2) @(posedge clk);
    nonce_start <= 32'h7c2bac1d;
    target_be <= {256{1'b1}};
    @(posedge clk);
    rst_n <= 1;
    @(posedge clk);
    start <= 1;
    @(posedge clk);
    start <= 0;
    wait(found);
    if (found_nonce !== 32'h7c2bac1d) $fatal(1, "unexpected nonce %h", found_nonce);
    if (found_digest !== 256'h6fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000)
      $fatal(1, "unexpected digest %h", found_digest);
    $display("BRAIN_NONCE_SEARCH_GENESIS=PASS");
    $finish;
  end

  initial begin
    #4000;
    $fatal(1, "nonce search timed out");
  end
endmodule
