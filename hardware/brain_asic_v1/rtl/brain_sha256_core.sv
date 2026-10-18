module brain_sha256_core (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         start,
  // Packed vector keeps the control shell compatible with Yosys synthesis.
  // Word 0 occupies midstate[31:0].
  input  logic [255:0] midstate,
  input  logic [31:0]  tail_w0,
  input  logic [31:0]  tail_w1,
  input  logic [31:0]  target,
  output logic         busy,
  output logic         found,
  output logic [31:0]  nonce
);
  // Control-path placeholder only; this is not a complete miner.
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      busy <= 1'b0;
      found <= 1'b0;
      nonce <= 32'd0;
    end else if (start && !busy) begin
      busy <= 1'b1;
      found <= 1'b0;
      nonce <= 32'd0;
    end else if (busy) begin
      busy <= 1'b0;
      found <= ((midstate[31:0] ^ tail_w0 ^ tail_w1) <= target);
    end
  end
endmodule
