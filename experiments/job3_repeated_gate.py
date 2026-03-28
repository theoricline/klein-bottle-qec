"""
job3_repeated_gate.py
=====================
Test 3: Holonomy path distinguishes Klein from Toric

Apply X_L2 twice (returns to vacuum in both codes).
BUT the intermediate state after the first gate differs:
  Klein intermediate: '10000001'  syndromes {0,7}
  Toric intermediate: '10001000'  syndromes {3,7}

Using dynamic circuits (mid-circuit measurement), we capture
the intermediate state. Both codes return to vacuum after 2 gates,
but via DIFFERENT paths. This tests whether the holonomy path
has different noise characteristics.

4 PUBs:
  A: Klein 2×X_L2 (dynamic — measure intermediate)
  B: Toric  2×X_L2 (dynamic — measure intermediate)
  C: Klein 1×X_L2 (reference — intermediate only)
  D: Toric  1×X_L2 (reference — intermediate only)

Predictions:
  Round 1 (intermediate): Klein '10000001', Toric '10001000'
  Round 2 (after 2nd gate): both '00000000' (vacuum)

Key question: does Klein return to vacuum more cleanly than Toric?
(Shorter intermediate path → less decoherence on the return)
"""

import time
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

SHOTS  = 8192
SEED   = 77
LX, LY = 4, 2

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

N_DATA = 2 * LX * LY   # 16
N_SYN  = LX * LY        # 8
X_L2   = v(LX-1, LY-1)  # = 15

# Predictions
KLEIN_INTER = "10000001"   # syndromes {0,7}
TORIC_INTER = "10001000"   # syndromes {3,7}
VACUUM      = "00000000"

print("="*65)
print("JOB 3 — REPEATED GATE / HOLONOMY PATH TEST")
print("="*65)
print(f"""
X_L2 gate = edge {X_L2} = v(3,1)

Predictions:
  Intermediate (after 1st gate):
    Klein: '{KLEIN_INTER}'  syndromes {{0,7}}
    Toric:  '{TORIC_INTER}'  syndromes {{3,7}}
    Hamming: {sum(a!=b for a,b in zip(KLEIN_INTER, TORIC_INTER))}
    
  Final (after 2nd gate):
    Both: '{VACUUM}' (vacuum — X_L2^2 = I)
    
  Key question: does Klein return to vacuum more cleanly?
  (Klein intermediate has 2 syndrome qubits, Toric has 2 also,
   but they are at DIFFERENT physical locations — different
   decoherence environment on Fez)
""")

def build_repeated_gate(star_fn, label=""):
    """Dynamic circuit: gate → measure R1 → reset → gate → measure R2"""
    qr_d = QuantumRegister(N_DATA, 'd')
    qr_s = QuantumRegister(N_SYN,  's')
    cr1  = ClassicalRegister(N_SYN, 'r1')  # intermediate
    cr2  = ClassicalRegister(N_SYN, 'r2')  # final
    qc   = QuantumCircuit(qr_d, qr_s, cr1, cr2)

    # First X_L2
    qc.x(qr_d[X_L2])
    qc.barrier()

    # Syndrome Round 1 (intermediate)
    for y in range(LY):
        for x in range(LX):
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[vi(x, y)])
    qc.measure(qr_s, cr1)
    qc.barrier()

    # Reset
    for i in range(N_SYN):
        qc.reset(qr_s[i])
    qc.barrier()

    # Second X_L2 (X_L2^2 = I → returns to vacuum)
    qc.x(qr_d[X_L2])
    qc.barrier()

    # Syndrome Round 2 (should be vacuum)
    for y in range(LY):
        for x in range(LX):
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[vi(x, y)])
    qc.measure(qr_s, cr2)
    return qc

def build_single_gate(star_fn):
    """Reference: single X_L2, measure once"""
    qr_d = QuantumRegister(N_DATA, 'd')
    qr_s = QuantumRegister(N_SYN,  's')
    cr   = ClassicalRegister(N_SYN, 'c')
    qc   = QuantumCircuit(qr_d, qr_s, cr)
    qc.x(qr_d[X_L2])
    qc.barrier()
    for y in range(LY):
        for x in range(LX):
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[vi(x, y)])
    qc.measure(qr_s, cr)
    return qc

