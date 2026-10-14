`timescale 1ns/1ps
module tb_brain_bitcoin_target_check;
    logic [255:0] digest;
    logic [255:0] target;
    logic [255:0] hash_value;
    logic meets_target;

    localparam logic [255:0] GENESIS_RAW_DIGEST =
        256'h6fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000;
    localparam logic [255:0] GENESIS_DISPLAY_HASH =
        256'h000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f;
    localparam logic [255:0] GENESIS_TARGET =
        256'h00000000ffff0000000000000000000000000000000000000000000000000000;

    brain_bitcoin_target_check dut (
        .digest_i(digest),
        .target_i(target),
        .hash_value_o(hash_value),
        .meets_target_o(meets_target)
    );

    initial begin
        digest = GENESIS_RAW_DIGEST;
        target = GENESIS_TARGET;
        #1;
        if (hash_value !== GENESIS_DISPLAY_HASH)
            $fatal(1, "FAIL: digest byte reversal mismatch: %064h", hash_value);
        if (meets_target !== 1'b1)
            $fatal(1, "FAIL: genesis hash should meet genesis target");
        target = 256'b0;
        #1;
        if (meets_target !== 1'b0)
            $fatal(1, "FAIL: nonzero genesis hash must not meet zero target");
        $display("PASS: Bitcoin digest byte order and target comparator vectors");
        $finish;
    end
endmodule
