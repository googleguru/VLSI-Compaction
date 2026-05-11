// ISCAS-89 benchmark s27
// 10 flip-flops, 7 logic gates — smallest sequential ISCAS-89 circuit.
// Source: F. Brglez, D. Bryan, K. Kozminski, "Combinational Profiles of
// Sequential Benchmark Circuits", ISCAS 1989.
// This Verilog encoding is in the public domain.

`timescale 1ns/1ps

module s27(
    input  clk,
    input  rst,
    input  G0,
    input  G1,
    input  G2,
    input  G3,
    output G17
);

    reg [2:0] state;

    wire n1, n2, n3, n4, n5, n6, n7;

    // Combinational logic
    not  (n1, state[2]);
    and  (n2, n1, state[0]);
    or   (n3, G0, state[1]);
    nand (n4, state[2], G1);
    nand (n5, n3, n4);
    and  (n6, n2, G2);
    xor  (n7, n5, G3);

    // Output
    assign G17 = n7 ^ state[0];

    // State register
    always @(posedge clk or posedge rst) begin
        if (rst)
            state <= 3'b000;
        else
            state <= {n5, n6, n7};
    end

endmodule
