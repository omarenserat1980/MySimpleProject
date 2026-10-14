`timescale 1ns/1ps
module tb_brain_bitcoin_nonce_search;
    logic clk = 1'b0;
    logic rst = 1'b1;
    logic start = 1'b0;
    logic [639:0] header_template;
    logic [255:0] target;
    logic [31:0] nonce_start;
    logic [31:0] max_attempts;
    logic busy, done, found;
    logic [31:0] nonce;
    logic [255:0] digest;
    logic [31:0] attempts;

    always #5 clk = ~clk;

    localparam logic [639:0] GENESIS_HEADER =
        640'h0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c;
    localparam logic [255:0] GENESIS_RAW_DIGEST =
        256'h6fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000;
    localparam logic [255:0] GENESIS_TARGET =
        256'h00000000ffff0000000000000000000000000000000000000000000000000000;

    brain_bitcoin_nonce_search dut (
        .clk_i(clk), .rst_i(rst), .start_i(start),
        .header_template_i(header_template), .target_i(target),
        .nonce_start_i(nonce_start), .max_attempts_i(max_attempts),
        .busy_o(busy), .done_o(done), .found_o(found),
        .nonce_o(nonce), .digest_o(digest), .attempts_o(attempts)
    );

    initial begin
        header_template = GENESIS_HEADER;
        target = GENESIS_TARGET;
        nonce_start = 32'h7c2bac1d;
        max_attempts = 1;
        repeat (2) @(posedge clk);
        rst <= 1'b0;
        @(posedge clk);
        start <= 1'b1;
        @(posedge clk);
        start <= 1'b0;
        wait(done);
        #1;
        if (!found) $fatal(1, "FAIL: genesis nonce not found");
        if (nonce !== 32'h7c2bac1d) $fatal(1, "FAIL: nonce mismatch %08h", nonce);
        if (digest !== GENESIS_RAW_DIGEST) $fatal(1, "FAIL: digest mismatch %064h", digest);
        if (attempts !== 1) $fatal(1, "FAIL: expected exactly one attempt, got %0d", attempts);
        $display("PASS: bounded nonce search finds Bitcoin genesis header in one attempt");

        // Negative-path test: zero target must not accept a nonzero hash.
        target = 256'b0;
        nonce_start = 32'h7c2bac1d;
        max_attempts = 3;
        @(posedge clk);
        start <= 1'b1;
        @(posedge clk);
        start <= 1'b0;
        wait(done);
        #1;
        if (found) $fatal(1, "FAIL: zero target unexpectedly accepted a hash");
        if (attempts !== 3) $fatal(1, "FAIL: expected exactly three attempts, got %0d", attempts);
        if (busy) $fatal(1, "FAIL: search remained busy after exhausting its bound");
        $display("PASS: bounded nonce search stops after three unsuccessful attempts");
        $finish;
    end
endmodule
