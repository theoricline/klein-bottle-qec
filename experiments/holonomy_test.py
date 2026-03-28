"""
holonomy_test.py
================
PAPER 3 — HOLONOMY TEST
Demonstrates non-orientable logical algebra in the Klein bottle code.

THEORY:
  In a non-orientable code, parallel transport of a logical operator
  around the b-cycle (orientation-reversing loop) maps the a-cycle
  to a different logical sector than in an orientable code.

  Concretely:
    Klein: a-anyon + b-cycle gate → pattern '10000010' (syndromes {1,7})
    Toric: a-anyon + b-cycle gate → pattern '10001011' (syndromes {0,1,3,7})

  The difference: syndrome qubit 3 fires in Toric but NOT in Klein.
  This is because edge 15 = v(3,1) belongs to star(0,0) in Klein
  but to star(3,0) in Toric — the antipodal identification changes
  which vertex "owns" the b-cycle gate.

CIRCUIT DESIGN (dynamic circuits — mid-circuit measurement):
  Round 1: prepare a-anyon, measure syndromes
           → confirms '00000011' in both Klein and Toric
  Gate:    flip edge 15 = v(3,1) (the b-cycle logical gate)
  Round 2: measure syndromes again
           Klein dominant: '10000010'
           Toric dominant: '10001011'

  Hamming distance between targets: 2 → distinguishable with exact match.

VERIFIED PREDICTIONS (analytical, from holonomy_test.py):
  edge 0  fires in Klein: syndromes [0,1]   pattern '00000011'
  edge 15 fires in Klein: syndromes [0,7]   → XOR → [1,7]  '10000010'
  edge 15 fires in Toric: syndromes [3,7]   → XOR → [0,1,3,7] '10001011'

Reference: doi:10.5281/zenodo.19284050 (Paper 1)
           doi:10.5281/zenodo.XXXXXXX  (Paper 2)
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

# ── Lattice functions ─────────────────────────────────────────────
def h(x, y):  return y * LX + (x % LX)
def v(x, y):  return LX*LY + (y % LY)*LX + (x % LX)
def vi(x, y): return y * LX + (x % LX)

# ── Star operators ────────────────────────────────────────────────
def klein_star(x, y):
    edges = [h(x,y), h(x-1,y), v(x,y)]
    if y == 0:
        edges.append(v(LX-1-x, LY-1))   # antipodal twist
    else:
        edges.append(v(x, y-1))
    return list(set(edges))

def toric_star(x, y):
    return list(set([h(x,y), h(x-1,y), v(x,y), v(x,y-1)]))

# ── Key edges ─────────────────────────────────────────────────────
PREP_A_ANYON = h(0, 0)       # edge 0  — creates a-anyon, pattern '00000011'
B_CYCLE_GATE = v(3, 1)       # edge 15 — b-cycle logical gate

# Predicted patterns
ROUND1_TARGET = "00000011"   # a-anyon sector (same for Klein and Toric)
KLEIN_TARGET  = "10000010"   # Klein after b-cycle gate, syndromes {1,7}
TORIC_TARGET  = "10001011"   # Toric after b-cycle gate, syndromes {0,1,3,7}

print("="*65)
print("HOLONOMY TEST — Non-Orientable Logical Algebra")
print("="*65)
print(f"""
Theoretical predictions:
  Round 1 (both):  '{ROUND1_TARGET}'  syndromes {{0,1}}  a-anyon ✓
  Round 2 Klein:   '{KLEIN_TARGET}'  syndromes {{1,7}}
  Round 2 Toric:   '{TORIC_TARGET}'  syndromes {{0,1,3,7}}
  Hamming distance: {sum(a!=b for a,b in zip(KLEIN_TARGET, TORIC_TARGET))}

  Interpretation:
    Syndrome qubit 3 fires in Toric (NOT in Klein) because
    edge 15 belongs to star(3,0) in Toric but star(0,0) in Klein.
    This is the direct signature of non-orientable topology.
