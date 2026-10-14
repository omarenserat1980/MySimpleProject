`timescale 1ns/1ps
module tb_sha256d_header_hash;
  logic [511:0] header_prefix;
  logic [127:0] header_tail;
  logic [31:0] nonce;
  logic [255:0] digest;
  sha256d_header_hash dut(.*);

  initial begin
    // Bitcoin mainnet genesis header, serialized in wire byte order.
    // Prefix bytes 0..63: version, previous hash, first 28 bytes of merkle root.
    header_prefix = 512'h0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa;
    // Tail bytes 64..75: last 4 merkle-root bytes, timestamp, and nBits.
    header_tail = 128'h4b1e5e4a29ab5f49ffff001d00000000;
    // Genesis nonce numeric value 0x7c2bac1d serializes as 1d ac 2b 7c.
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
