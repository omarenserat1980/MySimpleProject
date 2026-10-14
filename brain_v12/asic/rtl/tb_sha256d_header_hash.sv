`timescale 1ns/1ps
module tb_sha256d_header_hash;
  logic [511:0] header_prefix;
  logic [127:0] header_tail;
  logic [31:0] nonce;
  logic [255:0] digest;
  sha256d_header_hash dut(.*);

  initial begin
    // Bitcoin mainnet genesis block header serialized in wire byte order.
    header_prefix = {
      32'h01000000,
      256'b0,
      32'hfd3ba33b, // placeholder guard overwritten below by explicit full vector
      32'hb2127b7a, 32'h3e2cc77a, 32'h618f7667,
      32'hc31bc87f, 32'h32518a88, 32'haab89f3a, 32'h4a5e1e4b
    };
    // Use explicit 64-byte prefix to avoid ambiguity in endian conversions.
    header_prefix = 512'h0100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f61;
    header_tail = 128'h7fc81bc3888a51323a9fb8aa4b1e5e4a;
    // Tail here carries header bytes 64..79 with nonce bytes zeroed in the final 4.
    // Genesis nonce is 0x7c2bac1d numerically; wire bytes are 1d ac 2b 7c.
    nonce = 32'h7c2bac1d;
    #1;
    if (digest !== 256'h6fe28c0ab6f1b372c1a6a246ae63f74f931e8365e15a089c68d6190000000000) begin
      $display("FAIL genesis SHA256d header digest: %064h", digest);
      $fatal(1);
    end
    $display("PASS BITCOIN_GENESIS_HEADER_SHA256D");
    $display("ALL_SHA256D_HEADER_RTL_TESTS_PASSED");
    $finish;
  end
endmodule