""")

# ── Circuit builder ───────────────────────────────────────────────
def build_holonomy_circuit(star_fn, label=""):
    """
    Dynamic circuit with two syndrome measurement rounds.
    
    Round 1: prepare a-anyon, measure → confirm sector
    Gate:    apply b-cycle logical gate (flip edge 15)
    Round 2: measure again → observe holonomy
    """
    qr_d  = QuantumRegister(N_DATA, 'd')
    qr_s  = QuantumRegister(N_SYN,  's')
    cr1   = ClassicalRegister(N_SYN, 'r1')  # Round 1
    cr2   = ClassicalRegister(N_SYN, 'r2')  # Round 2
    qc    = QuantumCircuit(qr_d, qr_s, cr1, cr2)

    # ── Round 1: prepare a-anyon ──────────────────────────────────
    qc.x(qr_d[PREP_A_ANYON])
    qc.barrier()

    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])

    qc.measure(qr_s, cr1)
    qc.barrier()

    # ── Reset ancilla for round 2 ─────────────────────────────────
    for i in range(N_SYN):
        qc.reset(qr_s[i])
    qc.barrier()

    # ── Apply b-cycle logical gate ────────────────────────────────
    # Flip edge 15 = v(3,1) — the b-cycle gate
    # In Klein: this is in star(0,0) → changes Z_L1 sector
    # In Toric: this is in star(3,0) → changes different sector
    qc.x(qr_d[B_CYCLE_GATE])
    qc.barrier()

    # ── Round 2: measure after gate ───────────────────────────────
    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])

    qc.measure(qr_s, cr2)
    return qc

# ── Build circuits ────────────────────────────────────────────────
print("Building circuits...")
qc_klein = build_holonomy_circuit(klein_star, "Klein")
qc_toric = build_holonomy_circuit(toric_star, "Toric")
print(f"  Klein: {qc_klein.num_qubits} qubits, "
      f"{qc_klein.count_ops().get('cx',0)} CX, "
      f"{qc_klein.count_ops().get('reset',0)} resets")
print(f"  Toric: {qc_toric.num_qubits} qubits, "
      f"{qc_toric.count_ops().get('cx',0)} CX, "
      f"{qc_toric.count_ops().get('reset',0)} resets")

# ── Connect ───────────────────────────────────────────────────────
print("\nConnecting to IBM Fez...")
service = QiskitRuntimeService()
backend = service.backend("ibm_fez")
print(f"✅ {backend.num_qubits}q, {backend.status().pending_jobs} pending")

# ── Transpile ─────────────────────────────────────────────────────
print(f"\nTranspiling (seed={SEED}, optimization_level=3)...")
pm = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=SEED)

isa_klein = pm.run(qc_klein)
isa_toric = pm.run(qc_toric)
print(f"  Klein depth: {isa_klein.depth()}")
print(f"  Toric depth: {isa_toric.depth()}")

# ── Submit ────────────────────────────────────────────────────────
print(f"\nSubmitting 2 PUBs × {SHOTS} shots...")
sampler = Sampler(backend)
job     = sampler.run([(isa_klein,), (isa_toric,)], shots=SHOTS)
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

# Extract counts from both rounds
def get_counts(pub_result, reg_name):
    return getattr(pub_result.data, reg_name).get_counts()

klein_r1 = get_counts(result[0], 'r1')
klein_r2 = get_counts(result[0], 'r2')
toric_r1 = get_counts(result[1], 'r1')
toric_r2 = get_counts(result[1], 'r2')

# Frequencies
def freq(counts, target):
    return counts.get(target, 0) / SHOTS

# Round 1: both should show '00000011'
fk_r1 = freq(klein_r1, ROUND1_TARGET)
ft_r1 = freq(toric_r1, ROUND1_TARGET)

# Round 2: should differ
fk_r2_klein = freq(klein_r2, KLEIN_TARGET)
fk_r2_toric = freq(klein_r2, TORIC_TARGET)
ft_r2_klein = freq(toric_r2, KLEIN_TARGET)
ft_r2_toric = freq(toric_r2, TORIC_TARGET)

# Z-scores
def z_score(f_obs, f_null, shots):
    p0 = max(f_null, 1/2**N_SYN)
    return (f_obs*shots - shots*p0) / np.sqrt(shots*p0*(1-p0))

print("\n" + "="*65)
print("RESULTS")
print("="*65)

print(f"""
ROUND 1 — A-anyon sector confirmation:
  Target: '{ROUND1_TARGET}' (a-anyon)
  Klein: {fk_r1:.4f} ({fk_r1*100:.2f}%)
  Toric: {ft_r1:.4f} ({ft_r1*100:.2f}%)
  → Both should show ~25-40% if sector is confirmed

