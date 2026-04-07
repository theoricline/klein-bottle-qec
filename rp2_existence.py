"""
rp2_existence.py
================
Experimental confirmation of the RP² stabilizer code on IBM Fez.

Tests four circuits designed to confirm both boundary twists of the
real projective plane identification simultaneously:

  1. Vacuum      — no flip, expected syndrome {}
  2. Flip v(3,3) — vertical twist only, expected syndrome {0, 15}
  3. Flip h(3,0) — horizontal twist only, expected syndrome {3, 12}  ← kill test
  4. Flip both   — both twists, expected syndrome {0, 3, 12, 15}

The kill test (circuit 3) is the discriminating experiment:
  RP²        predicts syndrome {3, 12}  — non-local, horizontal identification
  Klein/Toric predict  {0, 3}           — local, adjacent vertices

Hardware firing {3, 12} at high significance confirms the horizontal
twist is physically realised, proving RP² is distinct from all orientable codes.

Verification data: data/04_rp2_existence.json
  Job d7af5cak86tc73a1hpvg — IBM Fez — 2026-04-07 — 2048 shots
  Results: vacuum 571σ · v(3,3) 390σ · h(3,0) 362σ · both 266σ

Reference:
  L. Roma, "Experimental Realization of the Klein Bottle Stabilizer Code
  on a Superconducting Processor", Zenodo (2026).
  doi:10.5281/zenodo.19284050
"""

import json, time
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# ── Parameters ────────────────────────────────────────────────────────────

LX    = 4       # lattice width
LY    = 4       # lattice height  (square — required for RP² routing symmetry)
SHOTS = 2048
SEED  = 77      # seed=77 optimal on IBM Fez for this geometry

N_DATA = 2 * LX * LY   # 32 data qubits
N_SYN  = LX * LY       # 16 syndrome ancillas
P0     = 1 / 2**N_SYN  # baseline = 1/65536

# ── Edge indexing ─────────────────────────────────────────────────────────

def h(x, y):
    """Horizontal edge index at lattice position (x, y)."""
    return y * LX + (x % LX)

def v(x, y):
    """Vertical edge index at lattice position (x, y)."""
    return LX * LY + (y % LY) * LX + (x % LX)

def vi(x, y):
    """Syndrome ancilla (vertex) index at lattice position (x, y)."""
    return y * LX + (x % LX)

# ── RP² star operator ─────────────────────────────────────────────────────

def rp2_star(x, y):
    """
    Star operator for the RP² code on an Lx×Ly lattice.

    Both pairs of opposite edges are identified with reversal:
      Vertical twist:   (x, 0) ~ (Lx-1-x, Ly-1)
      Horizontal twist: (0, y) ~ (Lx-1,   Ly-1-y)

    Modification vs Klein bottle:
      y=0: bottom vertical edge → v(Lx-1-x, Ly-1)  [same as Klein]
      x=0: left horizontal edge → h(Lx-1,   Ly-1-y) [NEW in RP²]
    """
    edges = [h(x, y), v(x, y)]

    # Left horizontal edge — antipodal identification at x=0
    if x == 0:
        edges.append(h(LX - 1, LY - 1 - y))
    else:
        edges.append(h(x - 1, y))

    # Bottom vertical edge — antipodal identification at y=0
    if y == 0:
        edges.append(v(LX - 1 - x, LY - 1))
    else:
        edges.append(v(x, y - 1))

    return list(set(edges))

# Key edges
E_V33 = v(LX-1, LY-1)   # v(3,3) — vertical twist discriminating edge
E_H30 = h(LX-1, 0)      # h(3,0) — horizontal twist kill-test edge

# ── Circuit builder ───────────────────────────────────────────────────────

def build_circuit(flip_edges):
    """
    Build RP² syndrome measurement circuit.

    Args:
        flip_edges: data qubit indices to X-flip before syndrome extraction.

    Returns:
        QuantumCircuit: N_DATA data qubits + N_SYN syndrome ancillas.
        Classical register 'c' holds the N_SYN syndrome bits.
    """
    qr_d = QuantumRegister(N_DATA, 'd')
    qr_s = QuantumRegister(N_SYN,  's')
    cr   = ClassicalRegister(N_SYN, 'c')
    qc   = QuantumCircuit(qr_d, qr_s, cr)

    for e in flip_edges:
        qc.x(qr_d[e])
    qc.barrier()

    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in rp2_star(x, y):
                qc.cx(qr_d[e], qr_s[anc])

    qc.measure(qr_s, cr)
    return qc

# ── Analysis ──────────────────────────────────────────────────────────────

def stats(counts, shots):
    """Return (dominant_pattern, frequency, Z_sigma)."""
    dom = max(counts, key=counts.get)
    f   = counts[dom] / shots
    Z   = (f - P0) / (P0 * (1 - P0) / shots)**0.5
    return dom, round(f, 6), round(Z, 1)

def fires(pattern):
    """Return sorted list of syndrome bit indices that are 1."""
    return sorted([i for i, b in enumerate(reversed(pattern)) if b == '1'])

# ── Main ──────────────────────────────────────────────────────────────────

