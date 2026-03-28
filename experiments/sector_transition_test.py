"""
sector_transition_test.py
==========================
PAPER 3 — TEST A: Full Sector Transition Table

Verifies the complete holonomy map of X_L2 across all four
logical sectors, for both Klein bottle and Toric codes.

THEORY:
  X_L2 = flip edge 15 = v(3,1), the b-cycle logical gate.

  Klein: edge 15 in star(0,0) AND star(3,1) → fires syndromes {0,7}
  Toric: edge 15 in star(3,0) AND star(3,1) → fires syndromes {3,7}

  Full transition table (Round1 → Round2):
  ┌─────────┬────────────┬─────────────┬─────────────┐
  │ Sector  │ Round 1    │ Klein R2    │ Toric R2    │
  ├─────────┼────────────┼─────────────┼─────────────┤
  │ |00>_L  │ 00000000   │ 10000001    │ 10001000    │
  │ |10>_L  │ 00000011   │ 10000010    │ 10001011    │ ← confirmed
  │ |01>_L  │ 00001001   │ 10001000    │ 10000001    │
  │ |11>_L  │ 00001011   │ 10001010    │ 10000011    │
  └─────────┴────────────┴─────────────┴─────────────┘

  Klein: X_L2 flips BOTH Z_L1 and Z_L2 (non-orientable algebra)
  Toric: X_L2 flips only Z_L2 (orientable algebra)
  Hamming distance between Klein and Toric R2: 2 in all cases.

  Elegant structure: Klein and Toric R2 patterns are sector-swapped.
  Klein |00>_L R2 = Toric |01>_L R2 — the twist permutes sectors.

CIRCUIT: dynamic circuits, mid-circuit reset (IBM Heron r2 native)
  8 PUBs: 4 sectors × Klein + 4 sectors × Toric
  Each PUB: prep → syndrome Round 1 → reset → gate → syndrome Round 2

Reference: doi:10.5281/zenodo.19284050 (Paper 1)
           doi:10.5281/zenodo.19286677 (Paper 2)
"""

import time
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# ── Parameters ────────────────────────────────────────────────────
LX, LY  = 4, 2
N_DATA  = 2 * LX * LY    # 16
N_SYN   = LX * LY         # 8
SHOTS   = 8192
SEED    = 77

# ── Lattice ───────────────────────────────────────────────────────
def h(x, y):  return y * LX + (x % LX)
def v(x, y):  return LX*LY + (y % LY)*LX + (x % LX)
def vi(x, y): return y * LX + (x % LX)

def klein_star(x, y):
    edges = [h(x,y), h(x-1,y), v(x,y)]
    if y == 0: edges.append(v(LX-1-x, LY-1))
    else:      edges.append(v(x, y-1))
    return list(set(edges))

def toric_star(x, y):
    return list(set([h(x,y), h(x-1,y), v(x,y), v(x,y-1)]))

# ── Sector definitions ────────────────────────────────────────────
# prep_edges: data qubits to flip before syndrome measurement
SECTORS = {
    '|00>_L': [],        # vacuum
    '|10>_L': [h(0,0)],  # a-anyon   = edge 0
    '|01>_L': [h(3,0)],  # b-anyon   = edge 3
    '|11>_L': [h(0,0), h(3,0)],  # both = edges 0,3
}

# X_L2 gate: flip edge 15 = v(3,1)
X_L2_EDGE = v(3, 1)   # = 15

# Analytically verified predictions
PREDICTIONS = {
    '|00>_L': {'r1': '00000000', 'klein': '10000001', 'toric': '10001000'},
    '|10>_L': {'r1': '00000011', 'klein': '10000010', 'toric': '10001011'},
    '|01>_L': {'r1': '00001001', 'klein': '10001000', 'toric': '10000001'},
    '|11>_L': {'r1': '00001011', 'klein': '10001010', 'toric': '10000011'},
}

