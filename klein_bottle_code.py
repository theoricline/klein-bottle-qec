"""
klein_bottle_code.py
====================
Core module for the Klein bottle stabilizer code.

Defines the lattice, stabilizer generators, logical operators,
and circuit construction for both Klein bottle and toric codes
on an Lx × Ly grid.

Reference:
  L. Roma, "Non-Orientable Topology in a Stabilizer Circuit:
  First Experimental Demonstration of a Klein Bottle
  Quantum Error-Correcting Code", Zenodo: https://doi.org/10.5281/zenodo.19202945

Hardware experiments: IBM Fez (ibm_fez, 156-qubit Heron r2)
Primary job IDs:
  Syndrome characterisation (Klein): d6uekv2tnsts73es36jg
  Syndrome characterisation (Toric): d6uel3469uic73ci5mc0
  Topological eraser (Job 1):        d6vr4hgv5rlc73f5aqk0
  Topological eraser (Job 2):        d6vrasgv5rlc73f5b0lg
  Seed optimisation (best, Z=499σ):  d70qt62f84ks73dgn3j0
  Parallel 4 Klein codes (Z=404-721σ): d711ljaf84ks73dgujf0

Usage:
  from klein_bottle_code import KleinBottleCode, ToricCode

  kb = KleinBottleCode(Lx=4, Ly=2)
  qc = kb.circuit('erased')   # prepare b-anyon sector |01⟩_L
  print(kb.expected_syndrome('erased'))  # '00001001'
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

# ── Lattice index conventions ────────────────────────────────────
# Data qubits occupy two types of edges on the Lx × Ly lattice:
#   Horizontal edges: h(x, y) = y * Lx + (x % Lx)
#   Vertical edges:   v(x, y) = Lx*Ly + y * Lx + (x % Lx)
# Total data qubits: N_data = 2 * Lx * Ly
# Total syndrome qubits: N_syn = Lx * Ly  (one per vertex)
# Vertex index: vi(x, y) = y * Lx + x


def h(x, y, Lx):
    """Index of horizontal edge at (x, y)."""
    return y * Lx + (x % Lx)


def v(x, y, Lx, Ly):
    """Index of vertical edge at (x, y)."""
    return Lx * Ly + (y % Ly) * Lx + (x % Lx)


def vi(x, y, Lx):
    """Index of vertex (syndrome qubit) at (x, y)."""
    return y * Lx + (x % Lx)


# ── Star operators ────────────────────────────────────────────────

def klein_star(x, y, Lx, Ly):
    """
    Star operator for vertex (x, y) in the Klein bottle code.

    Identical to the toric code except at y=0: the downward
    vertical edge connects to the ANTIPODAL vertex (Lx-1-x, Ly-1)
    rather than the periodic partner (x, Ly-1).

    This single modification encodes the orientation-reversing
    identification of the Klein bottle.

    Returns: list of data qubit indices in the star.
    """
    edges = [
        h(x,     y, Lx),       # right horizontal
        h(x - 1, y, Lx),       # left horizontal
        v(x,     y, Lx, Ly),   # upward vertical
    ]
    if y == 0:
        # Antipodal edge — the Klein bottle twist
        edges.append(v(Lx - 1 - x, Ly - 1, Lx, Ly))
    else:
        # Standard periodic downward edge
        edges.append(v(x, y - 1, Lx, Ly))
    return list(set(edges))


def toric_star(x, y, Lx, Ly):
    """
    Star operator for vertex (x, y) in the toric code.
    All edges are local and periodic.

    Returns: list of data qubit indices in the star.
    """
    return list(set([
        h(x,     y, Lx),
        h(x - 1, y, Lx),
        v(x,     y, Lx, Ly),
        v(x, y - 1, Lx, Ly),
    ]))


# ── Parity check matrix ───────────────────────────────────────────

def build_parity_check_matrix(Lx, Ly, star_fn):
    """
    Build the Z-type parity check matrix H.

    H[vi, e] = 1 if data qubit e is in the star of vertex vi.
    Shape: (N_syn, N_data) = (Lx*Ly, 2*Lx*Ly)

    Args:
        Lx, Ly: lattice dimensions
        star_fn: klein_star or toric_star

    Returns:
        H: numpy array of shape (Lx*Ly, 2*Lx*Ly), dtype int8
    """
    N_data = 2 * Lx * Ly
    N_syn  = Lx * Ly
    H = np.zeros((N_syn, N_data), dtype=np.int8)
    for y in range(Ly):
        for x in range(Lx):
            syndrome_idx = vi(x, y, Lx)
            for e in star_fn(x, y, Lx, Ly):
                H[syndrome_idx, e] = 1
    return H


# ── Logical operators ─────────────────────────────────────────────

def logical_operators(Lx, Ly, code='klein'):
    """
    Z-type logical operators for the Klein bottle (or toric) code.

    Z_L1 (a-cycle): horizontal string along row y=0, length Lx.
    Z_L2 (b-cycle): vertical string along column x=0, length Ly.

    CP class is determined by Z_L2:
      Z_L2 eigenvalue +1 → CP-even sector
      Z_L2 eigenvalue -1 → CP-odd sector

    Returns:
        Z_L1, Z_L2: numpy arrays of shape (2*Lx*Ly,), dtype int8
    """
    N_data = 2 * Lx * Ly
    Z_L1 = np.zeros(N_data, dtype=np.int8)
    Z_L2 = np.zeros(N_data, dtype=np.int8)
    for x in range(Lx):
        Z_L1[h(x, 0, Lx)] = 1          # a-cycle: row 0
    for y in range(Ly):
        Z_L2[v(0, y, Lx, Ly)] = 1      # b-cycle: column 0
    return Z_L1, Z_L2


# ── Sector definitions ────────────────────────────────────────────

# Logical sector definitions: list of data qubit edges to flip with X
# to prepare each sector from the vacuum |00⟩_L.
SECTORS = {
    'vacuum':  [],        # |00⟩_L  CP-even  syndrome: 00000000
    'a_anyon': [0],       # |10⟩_L  CP-even  syndrome: 00000011
    'b_anyon': [3],       # |01⟩_L  CP-odd   syndrome: 00001001
    'both':    [0, 3],    # |11⟩_L  CP-odd   syndrome: 00001010
}

# Alternative names used in the topological eraser experiment
SECTOR_ALIASES = {
    'control': 'vacuum',
    'path':    'a_anyon',
    'erased':  'b_anyon',
    'delayed': 'both',
}

# Expected dominant syndrome pattern for each sector (Lx=4, Ly=2)
EXPECTED_SYNDROMES_4x2 = {
    'vacuum':  '00000000',
    'a_anyon': '00000011',
    'b_anyon': '00001001',
    'both':    '00001010',
}

CP_CLASS = {
    'vacuum':  'CP-even',
    'a_anyon': 'CP-even',
    'b_anyon': 'CP-odd',
    'both':    'CP-odd',
}


def resolve_sector(name):
    """Resolve sector name including aliases."""
    return SECTOR_ALIASES.get(name, name)


# ── Circuit construction ──────────────────────────────────────────

def build_syndrome_circuit(Lx, Ly, star_fn, sector='vacuum'):
    """
    Build a syndrome measurement circuit for a given logical sector.

    Prepares the specified logical sector by applying X gates to
    the data qubits listed in SECTORS[sector], then measures all
    syndrome qubits via CNOT gates from data to ancilla.

    Args:
        Lx, Ly:   lattice dimensions
        star_fn:  klein_star or toric_star
        sector:   one of 'vacuum', 'a_anyon', 'b_anyon', 'both'
                  (or aliases 'control', 'path', 'erased', 'delayed')

    Returns:
        QuantumCircuit with N_data data qubits, N_syn ancilla qubits,
        and N_syn classical bits.
    """
    sector = resolve_sector(sector)
    prep_edges = SECTORS[sector]

    N_data = 2 * Lx * Ly
    N_syn  = Lx * Ly

    qr_d = QuantumRegister(N_data, 'd')
    qr_s = QuantumRegister(N_syn,  's')
    cr   = ClassicalRegister(N_syn, 'c')
    qc   = QuantumCircuit(qr_d, qr_s, cr)

    # Prepare logical sector
    for e in prep_edges:
        qc.x(qr_d[e])
    qc.barrier()

    # Syndrome measurement: CX from each data qubit to its ancilla
    for y in range(Ly):
        for x in range(Lx):
            syndrome_idx = vi(x, y, Lx)
            for e in star_fn(x, y, Lx, Ly):
                qc.cx(qr_d[e], qr_s[syndrome_idx])

    qc.measure(qr_s, cr)
    return qc


def build_delayed_choice_circuit(Lx, Ly, erase=False):
    """
    Build a delayed-choice quantum eraser circuit.

    Step 1: Prepare |10⟩_L (a-anyon, path information present)
    Step 2: Measure syndrome BEFORE the erasure decision
    Step 3: Reset syndrome register
    Step 4: Optionally apply X_L2 (erasure operation)
    Step 5: Measure syndrome AFTER the erasure decision

    Args:
        Lx, Ly: lattice dimensions
        erase:  if True, apply erasure; if False, no erasure

    Returns:
        QuantumCircuit with 'before' and 'after' classical registers.
    """
    N_data = 2 * Lx * Ly
    N_syn  = Lx * Ly

    # Erasure operator: X_L2 = X on all vertical edges in column 0
    X_L2_edges = [v(0, y, Lx, Ly) for y in range(Ly)]

    qr_d   = QuantumRegister(N_data, 'd')
    qr_s   = QuantumRegister(N_syn,  's')
    cr_bef = ClassicalRegister(N_syn, 'before')
    cr_aft = ClassicalRegister(N_syn, 'after')
    qc     = QuantumCircuit(qr_d, qr_s, cr_bef, cr_aft)

    # Prepare |10⟩_L
    for e in SECTORS['a_anyon']:
        qc.x(qr_d[e])
    qc.barrier()

    # Pre-choice syndrome measurement
    for y in range(Ly):
        for x in range(Lx):
            for e in klein_star(x, y, Lx, Ly):
                qc.cx(qr_d[e], qr_s[vi(x, y, Lx)])
    qc.measure(qr_s, cr_bef)

    # Reset syndrome register
    qc.barrier()
    for i in range(N_syn):
        qc.reset(qr_s[i])
    qc.barrier()

    # Delayed choice: apply erasure or not
    if erase:
        for e in X_L2_edges:
            qc.x(qr_d[e])
    qc.barrier()

    # Post-choice syndrome measurement
    for y in range(Ly):
        for x in range(Lx):
            for e in klein_star(x, y, Lx, Ly):
                qc.cx(qr_d[e], qr_s[vi(x, y, Lx)])
    qc.measure(qr_s, cr_aft)

    return qc


# ── Convenience classes ───────────────────────────────────────────

class KleinBottleCode:
    """
    Klein bottle stabilizer code on an Lx × Ly lattice.

    Example:
        kb = KleinBottleCode(Lx=4, Ly=2)
        qc = kb.circuit('b_anyon')
        print(kb.expected_syndrome('b_anyon'))  # '00001001'
        print(kb.cp_class('b_anyon'))           # 'CP-odd'
    """

    def __init__(self, Lx=4, Ly=2):
        self.Lx = Lx
        self.Ly = Ly
        self.N_data = 2 * Lx * Ly
        self.N_syn  = Lx * Ly
        self.H = build_parity_check_matrix(Lx, Ly, klein_star)
        self.Z_L1, self.Z_L2 = logical_operators(Lx, Ly, 'klein')

    def star(self, x, y):
        return klein_star(x, y, self.Lx, self.Ly)

    def circuit(self, sector='vacuum'):
        return build_syndrome_circuit(
            self.Lx, self.Ly, klein_star, sector)

    def delayed_choice_circuit(self, erase=False):
        return build_delayed_choice_circuit(
            self.Lx, self.Ly, erase=erase)

    def expected_syndrome(self, sector):
        """Expected dominant syndrome pattern (Lx=4, Ly=2 only)."""
        if self.Lx == 4 and self.Ly == 2:
            return EXPECTED_SYNDROMES_4x2.get(resolve_sector(sector))
        return None

    def cp_class(self, sector):
        return CP_CLASS.get(resolve_sector(sector), 'unknown')

    def __repr__(self):
        return (f"KleinBottleCode(Lx={self.Lx}, Ly={self.Ly}, "
                f"N_data={self.N_data}, N_syn={self.N_syn}, "
                f"GSD=4)")


class ToricCode:
    """
    Toric code on an Lx × Ly lattice (control code).

    Example:
        tc = ToricCode(Lx=4, Ly=2)
        qc = tc.circuit('b_anyon')
    """

    def __init__(self, Lx=4, Ly=2):
        self.Lx = Lx
        self.Ly = Ly
        self.N_data = 2 * Lx * Ly
        self.N_syn  = Lx * Ly
        self.H = build_parity_check_matrix(Lx, Ly, toric_star)
        self.Z_L1, self.Z_L2 = logical_operators(Lx, Ly, 'toric')

    def star(self, x, y):
        return toric_star(x, y, self.Lx, self.Ly)

    def circuit(self, sector='vacuum'):
        return build_syndrome_circuit(
            self.Lx, self.Ly, toric_star, sector)

    def __repr__(self):
        return (f"ToricCode(Lx={self.Lx}, Ly={self.Ly}, "
                f"N_data={self.N_data}, N_syn={self.N_syn})")


# ── Self-test ─────────────────────────────────────────────────────

def verify(verbose=True):
    """
    Noiseless Aer simulation verifying all four sector preparations.
    Requires qiskit-aer.

    Returns True if all four Klein bottle sectors produce the
    expected dominant syndrome pattern.
    """
    try:
        from qiskit_aer import AerSimulator
    except ImportError:
        print("qiskit-aer not installed — skipping noiseless verify.")
        return None

    sim = AerSimulator()
    kb  = KleinBottleCode(Lx=4, Ly=2)
    all_ok = True

    if verbose:
        print("Noiseless verification (Lx=4, Ly=2):")
        print(f"  {'Sector':<12} {'Expected':<14} {'Got':<14} {'OK?'}")
        print("  " + "─" * 46)

    for sector in ['vacuum', 'a_anyon', 'b_anyon', 'both']:
        qc  = kb.circuit(sector)
        res = sim.run(qc, shots=512).result().get_counts()
        top = max(res, key=res.get)
        exp = kb.expected_syndrome(sector)
        ok  = (top == exp)
        all_ok = all_ok and ok
        if verbose:
            print(f"  {sector:<12} {exp:<14} {top:<14} "
                  f"{'✓' if ok else '✗ FAIL'}")

    if verbose:
        print(f"\n  Result: {'ALL PASS ✓' if all_ok else 'SOME FAILED ✗'}")
    return all_ok


if __name__ == "__main__":
    # Print code summary
    kb = KleinBottleCode(Lx=4, Ly=2)
    tc = ToricCode(Lx=4, Ly=2)
    print(kb)
    print(tc)
    print()
    print("Klein bottle star at (0,0):", kb.star(0, 0),
          "  ← includes antipodal edge")
    print("Toric code  star at (0,0):", tc.star(0, 0),
          "  ← all local edges")
    print()
    print("Logical operators:")
    print("  Z_L1 (a-cycle) support:", list(np.where(kb.Z_L1)[0]))
    print("  Z_L2 (b-cycle) support:", list(np.where(kb.Z_L2)[0]))
    print()
    verify()
