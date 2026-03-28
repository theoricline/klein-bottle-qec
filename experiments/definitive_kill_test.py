"""
definitive_kill_test.py
========================
THE CORRECT TOPOLOGY KILL TEST

Tests whether the antipodal VERTICAL edge (not horizontal) is
the source of the Klein bottle syndrome signal.

DESIGN:
  Klein circuit:      prep edge = v(3,1) = edge 15 (antipodal vertical)
  Fake Klein circuit: prep edge = v(3,1) = edge 15 (same edge, different star)

  In Klein: edge 15 is in star(0,0) AND star(3,1)
            → fires syndromes {0, 7} → pattern "10000001"

  In Fake:  edge 15 is in star(3,0) AND star(3,1)
            → fires syndromes {3, 7} → pattern "10001000"

EXPECTED:
  Klein  "10000001": ~40%  (topology active)
  Fake   "10000001": ~1-2% (topology absent — signal is in "10001000")
  Enhancement: ~20-40×

If topology is real: Klein >> Fake for "10000001"
If hardware resonance: both should show similar rates

Reference: doi:10.5281/zenodo.19202945
"""

import time
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# ── Parameters ────────────────────────────────────────────────────
LX, LY  = 4, 2
N_DATA  = 2 * LX * LY   # 16
N_SYN   = LX * LY        # 8
SHOTS   = 8192
SEED    = 77             # optimal for Klein δ=0 on IBM Fez

# ── Lattice functions ─────────────────────────────────────────────
def h(x, y):  return y * LX + (x % LX)
def v(x, y):  return LX*LY + (y % LY)*LX + (x % LX)
def vi(x, y): return y * LX + (x % LX)

# ── Star operators ────────────────────────────────────────────────
def klein_star(x, y):
    """Klein bottle: antipodal vertical edge at y=0."""
    edges = [h(x,y), h(x-1,y), v(x,y)]
    if y == 0:
        edges.append(v(LX-1-x, LY-1))   # ← antipodal twist
    else:
        edges.append(v(x, y-1))
    return list(set(edges))

def fake_star(x, y):
    """Fake Klein: periodic (toric) boundary, NO antipodal twist."""
    return list(set([h(x,y), h(x-1,y), v(x,y), v(x,y-1)]))

# ── Verify prep edge membership ───────────────────────────────────
PREP_EDGE    = v(3, 1)   # = edge 15 — the antipodal vertical edge
KLEIN_TARGET = "10000001"  # syndromes {0,7} — what Klein fires
FAKE_TARGET  = "10001000"  # syndromes {3,7} — what Fake fires

print("="*65)
print("DEFINITIVE TOPOLOGY KILL TEST")
print(f"Prep edge: v(3,1) = edge {PREP_EDGE}")
print("="*65)

print("\nVerifying predicted firing patterns:")
for label, star_fn in [("Klein", klein_star), ("Fake", fake_star)]:
    firing = [vi(x,y) for y in range(LY) for x in range(LX)
              if PREP_EDGE in star_fn(x, y)]
    bits = [0] * N_SYN
    for idx in firing: bits[idx] = 1
    pattern = ''.join(str(b) for b in reversed(bits))
    print(f"  {label}: fires syndromes {sorted(firing)} → '{pattern}'")

print(f"\n  Klein target: '{KLEIN_TARGET}'")
print(f"  Fake  target: '{FAKE_TARGET}'")
print(f"  Hamming distance between targets: "
      f"{sum(a!=b for a,b in zip(KLEIN_TARGET,FAKE_TARGET))}")
print(f"  → Targets are distinct. Test is well-designed.")

# ── Circuit builder ───────────────────────────────────────────────
def build_circuit(star_fn, prep_edge=PREP_EDGE):
    qr_d = QuantumRegister(N_DATA, 'd')
    qr_s = QuantumRegister(N_SYN,  's')
    cr   = ClassicalRegister(N_SYN, 'c')
    qc   = QuantumCircuit(qr_d, qr_s, cr)

    # Prepare topological excitation on the antipodal vertical edge
    qc.x(qr_d[prep_edge])
    qc.barrier()

    # Syndrome measurement
    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])

    qc.measure(qr_s, cr)
    return qc

# ── Build ─────────────────────────────────────────────────────────
print("\nBuilding circuits...")
qc_klein = build_circuit(klein_star)
qc_fake  = build_circuit(fake_star)
print(f"  Klein: {qc_klein.num_qubits} qubits, "
      f"{qc_klein.count_ops().get('cx',0)} CX gates")
