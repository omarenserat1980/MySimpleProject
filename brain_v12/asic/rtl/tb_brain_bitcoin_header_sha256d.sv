`timescale 1ns/1ps
module tb_brain_bitcoin_header_sha256d;
    logic [639:0] header;
    logic [255:0] digest;

    // Bitcoin mainnet genesis block header, serialized in wire byte order.
    localparam logic [639:0] GENESIS_HEADER =
        640'h0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c;
    // Raw SHA256d digest byte order; displayed block hash reverses these bytes.
    localparam logic [255:0] GENESIS_DIGEST =
        256'h6fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000;

    brain_bitcoin_header_sha256d dut (
        .header_i(header),
        .digest_o(digest)
    );

    initial begin
        header = GENESIS_HEADER;
        #1;
        if (digest !== GENESIS_DIGEST) begin
            $display("FAIL: genesis header digest mismatch");
            $display("expected=%064h", GENESIS_DIGEST);
            $display("actual  =%064h", digest);
            $fatal(1);
        end
        $display("PASS: Bitcoin genesis 80-byte header SHA256d vector");
        $finish;
    end
endmodule
