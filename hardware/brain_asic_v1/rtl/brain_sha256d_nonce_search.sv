module brain_sha256d_nonce_search (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         start,
  input  logic [639:0] header_template,
  input  logic [31:0]  nonce_start,
  input  logic [255:0] target_be,
  output logic         busy,
  output logic         found,
  output logic [31:0]  found_nonce,
  output logic [255:0] found_digest,
  output logic         exhausted
);
  logic hash_start, hash_busy, hash_done;
  logic [639:0] candidate_header;
  logic [31:0] nonce_reg;
  logic [255:0] digest;
  logic [255:0] digest_be_for_pow;
  logic [255:0] header_hold;
  integer i;

  brain_sha256d_header hasher(
    .clk(clk), .rst_n(rst_n), .start(hash_start),
    .header_bits(candidate_header), .busy(hash_busy), .done(hash_done), .digest(digest)
  );

  // SHA output is serialized big-endian bytes. Bitcoin interprets the displayed
  // hash in reverse byte order for proof-of-work comparison. Convert explicitly.
  always_comb begin
    candidate_header = header_template;
    candidate_header[31:0] = {
      nonce_reg[7:0], nonce_reg[15:8], nonce_reg[23:16], nonce_reg[31:24]
    };
    for (i=0; i<32; i=i+1)
      digest_be_for_pow[i*8 +: 8] = digest[255-i*8 -: 8];
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      busy <= 1'b0;
      found <= 1'b0;
      found_nonce <= '0;
      found_digest <= '0;
      exhausted <= 1'b0;
      hash_start <= 1'b0;
      nonce_reg <= '0;
    end else begin
      hash_start <= 1'b0;
      if (start && !busy) begin
        busy <= 1'b1;
        found <= 1'b0;
        exhausted <= 1'b0;
        nonce_reg <= nonce_start;
        hash_start <= 1'b1;
      end else if (busy && hash_done) begin
        if (digest_be_for_pow <= target_be) begin
          found <= 1'b1;
          busy <= 1'b0;
          found_nonce <= nonce_reg;
          found_digest <= digest;
        end else if (nonce_reg == 32'hffffffff) begin
          busy <= 1'b0;
          exhausted <= 1'b1;
        end else begin
          nonce_reg <= nonce_reg + 1'b1;
          hash_start <= 1'b1;
        end
      end
    end
  end
endmodule