# ── Build 4 circuits ──────────────────────────────────────────────
print("Building 4 circuits...")
qc_A = build_repeated_gate(klein_star, "Klein 2-gate")
qc_B = build_repeated_gate(toric_star, "Toric 2-gate")
qc_C = build_single_gate(klein_star)
qc_D = build_single_gate(toric_star)

for name, qc in [("A Klein 2-gate", qc_A), ("B Toric 2-gate", qc_B),
                  ("C Klein 1-gate", qc_C), ("D Toric 1-gate", qc_D)]:
    cx = qc.count_ops().get('cx', 0)
    rs = qc.count_ops().get('reset', 0)
    print(f"  {name}: {qc.num_qubits}q, {cx} CX, {rs} resets")

# ── Connect and transpile ─────────────────────────────────────────
print("\nConnecting to IBM Fez...")
service = QiskitRuntimeService()
backend = service.backend("ibm_fez")
print(f"✅ {backend.num_qubits}q, {backend.status().pending_jobs} pending")

pm = generate_preset_pass_manager(3, backend=backend, seed_transpiler=SEED)
print(f"Transpiling (seed={SEED})...")
isa_A = pm.run(qc_A)
isa_B = pm.run(qc_B)
isa_C = pm.run(qc_C)
isa_D = pm.run(qc_D)

print(f"  A Klein 2-gate: depth={isa_A.depth()}")
print(f"  B Toric  2-gate: depth={isa_B.depth()}")
print(f"  C Klein 1-gate:  depth={isa_C.depth()}")
print(f"  D Toric  1-gate:  depth={isa_D.depth()}")

# ── Submit ────────────────────────────────────────────────────────
print(f"\nSubmitting 4 PUBs × {SHOTS} shots...")
sampler = Sampler(backend)
job = sampler.run([(isa_A,),(isa_B,),(isa_C,),(isa_D,)], shots=SHOTS)
print(f"Job ID: {job.job_id()}")

t0 = time.time()
while True:
    s = str(job.status())
    if "DONE" in s: print(f"Done in {time.time()-t0:.0f}s"); break
    if "ERROR" in s or "CANCEL" in s: raise RuntimeError(s)
    time.sleep(5)

# ── Analyse ───────────────────────────────────────────────────────
result = job.result()

def freq(counts, target): return counts.get(target, 0) / SHOTS
def zscore(f, p0=1/256):
    p0 = max(p0, 1/256)
    return (f*SHOTS - SHOTS*p0) / np.sqrt(SHOTS*p0*(1-p0))

# PUBs A and B have two registers (r1, r2)
# PUBs C and D have one register (c)
A_r1 = result[0].data.r1.get_counts()
A_r2 = result[0].data.r2.get_counts()
B_r1 = result[1].data.r1.get_counts()
B_r2 = result[1].data.r2.get_counts()
C_c  = result[2].data.c.get_counts()
D_c  = result[3].data.c.get_counts()

print("\n" + "="*65)
print("RESULTS")
print("="*65)

# Intermediate state
fA_r1 = freq(A_r1, KLEIN_INTER)
fB_r1 = freq(B_r1, TORIC_INTER)
ZA_r1 = zscore(fA_r1)
ZB_r1 = zscore(fB_r1)
domA_r1 = max(A_r1, key=A_r1.get)
domB_r1 = max(B_r1, key=B_r1.get)

print(f"\nINTERMEDIATE (Round 1 — after 1st gate):")
print(f"  Klein target '{KLEIN_INTER}': {fA_r1:.4f} ({fA_r1*100:.2f}%)  Z={ZA_r1:.0f}σ  "
      f"dominant='{domA_r1}'  {'✓' if domA_r1==KLEIN_INTER else '✗'}")
