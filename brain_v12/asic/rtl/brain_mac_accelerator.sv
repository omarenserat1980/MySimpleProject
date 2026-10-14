// Electronic Brain Digital ASIC Lab — experimental signed MAC unit.
// Digital RTL prototype only. Not fabricated hardware.
`timescale 1ns/1ps
module brain_mac_accelerator #(
    parameter int DATA_WIDTH = 8,
    parameter int ACC_WIDTH = 32
) (
    input  logic clk,
    input  logic rst_n,
    input  logic clear,
    input  logic enable,
    input  logic signed [DATA_WIDTH-1:0] operand_a,
    input  logic signed [DATA_WIDTH-1:0] operand_b,
    output logic signed [ACC_WIDTH-1:0] accumulator
);
    logic signed [(2*DATA_WIDTH)-1:0] product;
    logic signed [ACC_WIDTH-1:0] product_extended;

    // Assignment between signed vectors performs sign extension when ACC_WIDTH
    // exceeds the full product width, without a negative replication count for
    // unsupported parameter combinations.
    always_comb begin
        product = operand_a * operand_b;
        product_extended = product;
    end

    initial begin
        if (DATA_WIDTH < 1)
            $fatal(1, "DATA_WIDTH must be at least 1");
        if (ACC_WIDTH < (2*DATA_WIDTH))
            $fatal(1, "ACC_WIDTH must be at least twice DATA_WIDTH");
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            accumulator <= '0;
        else if (clear)
            accumulator <= '0;
        else if (enable)
            accumulator <= accumulator + product_extended;
    end
endmodule
