"""
kbcode/core.py
===============
Klein bottle stabilizer code — core library.
Pure Python/numpy. No IBM credentials needed.

Reference:
  L. Roma, "Non-Orientable Topology in a Stabilizer Circuit",
  Zenodo (2026), https://doi.org/10.5281/zenodo.19202945
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional

# ── Lattice index functions ───────────────────────────────────────

def h(x, y, Lx):
    """Horizontal edge index at position (x, y)."""
    return y * Lx + (x % Lx)

def v(x, y, Lx, Ly):
    """Vertical edge index at position (x, y)."""
    return Lx * Ly + (y % Ly) * Lx + (x % Lx)

def vi(x, y, Lx):
    """Syndrome qubit (vertex) index at position (x, y)."""
    return y * Lx + (x % Lx)

# ── Star operators ────────────────────────────────────────────────

def klein_star(x, y, Lx, Ly, delta=0):
    """
    Star operator for the Klein bottle code with shift δ.

    At y=0: the downward edge connects to the antipodal vertex
      ((Lx-1-x+delta) % Lx, Ly-1) — the orientation-reversing
      identification of the Klein bottle.
    At y>0: standard periodic downward edge.

    delta=0 gives the standard Klein bottle code (Paper 1).
    delta=1,2,3 give the δ-family members (Paper 2).
    """
    edges = [h(x, y, Lx), h(x-1, y, Lx), v(x, y, Lx, Ly)]
    if y == 0:
        anti_x = (Lx - 1 - x + delta) % Lx
        edges.append(v(anti_x, Ly-1, Lx, Ly))
    else:
        edges.append(v(x, y-1, Lx, Ly))
    return list(set(edges))

def toric_star(x, y, Lx, Ly, delta=0):
    """Standard toric code star operator (control)."""
    return list(set([
        h(x,   y, Lx),
        h(x-1, y, Lx),
        v(x,   y, Lx, Ly),
        v(x, y-1, Lx, Ly),
    ]))

# ── GF(2) linear algebra ──────────────────────────────────────────

def gf2_rank(H):
    """Rank of a binary matrix over GF(2)."""
    mat = H.copy().astype(int) % 2
    rows, cols = mat.shape
    rank = 0
    for col in range(cols):
        pivot = next((r for r in range(rank, rows) if mat[r, col]), None)
        if pivot is None:
            continue
        mat[[rank, pivot]] = mat[[pivot, rank]]
        for row in range(rows):
            if row != rank and mat[row, col]:
                mat[row] = (mat[row] + mat[rank]) % 2
        rank += 1
    return rank

def build_H(Lx, Ly, delta=0):
    """Build the Z-type parity check matrix H for C(delta)."""
    N_data = 2 * Lx * Ly
    N_syn  = Lx * Ly
    H = np.zeros((N_syn, N_data), dtype=int)
    for y in range(Ly):
        for x in range(Lx):
            i = vi(x, y, Lx)
            for e in klein_star(x, y, Lx, Ly, delta):
                H[i, e] = 1
    return H

def compute_gsd(Lx, Ly, delta=0):
    """
    Compute GSD, stabilizer rank, and logical qubit count k.
    GSD = 2^k where k = N_data - 2*rank(H).

    Returns: (gsd, rank, k)
    """
    H    = build_H(Lx, Ly, delta)
    rank = gf2_rank(H)
    k    = 2 * Lx * Ly - 2 * rank
    return (2**k if k >= 0 else 1), rank, k

# ── Syndrome fingerprint prediction ──────────────────────────────

def predicted_pattern(Lx, Ly, delta=0):
    """
    Predict the dominant syndrome pattern for the b-anyon
    prepared state in C(delta).

    The b-anyon preparation flips the antipodal edge at vertex (0,0).
    The pattern is determined entirely by circuit wiring — it is
    topologically protected against local quantum errors.

    Returns:
        pattern:   8-bit string e.g. '10000001'
        firing:    list of syndrome qubit indices that fire
        prep_edge: data qubit index used for b-anyon preparation
    """
    anti_x    = (Lx - 1 - 0 + delta) % Lx
    prep_edge = v(anti_x, Ly-1, Lx, Ly)

    firing = []
    for y in range(Ly):
        for x in range(Lx):
            if prep_edge in klein_star(x, y, Lx, Ly, delta):
                firing.append(vi(x, y, Lx))

    bits    = [0] * (Lx * Ly)
    for idx in firing:
        bits[idx] = 1
    pattern = ''.join(str(b) for b in reversed(bits))
    return pattern, sorted(firing), prep_edge

# ── Result dataclasses ────────────────────────────────────────────

@dataclass
class CodeResult:
    """Analysis result for a single Klein bottle code run."""
    delta:       int
    Lx:          int
    Ly:          int
    shots:       int
    f_K:         float
    f_T:         float
    Z:           float
    enhancement: float
    dominant:    str
    predicted:   str
    match:       bool
    firing:      list
    gsd:         int
    k_logical:   int
    prep_edge:   int

    @property
    def n_logical_qubits(self):
        return self.k_logical

    @property
    def verified(self):
        """True if dominant pattern matches theory at Z > 100σ."""
        return self.match and self.Z > 100

    def to_dict(self):
        return {
            'delta':             self.delta,
            'Lx':                self.Lx,
            'Ly':                self.Ly,
            'shots':             self.shots,
            'f_K':               round(self.f_K, 4),
            'f_T':               round(self.f_T, 4),
            'Z':                 round(self.Z, 1),
            'enhancement':       round(self.enhancement, 1),
            'dominant_pattern':  self.dominant,
            'predicted_pattern': self.predicted,
            'match':             self.match,
            'firing_syndromes':  self.firing,
            'GSD':               self.gsd,
            'n_logical_qubits':  self.n_logical_qubits,
            'prep_edge':         self.prep_edge,
            'verified':          self.verified,
        }


@dataclass
class ParallelResult:
    """Analysis result for parallel deployment of N Klein codes."""
    backend:        str
    n_physical:     int
    n_codes:        int
    Lx:             int
    Ly:             int
    delta:          int
    shots:          int
    codes:          list
    qubit_overlaps: int
    job_id:         Optional[str] = None

    @property
    def n_logical_qubits(self):
        return self.n_codes * self.codes[0].k_logical if self.codes else 0

    @property
    def all_verified(self):
        return all(c.verified for c in self.codes)

    @property
    def mean_fK(self):
        vals = [c.f_K for c in self.codes]
        return float(np.mean(vals)) if vals else 0.0

    @property
    def cv(self):
        vals = [c.f_K for c in self.codes]
        m = np.mean(vals)
        return float(np.std(vals) / m) if vals and m > 0 else 0.0

    @property
    def surface_codes_fit(self):
        """Surface code d=4 uses 32 qubits, encodes 1 logical qubit."""
        return self.n_physical // 32

    @property
    def klein_advantage(self):
        s = self.surface_codes_fit
        return round(self.n_logical_qubits / s, 1) if s > 0 else float('inf')

    @property
    def qubit_utilisation(self):
        qpc = 2 * self.Lx * self.Ly + self.Lx * self.Ly
        return round(self.n_codes * qpc / self.n_physical * 100, 1)

    def to_dict(self):
        return {
            'backend':              self.backend,
            'n_physical_qubits':    self.n_physical,
            'n_codes_deployed':     self.n_codes,
            'n_logical_qubits_claimed': self.n_logical_qubits,
            'qubit_utilisation_pct': self.qubit_utilisation,
            'verification': {
                'qubit_overlaps':   self.qubit_overlaps,
                'patterns_matched': sum(1 for c in self.codes if c.match),
                'z_scores':         [round(c.Z, 0) for c in self.codes],
                'mean_fK':          round(self.mean_fK, 4),
                'cv':               round(self.cv, 3),
                'all_verified':     self.all_verified,
            },
            'n_logical_qubits_verified':
                self.n_logical_qubits if self.all_verified else 0,
            'vs_surface_code_d4': {
                'surface_codes_fit':      self.surface_codes_fit,
                'surface_logical_qubits': self.surface_codes_fit,
                'klein_advantage':        f"{self.klein_advantage}×",
            },
            'codes':   [c.to_dict() for c in self.codes],
            'job_id':  self.job_id,
        }

# ── Analysis ──────────────────────────────────────────────────────

def analyse_counts(klein_counts: dict, toric_counts: dict,
                   shots: int, Lx: int, Ly: int,
                   delta: int = 0) -> CodeResult:
    """
    Analyse raw syndrome counts from a Klein + Toric job.
    No IBM credentials needed — pure computation on count dicts.

    Args:
        klein_counts: {pattern_str: count} from Klein circuit
        toric_counts: {pattern_str: count} from Toric circuit
        shots:        total shots per circuit
        Lx, Ly:       lattice dimensions
        delta:        boundary condition shift

    Returns:
        CodeResult with f_K, f_T, Z, enhancement, match, verified
    """
    pred, firing, prep_edge = predicted_pattern(Lx, Ly, delta)
    gsd, rank, k            = compute_gsd(Lx, Ly, delta)

    f_K = klein_counts.get(pred, 0) / shots
    f_T = toric_counts.get(pred, 0) / shots
    p0  = max(f_T, 1 / 2**(Lx * Ly))
    Z   = (f_K * shots - shots * p0) / np.sqrt(shots * p0 * (1 - p0))
    enh = f_K / f_T if f_T > 0 else float('inf')
    dom = max(klein_counts, key=klein_counts.get) if klein_counts else pred

    return CodeResult(
        delta=delta, Lx=Lx, Ly=Ly, shots=shots,
        f_K=float(f_K), f_T=float(f_T),
        Z=float(Z), enhancement=float(enh),
        dominant=dom, predicted=pred,
        match=(dom == pred), firing=firing,
        gsd=gsd, k_logical=k, prep_edge=prep_edge,
    )

# ── Capacity calculator ───────────────────────────────────────────

KNOWN_BACKENDS = {
    'ibm_fez':        {'n_qubits': 156, 'arch': 'Heron r2'},
    'ibm_marrakesh':  {'n_qubits': 156, 'arch': 'Heron r2'},
    'ibm_torino':     {'n_qubits': 133, 'arch': 'Eagle r3'},
    'ibm_brisbane':   {'n_qubits': 127, 'arch': 'Eagle r3'},
    'ibm_kyiv':       {'n_qubits': 127, 'arch': 'Eagle r3'},
    'ibm_sherbrooke': {'n_qubits': 127, 'arch': 'Eagle r3'},
}

def capacity(backend_name: str, Lx: int = 4, Ly: int = 2) -> dict:
    """
    Calculate Klein code capacity for a given backend.
    Compares Klein bottle vs surface code d=4 logical qubit density.
    No IBM credentials needed.
    """
    info      = KNOWN_BACKENDS.get(
                    backend_name, {'n_qubits': 127, 'arch': 'Unknown'})
    n_q       = info['n_qubits']
    qpc       = 2 * Lx * Ly + Lx * Ly          # qubits per Klein code
    gsd, _, k = compute_gsd(Lx, Ly, 0)
    max_klein = n_q // qpc
    max_surf  = n_q // 32                        # surface d=4: 32q, 1 logical

    return {
        'backend':                backend_name,
        'architecture':           info['arch'],
        'n_physical_qubits':      n_q,
        'qubits_per_klein_code':  qpc,
        'max_klein_codes':        max_klein,
        'max_logical_qubits':     max_klein * k,
        'max_surface_codes_d4':   max_surf,
        'surface_logical_qubits': max_surf,
        'klein_advantage':        round((max_klein * k) / max_surf, 1)
                                  if max_surf > 0 else 0,
        'k_per_code':             k,
        'GSD':                    gsd,
        'note': ('Klein advantage vs surface code d=4: '
                 '32 physical qubits, 1 logical qubit'),
    }

def all_capacities(Lx: int = 4, Ly: int = 2) -> list:
    """Return capacity dict for all known backends."""
    return [capacity(b, Lx, Ly) for b in KNOWN_BACKENDS]