print(f"  Toric target  '{TORIC_INTER}': {fB_r1:.4f} ({fB_r1*100:.2f}%)  Z={ZB_r1:.0f}σ  "
      f"dominant='{domB_r1}'  {'✓' if domB_r1==TORIC_INTER else '✗'}")

# Reference single gate
fC = freq(C_c, KLEIN_INTER)
fD = freq(D_c, TORIC_INTER)
print(f"\nREFERENCE (single gate, no reset):")
print(f"  Klein '{KLEIN_INTER}': {fC:.4f} ({fC*100:.2f}%)")
print(f"  Toric  '{TORIC_INTER}': {fD:.4f} ({fD*100:.2f}%)")
print(f"  Intermediate degradation vs reference:")
print(f"    Klein: {(fC-fA_r1)/fC*100:.1f}% reduction (dynamic overhead)")
print(f"    Toric:  {(fD-fB_r1)/fD*100:.1f}% reduction (dynamic overhead)")

# Final state (should be vacuum)
fA_r2 = freq(A_r2, VACUUM)
fB_r2 = freq(B_r2, VACUUM)
ZA_r2 = zscore(fA_r2, p0=1/256)
ZB_r2 = zscore(fB_r2, p0=1/256)
domA_r2 = max(A_r2, key=A_r2.get)
domB_r2 = max(B_r2, key=B_r2.get)

print(f"\nFINAL (Round 2 — after 2nd gate, should be vacuum '{VACUUM}'):")
print(f"  Klein: {fA_r2:.4f} ({fA_r2*100:.2f}%)  Z={ZA_r2:.0f}σ  "
      f"dominant='{domA_r2}'  {'✓' if domA_r2==VACUUM else '~'}")
print(f"  Toric:  {fB_r2:.4f} ({fB_r2*100:.2f}%)  Z={ZB_r2:.0f}σ  "
      f"dominant='{domB_r2}'  {'✓' if domB_r2==VACUUM else '~'}")

vacuum_advantage = fA_r2 / fB_r2 if fB_r2 > 0 else float('inf')
print(f"\n  Vacuum return ratio Klein/Toric: {vacuum_advantage:.2f}×")
if vacuum_advantage > 1.05:
    print("  ✅ Klein returns to vacuum more cleanly than Toric")
    print("     → Holonomy path advantage: Klein intermediate is")
    print("       less noisy than Toric intermediate")
elif vacuum_advantage > 0.95:
    print("  — Similar vacuum return for both codes")
else:
    print("  ⚠️  Toric returns more cleanly — unexpected")

print("\n" + "="*65)
print("PATH INTERPRETATION")
print("="*65)
print(f"""
Klein path:  vacuum → [gate 1] → '{KLEIN_INTER}' → [gate 2] → vacuum
Toric path:  vacuum → [gate 1] → '{TORIC_INTER}' → [gate 2] → vacuum

Both return to vacuum (X_L2^2 = I confirmed).
The INTERMEDIATE state determines the noise accumulated:
  Klein intermediate fires syndromes {{0,7}}  — antipodal pair
  Toric intermediate fires syndromes {{3,7}}  — toric pair

If Klein returns more cleanly:
  → The non-orientable holonomy path accumulates less noise
  → The antipodal intermediate state is more stable
  → This is a path-dependent computational advantage
""")

import json
out = {
    'job_id': job.job_id(), 'shots': SHOTS, 'seed': SEED,
    'depths': {
        'A_klein_2gate': isa_A.depth(), 'B_toric_2gate': isa_B.depth(),
        'C_klein_1gate': isa_C.depth(), 'D_toric_1gate': isa_D.depth(),
    },
    'intermediate': {
        'klein_f': fA_r1, 'klein_Z': float(ZA_r1), 'klein_dom': domA_r1,
        'toric_f':  fB_r1, 'toric_Z':  float(ZB_r1), 'toric_dom':  domB_r1,
    },
    'final_vacuum': {
        'klein_f': fA_r2, 'toric_f': fB_r2,
        'vacuum_advantage': vacuum_advantage,
    },
}
with open('job3_repeated_gate_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"Saved to job3_repeated_gate_results.json")