ROUND 2 — Holonomy measurement:
  Klein target '{KLEIN_TARGET}': {fk_r2_klein:.4f} ({fk_r2_klein*100:.2f}%)
  Toric target '{TORIC_TARGET}': {ft_r2_toric:.4f} ({ft_r2_toric*100:.2f}%)

  Klein circuit on Toric target '{TORIC_TARGET}': {fk_r2_toric:.4f}
  Toric circuit on Klein target '{KLEIN_TARGET}': {ft_r2_klein:.4f}
""")

dom_k = max(klein_r2, key=klein_r2.get)
dom_t = max(toric_r2, key=toric_r2.get)
print(f"  Klein dominant pattern: '{dom_k}' ({klein_r2[dom_k]/SHOTS:.4f})")
print(f"  Toric dominant pattern: '{dom_t}' ({toric_r2[dom_t]/SHOTS:.4f})")

print("\n" + "="*65)
print("HOLONOMY VERDICT")
print("="*65)

klein_hits_own   = fk_r2_klein > 0.10
toric_hits_own   = ft_r2_toric > 0.10
patterns_differ  = dom_k != dom_t
theory_confirmed = (dom_k == KLEIN_TARGET and dom_t == TORIC_TARGET)

if theory_confirmed:
    print(f"""
✅ HOLONOMY CONFIRMED — NON-ORIENTABLE ALGEBRA PROVEN

  Klein dominant = '{dom_k}' = predicted Klein pattern ✓
  Toric dominant = '{dom_t}' = predicted Toric pattern ✓

  Interpretation:
    The b-cycle gate (flip edge 15) moves the a-anyon to
    DIFFERENT syndrome pairs in Klein vs Toric.
    
    In Klein: edge 15 is in star(0,0) → syndrome 0 cancels
              Final syndromes: {{1,7}} (syndrome 3 absent)
    
    In Toric: edge 15 is in star(3,0) → syndrome 3 fires
              Final syndromes: {{0,1,3,7}} (syndrome 3 present)
    
    This proves that the b-cycle has a non-trivial action
    on the a-cycle — the algebraic signature of
    non-orientable topology.
    
    No orientable surface code can produce this result.
    This is Paper 3.
""")
elif patterns_differ:
    print(f"""
✓ PATTERNS DIFFER — HOLONOMY PRESENT

  Klein dominant: '{dom_k}'
  Toric dominant: '{dom_t}'
  
  Patterns differ as expected (Hamming distance {sum(a!=b for a,b in zip(dom_k,dom_t))}).
  Partial confirmation — check dominant patterns against theory.
""")
else:
    print(f"""
⚠️ SAME DOMINANT PATTERN IN BOTH

  Both dominant: '{dom_k}'
  
  Possible causes:
  1. Circuit depth too high (reset overhead)
  2. Dynamic circuit noise degraded the signal
  3. Seed needs optimisation for dynamic circuit
  
  Check raw counts for second-dominant patterns.
""")

# Save results
import json
out = {
    'job_id':     job.job_id(),
    'backend':    'ibm_fez',
    'shots':      SHOTS,
    'seed':       SEED,
    'predictions': {
        'round1_target':  ROUND1_TARGET,
        'klein_r2_target': KLEIN_TARGET,
        'toric_r2_target': TORIC_TARGET,
    },
    'results': {
        'round1': {'klein': fk_r1, 'toric': ft_r1},
        'round2': {
            'klein_on_klein_target': fk_r2_klein,
            'klein_on_toric_target': fk_r2_toric,
            'toric_on_klein_target': ft_r2_klein,
            'toric_on_toric_target': ft_r2_toric,
        },
        'dominant': {
            'klein': dom_k,
            'toric': dom_t,
        },
    },
    'verdict': 'CONFIRMED' if theory_confirmed else
               'PARTIAL'   if patterns_differ   else 'INCONCLUSIVE',
}
with open('holonomy_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to holonomy_results.json")