def main():
    configs = [
        ("vacuum", [],              [],              "{}"),
        ("v33",    [E_V33],         [0, 15],         "{0, 15}"),
        ("h30",    [E_H30],         [3, 12],         "{3, 12}  ← kill test"),
        ("both",   [E_V33, E_H30],  [0, 3, 12, 15],  "{0, 3, 12, 15}"),
    ]

    print("RP² Stabilizer Code — Existence Confirmation")
    print("=" * 58)
    print(f"Lattice: {LX}×{LY}  |  Data: {N_DATA}q  |  Syndrome: {N_SYN}q")
    print(f"Shots: {SHOTS}  |  Seed: {SEED}  |  p₀ = {P0:.2e}")
    print()
    print("Kill test: edge h(3,0)")
    print(f"  RP²        → syndrome {{3, 12}}  (non-local, horizontal twist)")
    print(f"  Klein/Toric → syndrome {{0, 3}}   (local, adjacent)")
    print()

    # Build
    print("Building circuits...")
    built = []
    for label, flips, expected, note in configs:
        qc = build_circuit(flips)
        built.append((label, qc, flips, expected, note))
        print(f"  {label:<8} flips={str(flips):<12} expected={note}")

    # Connect
    print("\nConnecting to IBM Fez...")
    service = QiskitRuntimeService()
    backend = service.backend("ibm_fez")
    print(f"✅ {backend.num_qubits}q  |  {backend.status().pending_jobs} pending")

    # Transpile
    pm = generate_preset_pass_manager(
        optimization_level=3, backend=backend, seed_transpiler=SEED)
    print(f"\nTranspiling {len(built)} circuits (seed={SEED})...")
    isa_list = []
    for label, qc, flips, expected, note in built:
        isa = pm.run(qc)
        isa_list.append((label, isa, flips, expected))
        print(f"  {label}: depth={isa.depth()}")

    # Submit
    print(f"\nSubmitting {len(isa_list)} PUBs × {SHOTS} shots...")
    sampler = Sampler(backend)
    job     = sampler.run([(isa,) for _, isa, _, _ in isa_list], shots=SHOTS)
    print(f"Job ID: {job.job_id()}")

    t0 = time.time()
    while True:
        st = str(job.status())
        if "DONE"   in st: print(f"Done in {time.time()-t0:.0f}s"); break
        if "ERROR"  in st or "CANCEL" in st: raise RuntimeError(st)
        time.sleep(5)

    # Analyse
    result = job.result()
    print()
    print("RESULTS")
    print("=" * 58)
    print(f"  {'Circuit':<8}  {'Expected':>14}  {'Got':>14}  {'f':>8}  {'Z':>8}  OK")
    print("  " + "-" * 58)

    records = []
    for i, (label, isa, flips, expected) in enumerate(isa_list):
        counts       = result[i].data.c.get_counts()
        dom, f, Z    = stats(counts, SHOTS)
        got          = fires(dom)
        match        = (got == sorted(expected))
        print(f"  {label:<8}  {str(sorted(expected)):>14}  {str(got):>14}"
              f"  {f:>8.4f}  {Z:>7.1f}σ  {'✓' if match else '✗'}")
        records.append({"label": label, "flips": flips,
                        "expected": sorted(expected), "got": got,
                        "dominant": dom, "f": f, "Z": Z,
                        "match": match, "counts": counts})

    n_ok = sum(r["match"] for r in records)
    print(f"\n  {n_ok}/{len(records)} circuits match prediction")

    # Kill test
    h30 = next(r for r in records if r["label"] == "h30")
    print()
    if h30["got"] == [3, 12]:
        print(f"KILL TEST ✓ — h(3,0) fires {{3, 12}} at Z = {h30['Z']:.0f}σ")
        print("  Horizontal twist physically confirmed.")
        print("  RP² is experimentally distinct from Klein bottle and toric codes.")
    else:
        print(f"KILL TEST ✗ — got {h30['got']} instead of [3, 12]")
        print("  Check circuit depth and transpiler seed.")

    # Save
    out = {
        "experiment": "rp2_existence",
        "claim": "RP² stabilizer code exists: both boundary twists confirmed simultaneously",
        "hardware": backend.name, "shots": SHOTS, "seed": SEED,
        "job_id": job.job_id(),
        "geometry": {"Lx": LX, "Ly": LY, "N_data": N_DATA, "N_syn": N_SYN},
        "p0": P0,
        "kill_test": "h(3,0) edge: RP² predicts {3,12}, Klein/toric predict {0,3}",
        "circuits": [
            {"label": r["label"], "flipped_edges": r["flips"],
             "expected_syndrome": r["expected"], "observed_syndrome": r["got"],
             "dominant_pattern": r["dominant"],
             "f_dominant": r["f"], "Z_sigma": r["Z"],
             "match": r["match"], "all_counts": r["counts"]}
            for r in records
        ]
    }
    fname = "rp2_existence_results.json"
    with open(fname, 'w') as fw:
        json.dump(out, fw, indent=2)
    print(f"\nSaved: {fname}")
    print("Upload to data/ folder or compare with data/04_rp2_existence.json")

if __name__ == "__main__":
    main()