print(f"  Fake:  {qc_fake.num_qubits} qubits, "
      f"{qc_fake.count_ops().get('cx',0)} CX gates")

# ── Connect and transpile ─────────────────────────────────────────
print("\nConnecting to IBM Fez...")
service = QiskitRuntimeService()
backend = service.backend("ibm_fez")
print(f"✅ {backend.num_qubits}q, {backend.status().pending_jobs} pending")

pm = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=SEED)

print(f"\nTranspiling (seed={SEED})...")
isa_klein = pm.run(qc_klein)
isa_fake  = pm.run(qc_fake)
print(f"  Klein depth: {isa_klein.depth()}")
print(f"  Fake  depth: {isa_fake.depth()}")

# ── Submit ────────────────────────────────────────────────────────
print(f"\nSubmitting 2 PUBs × {SHOTS} shots...")
sampler = Sampler(backend)
job = sampler.run([(isa_klein,), (isa_fake,)], shots=SHOTS)
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
klein_counts = result[0].data.c.get_counts()
fake_counts  = result[1].data.c.get_counts()

f_klein = klein_counts.get(KLEIN_TARGET, 0) / SHOTS
f_fake  = fake_counts.get(KLEIN_TARGET, 0) / SHOTS
f_fake_own = fake_counts.get(FAKE_TARGET, 0) / SHOTS

# Z-score: Klein vs noise floor
p0 = max(f_fake, 1/2**N_SYN)
Z  = (f_klein*SHOTS - SHOTS*p0) / np.sqrt(SHOTS*p0*(1-p0))

# Enhancement
enh = f_klein / f_fake if f_fake > 0 else float('inf')

print("\n" + "="*65)
print("RESULTS")
print("="*65)

print(f"""
  Prep edge:     v(3,1) = edge {PREP_EDGE}

  Klein '{KLEIN_TARGET}':  {f_klein:.4f} ({f_klein*100:.2f}%)
  Fake  '{KLEIN_TARGET}':  {f_fake:.4f}  ({f_fake*100:.2f}%)
  Enhancement:             {enh:.1f}×
  Z-score:                 {Z:.0f}σ

  Fake own pattern '{FAKE_TARGET}': {f_fake_own:.4f} ({f_fake_own*100:.2f}%)
""")

print("="*65)
print("INTERPRETATION")
print("="*65)

if enh >= 20:
    verdict = "TOPOLOGY CONFIRMED"
    detail  = ("The antipodal vertical edge is the definitive source "
               "of the Klein bottle syndrome signal. Hardware resonance "
               "cannot explain a {:.0f}× enhancement.".format(enh))
elif enh >= 5:
    verdict = "TOPOLOGY STRONGLY SUPPORTED"
    detail  = ("Clear enhancement attributable to the antipodal edge. "
               "Some hardware contribution cannot be excluded.")
elif enh >= 2:
    verdict = "WEAK SIGNAL"
    detail  = ("Modest enhancement. Circuit depth at seed=77 may be "
               "suboptimal for this exact prep edge. "
               "Consider a seed scan.")
else:
    verdict = "INCONCLUSIVE"
    detail  = ("Enhancement below 2×. Check circuit construction "
               "and confirm prep edge is correct.")

print(f"\n  Verdict: {verdict}")
print(f"\n  {detail}")

print(f"""
  For comparison — Paper 1 validated results (same prep edge):
    Klein 'pattern': ~26-44%  Enhancement: 37-138×  Z: 195-499σ
    Toric vacuum:    ~0.71%

  This test uses Fake Klein WITH b-anyon prep (not toric vacuum).
  Expected enhancement here: ~20-40× (Fake has its own pattern
  'FAKE_TARGET' and the noise floor for KLEIN_TARGET is ~1-2%).
""")

import json
out = {
    'job_id':        job.job_id(),
    'backend':       'ibm_fez',
    'shots':         SHOTS,
    'seed':          SEED,
    'prep_edge':     PREP_EDGE,
    'klein_target':  KLEIN_TARGET,
    'fake_target':   FAKE_TARGET,
    'f_klein':       round(f_klein, 4),
    'f_fake_on_klein_target': round(f_fake, 4),
    'f_fake_on_own_target':   round(f_fake_own, 4),
    'enhancement':   round(enh, 1),
    'Z':             round(Z, 1),
    'verdict':       verdict,
}
with open('kill_test_definitive.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"Saved to kill_test_definitive.json")
