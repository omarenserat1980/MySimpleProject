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

  logic [255:0] state_reg;
  logic [511:0] block_reg;
  logic [255:0] compressed;
  logic [1:0] phase;
  logic [639:0] header_reg;
  logic [511:0] first_block;
  logic [511:0] second_block;
  logic [511:0] digest_block;
  logic [255:0] first_hash;
  logic [511:0] compress_block;
  logic [255:0] compress_state;
  logic [255:0] compress_result;

  brain_sha256_compress compressor(
    .state_in(compress_state),
    .block_in(compress_block),
    .state_out(compress_result)
  );

  always_comb begin
    // Bitcoin header bytes are supplied as an 80-byte big-endian bit vector.
    // The first SHA-256 pass uses one 512-bit block then a padded 128-bit tail.
    first_block = header_reg[639:128];
    second_block = {header_reg[127:0], 8'h80, 368'd0, 64'd640};
    digest_block = {first_hash, 8'h80, 184'd0, 64'd256};

    compress_state = state_reg;
    compress_block = block_reg;
    if (phase == 0) begin
      compress_state = IV;
      compress_block = first_block;
    end else if (phase == 1) begin
      compress_state = first_hash;
      compress_block = second_block;
    end else if (phase == 2) begin
      compress_state = IV;
      compress_block = digest_block;
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      busy <= 1'b0;
      done <= 1'b0;
      digest <= '0;
      state_reg <= '0;
      block_reg <= '0;
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
          0: begin
            first_hash <= compress_result;
            phase <= 1;
          end
          1: begin
            first_hash <= compress_result;
            phase <= 2;
          end
          2: begin
            digest <= compress_result;
            busy <= 1'b0;
            done <= 1'b1;
            phase <= 3;
          end
          default: begin
            busy <= 1'b0;
            phase <= 0;
          end
        endcase
      end
    end
  end
endmodule
