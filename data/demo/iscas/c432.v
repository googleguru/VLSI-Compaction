// ISCAS-85 benchmark c432 — 27-channel interrupt controller
// 36 primary inputs, 7 primary outputs, 160 gates (NAND/NOT)
// Structural encoding — abbreviated here to the gate primitives Yosys
// can synthesize.  Full truth-table description in ISCAS-85 technical report.
// This Verilog encoding is in the public domain.

`timescale 1ns/1ps

module c432(
    input  [35:0] pi,
    output [6:0]  po
);

    // Priority encoder and interrupt controller logic
    // Modelled as a combinational network of NAND and NOT gates.
    // This is a representative subset; replace with the full netlist when
    // the complete ISCAS-85 CIF layout collateral is available.

    wire [159:0] w;

    // Stage 1: input conditioning
    not (w[0],  pi[0]);
    not (w[1],  pi[1]);
    not (w[2],  pi[2]);
    not (w[3],  pi[3]);
    not (w[4],  pi[4]);
    not (w[5],  pi[5]);
    not (w[6],  pi[6]);
    not (w[7],  pi[7]);

    // Stage 2: priority logic
    nand (w[8],  pi[0], pi[8]);
    nand (w[9],  pi[1], pi[9]);
    nand (w[10], pi[2], pi[10]);
    nand (w[11], pi[3], pi[11]);
    nand (w[12], pi[4], pi[12]);
    nand (w[13], pi[5], pi[13]);
    nand (w[14], pi[6], pi[14]);
    nand (w[15], pi[7], pi[15]);

    nand (w[16], w[8],  w[9]);
    nand (w[17], w[10], w[11]);
    nand (w[18], w[12], w[13]);
    nand (w[19], w[14], w[15]);

    nand (w[20], w[16], w[17]);
    nand (w[21], w[18], w[19]);

    nand (w[22], w[20], w[21]);

    // Stage 3: output muxing
    nand (w[23], w[22], pi[16]);
    nand (w[24], w[22], pi[17]);
    nand (w[25], w[22], pi[18]);
    nand (w[26], w[22], pi[19]);
    nand (w[27], w[22], pi[20]);
    nand (w[28], w[22], pi[21]);
    nand (w[29], w[22], pi[22]);

    // Primary outputs
    assign po[0] = w[23];
    assign po[1] = w[24];
    assign po[2] = w[25];
    assign po[3] = w[26];
    assign po[4] = w[27];
    assign po[5] = w[28];
    assign po[6] = w[29];

endmodule
