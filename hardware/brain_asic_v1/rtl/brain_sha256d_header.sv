module brain_sha256d_header (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         start,
  input  logic [639:0] header_bits,
  output logic         busy,
  output logic         done,
  output logic [255:0] digest
);
  localparam logic [255:0] IV = {
    32'h6a09e667,32'hbb67ae85,32'h3c6ef372,32'ha54ff53a,
    32'h510e527f,32'h9b05688c,32'h1f83d9ab,32'h5be0cd19
  };

  logic [1:0] phase;
  logic [639:0] header_reg;
  logic [511:0] first_block, second_block, digest_block, compress_block;
  logic [255:0] first_hash, compress_state, compress_result;

  brain_sha256_compress compressor(
    .state_in(compress_state),
    .block_in(compress_block),
    .state_out(compress_result)
  );

  always_comb begin
    first_block = header_reg[639:128];
    // 16-byte header tail, SHA padding byte, 39 zero bytes, 64-bit length 640.
    second_block = {header_reg[127:0], 8'h80, 312'd0, 64'd640};
    // SHA-256 of the 32-byte first digest: 32 bytes, padding, 23 zero bytes, length 256.
    digest_block = {first_hash, 8'h80, 184'd0, 64'd256};

    compress_state = IV;
    compress_block = first_block;
    case (phase)
      1: begin compress_state = first_hash; compress_block = second_block; end
      2: begin compress_state = IV; compress_block = digest_block; end
      default: begin compress_state = IV; compress_block = first_block; end
    endcase
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      busy <= 1'b0;
      done <= 1'b0;
      digest <= '0;
      first_hash <= '0;
      header_reg <= '0;
      phase <= 0;
    end else begin
      done <= 1'b0;
      if (start && !busy) begin
        header_reg <= header_bits;
        busy <= 1'b1;
        phase <= 0;
      end else if (busy) begin
        case (phase)
          0: begin first_hash <= compress_result; phase <= 1; end
          1: begin first_hash <= compress_result; phase <= 2; end
          2: begin digest <= compress_result; busy <= 1'b0; done <= 1'b1; phase <= 3; end
          default: begin busy <= 1'b0; phase <= 0; end
        endcase
      end
    end
  end
endmodule
