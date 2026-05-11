// ISCAS-85 benchmark c17
// 6 NAND2 gates, 5 primary inputs, 2 primary outputs
// Source: F. Brglez and H. Fujiwara, "A Neutral Netlist of 10 Combinational
// Benchmark Circuits and a Target Translator in Fortran", ISCAS 1985.
// This Verilog encoding is in the public domain.

`timescale 1ns/1ps

module c17(
    input  G1nGATE,
    input  G2nGATE,
    input  G3nGATE,
    input  G6nGATE,
    input  G7nGATE,
    output G22nGATE,
    output G23nGATE
);

    wire N10, N11, N16, N19;

    nand (N10,  G1nGATE, G3nGATE);
    nand (N11,  G3nGATE, G6nGATE);
    nand (N16,  G2nGATE, N11);
    nand (N19,  N11,     G7nGATE);
    nand (G22nGATE, N10, N16);
    nand (G23nGATE, N16, N19);

endmodule
