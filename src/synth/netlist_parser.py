"""
Gate-level Verilog netlist parser.

Parses the gate-level Verilog emitted by Yosys and extracts cell instances
and their port connections.  The extracted instances are passed to the
geometry mapper to build bounding-box layout representations.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PortConn:
    port: str
    net:  str


@dataclass
class CellInstance:
    cell_type:   str
    inst_name:   str
    connections: List[PortConn] = field(default_factory=list)


@dataclass
class ParsedNetlist:
    top_module:  str
    instances:   List[CellInstance]
    input_ports: List[str]
    output_ports: List[str]
    wire_names:  List[str]


class NetlistParser:
    """
    Parse a Yosys-emitted gate-level Verilog file.

    Supports the subset of Verilog produced by Yosys write_verilog:
    - module declaration with port list
    - input/output/wire declarations
    - cell instantiations with named port connections
    """

    def parse(self, path: str) -> Optional[ParsedNetlist]:
        """
        Parse *path* and return a ParsedNetlist, or None on failure.
        """
        try:
            with open(path) as fh:
                text = fh.read()
        except OSError as exc:
            logger.error("Cannot read netlist: %s", exc)
            return None

        # Strip comments
        text = re.sub(r'//.*?\n', '\n', text)
        text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.DOTALL)

        top, in_ports, out_ports = self._parse_module(text)
        wires = self._parse_wires(text)
        instances = self._parse_instances(text)

        logger.info(
            "Netlist: module=%s inputs=%d outputs=%d wires=%d instances=%d",
            top, len(in_ports), len(out_ports), len(wires), len(instances),
        )
        return ParsedNetlist(
            top_module   = top,
            instances    = instances,
            input_ports  = in_ports,
            output_ports = out_ports,
            wire_names   = wires,
        )

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_module(text: str) -> Tuple[str, List[str], List[str]]:
        m = re.search(r'\bmodule\s+(\w+)\s*[(\s]', text)
        top = m.group(1) if m else "unknown"

        in_ports  = re.findall(r'\binput\s+(?:wire\s+)?(?:\[[\d\s:]+\]\s+)?(\w+)', text)
        out_ports = re.findall(r'\boutput\s+(?:wire\s+)?(?:\[[\d\s:]+\]\s+)?(\w+)', text)
        return top, in_ports, out_ports

    @staticmethod
    def _parse_wires(text: str) -> List[str]:
        return re.findall(r'\bwire\s+(?:\[[\d\s:]+\]\s+)?(\w+)', text)

    @staticmethod
    def _parse_instances(text: str) -> List[CellInstance]:
        """
        Match patterns like:
            NAND2_X1 u1 (.A(a), .B(b), .ZN(z));
        """
        instances: List[CellInstance] = []
        # cell_type inst_name (.port(net), ...);
        inst_re = re.compile(
            r'(\w+)\s+(\w+)\s*\(([^;]*)\)\s*;',
            re.DOTALL,
        )
        port_re = re.compile(r'\.(\w+)\s*\(\s*(\w+)\s*\)')

        keywords = {
            "module", "input", "output", "wire", "reg",
            "assign", "always", "begin", "end", "endmodule",
        }

        for m in inst_re.finditer(text):
            cell_type = m.group(1)
            if cell_type in keywords:
                continue
            inst_name = m.group(2)
            conns_str = m.group(3)
            conns = [
                PortConn(port=pm.group(1), net=pm.group(2))
                for pm in port_re.finditer(conns_str)
            ]
            instances.append(CellInstance(
                cell_type=cell_type,
                inst_name=inst_name,
                connections=conns,
            ))

        return instances