print("="*65)
print("SECTOR TRANSITION TEST — Full Holonomy Map")
print("="*65)
print(f"\nX_L2 gate: edge {X_L2_EDGE} = v(3,1)")
print(f"\nPredictions:")
print(f"  {'Sector':<10} {'Round1':<12} {'Klein R2':<14} {'Toric R2':<14} Hamming")
print("  " + "─"*58)
for s, p in PREDICTIONS.items():
    d = sum(a!=b for a,b in zip(p['klein'], p['toric']))
    conf = " ← confirmed" if s == '|10>_L' else ""
    print(f"  {s:<10} {p['r1']:<12} {p['klein']:<14} {p['toric']:<14} {d}{conf}")

# ── Circuit builder ───────────────────────────────────────────────
def build_circuit(star_fn, prep_edges, label=""):
    """
    Dynamic circuit: prep → Round1 → reset → X_L2 gate → Round2
    Returns 16-bit classical register: [r1 (8 bits) | r2 (8 bits)]
    """
    qr_d = QuantumRegister(N_DATA, 'd')
    qr_s = QuantumRegister(N_SYN,  's')
    cr1  = ClassicalRegister(N_SYN, 'r1')
    cr2  = ClassicalRegister(N_SYN, 'r2')
    qc   = QuantumCircuit(qr_d, qr_s, cr1, cr2)

    # Prepare logical sector
    for e in prep_edges:
        qc.x(qr_d[e])
    qc.barrier()

    # Round 1: syndrome measurement
    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])
    qc.measure(qr_s, cr1)
    qc.barrier()

    # Reset ancilla
    for i in range(N_SYN):
        qc.reset(qr_s[i])
    qc.barrier()

    # Apply X_L2 gate
    qc.x(qr_d[X_L2_EDGE])
    qc.barrier()

    # Round 2: syndrome measurement
    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])
    qc.measure(qr_s, cr2)

    return qc

# ── Build all 8 circuits ──────────────────────────────────────────
print(f"\nBuilding 8 circuits (4 sectors × Klein + Toric)...")
circuits = []
pub_labels = []

for code_name, star_fn in [("Klein", klein_star), ("Toric", toric_star)]:
    for sector, prep in SECTORS.items():
        qc = build_circuit(star_fn, prep)
        circuits.append(qc)
        pub_labels.append(f"{code_name} {sector}")

cx_count = circuits[0].count_ops().get('cx', 0)
reset_count = circuits[0].count_ops().get('reset', 0)
print(f"  Each circuit: {circuits[0].num_qubits} qubits, "
      f"{cx_count} CX gates, {reset_count} resets")

# ── Connect and transpile ─────────────────────────────────────────
print(f"\nConnecting to IBM Fez...")
service = QiskitRuntimeService()
backend = service.backend("ibm_fez")
print(f"✅ {backend.num_qubits}q, {backend.status().pending_jobs} pending")

pm = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=SEED)

print(f"Transpiling 8 circuits (seed={SEED})...")
isa_circuits = [pm.run(qc) for qc in circuits]
depths = [c.depth() for c in isa_circuits]
print(f"  Klein depths: {depths[:4]}")
print(f"  Toric depths: {depths[4:]}")

# ── Submit ────────────────────────────────────────────────────────
print(f"\nSubmitting 8 PUBs × {SHOTS} shots...")
sampler = Sampler(backend)
job = sampler.run([(c,) for c in isa_circuits], shots=SHOTS)
print(f"Job ID: {job.job_id()}")

t0 = time.time()
while True:
    status = str(job.status())
    if "DONE" in status:
        print(f"Done in {time.time()-t0:.0f}s")
        break
    if "ERROR" in status or "CANCEL" in status:
        raise RuntimeError(f"Job failed: {status}")
    time.sleep(5)

# ── Analyse ───────────────────────────────────────────────────────
result = job.result()

def freq(counts, target):
    return counts.get(target, 0) / SHOTS

def z_score(f_sig, f_noise, shots=SHOTS):
    p0 = max(f_noise, 1/2**N_SYN)
    return (f_sig*shots - shots*p0) / np.sqrt(shots*p0*(1-p0))

print("\n" + "="*65)
print("RESULTS — ROUND 1 (sector confirmation)")
print("="*65)
print(f"\n  {'Circuit':<22} {'Target':<12} {'f_R1':<10} {'Dominant'}")
print("  " + "─"*52)

# PUB order: Klein|00>, Klein|10>, Klein|01>, Klein|11>,
#            Toric|00>, Toric|10>, Toric|01>, Toric|11>
sectors_list = list(SECTORS.keys())

for i, label in enumerate(pub_labels):
    r1_counts = result[i].data.r1.get_counts()
    sector = sectors_list[i % 4]
    target_r1 = PREDICTIONS[sector]['r1']
    f_r1 = freq(r1_counts, target_r1)
    dom = max(r1_counts, key=r1_counts.get)
    print(f"  {label:<22} '{target_r1}'   {f_r1:.3f}      '{dom}'")

print("\n" + "="*65)
print("RESULTS — ROUND 2 (holonomy measurement)")
print("="*65)
print(f"\n  {'Circuit':<22} {'Target':<12} {'f_R2':<10} {'Z':>6}  {'Match'}")
print("  " + "─"*58)

all_match = True
results_table = {}

for i, label in enumerate(pub_labels):
    r2_counts = result[i].data.r2.get_counts()
    sector = sectors_list[i % 4]
    code = "klein" if i < 4 else "toric"
    target_r2 = PREDICTIONS[sector][code]

    # Noise: the OTHER code's target for same sector
    other_code = "toric" if code == "klein" else "klein"
    noise_target = PREDICTIONS[sector][other_code]

    f_sig   = freq(r2_counts, target_r2)
    f_noise = freq(r2_counts, noise_target)
    Z       = z_score(f_sig, f_noise)
    dom     = max(r2_counts, key=r2_counts.get)
    match   = dom == target_r2

    if not match: all_match = False

    print(f"  {label:<22} '{target_r2}'   {f_sig:.3f}   {Z:>6.0f}σ  "
          f"{'✓' if match else '✗'}")
    results_table[label] = {
        'sector': sector, 'code': code,
        'target': target_r2, 'f': f_sig, 'Z': Z, 'match': match,
        'dominant': dom,
    }

print("\n" + "="*65)
print("VERDICT")
print("="*65)

klein_matches = sum(1 for l,r in results_table.items()
                    if 'Klein' in l and r['match'])
toric_matches = sum(1 for l,r in results_table.items()
                    if 'Toric' in l and r['match'])

print(f"\n  Klein: {klein_matches}/4 sectors match predicted pattern")
print(f"  Toric: {toric_matches}/4 sectors match predicted pattern")

if klein_matches == 4 and toric_matches == 4:
    print(f"""
✅ COMPLETE HOLONOMY MAP CONFIRMED

  All 8 circuits produce their theoretically predicted patterns.

  Klein: X_L2 flips BOTH Z_L1 and Z_L2 — non-orientable algebra ✓
  Toric: X_L2 flips ONLY Z_L2 — orientable algebra ✓

  The b-cycle logical gate acts differently depending on whether
  the code is orientable or non-orientable. This is proven across
  all four logical sectors, not just one.

  Klein and Toric Round 2 patterns are sector-permuted:
  the non-orientable twist maps sectors to their duals.

  This is Paper 3.
""")
elif klein_matches + toric_matches >= 6:
    print(f"\n✓ STRONG CONFIRMATION — {klein_matches+toric_matches}/8 sectors match")
    print("  Partial noise in some sectors — check depths and Z-scores")
else:
    print(f"\n⚠️  Only {klein_matches+toric_matches}/8 match — check circuit design")

# Save results
import json
out = {
    'job_id':      job.job_id(),
    'backend':     'ibm_fez',
    'shots':       SHOTS,
    'seed':        SEED,
    'x_l2_edge':   X_L2_EDGE,
    'predictions': PREDICTIONS,
    'results':     {l: {k: (float(v) if isinstance(v, float) else v)
                        for k,v in r.items()}
                    for l,r in results_table.items()},
    'verdict': {
        'klein_matches': klein_matches,
        'toric_matches': toric_matches,
        'confirmed': klein_matches == 4 and toric_matches == 4,
    }
}
with open('sector_transition_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"Saved to sector_transition_results.json")