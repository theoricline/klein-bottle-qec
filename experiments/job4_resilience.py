"""
job4_resilience.py
==================
Job 4: Dynamic resilience verification

Tests whether Klein or Toric signal decays faster when
extra syndrome measurement rounds are added identically
to both circuits.

JOB 3 OBSERVATION:
  Klein dynamic overhead:  8.2% loss with 229 extra gates
  Toric dynamic overhead: 31.6% loss with 150 extra gates
  Klein degraded 5.9× more slowly per extra gate.
  
  CONFOUND: the extra gates were not structurally identical.
  Klein had 229 extra gates, Toric had 150.

THIS TEST — CLEAN COMPARISON:
  Add N identical syndrome rounds to BOTH codes.
  Each round: 32 CX + 8 resets (same for Klein and Toric at Lx=4).
  Measure f(N) = signal frequency after N extra rounds.
  
  Fit: f(N) = f(0) × exp(-λ × N)
  Compare decay constant λ_Klein vs λ_Toric.
  
  If λ_Klein < λ_Toric: Klein is genuinely more resilient.
  If λ_Klein ≈ λ_Toric: Job 3 finding was circuit-dependent.

CIRCUIT: 10 PUBs (N=0,1,2,3,4 × Klein + Toric)
  prep b-anyon → [N × (syndrome + reset)] → final syndrome → measure

Klein target: '10000001' (syndromes {0,7})
Toric target:  '10001000' (syndromes {3,7})
"""

import time
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# ── Parameters ────────────────────────────────────────────────────
LX, LY  = 4, 2
N_DATA  = 2 * LX * LY
N_SYN   = LX * LY
SHOTS   = 8192
SEED    = 77
N_ROUNDS = [0, 1, 2, 3, 4]   # extra syndrome rounds

PREP_EDGE    = 15   # v(3,1) — b-anyon from vacuum
KLEIN_TARGET = "10000001"
TORIC_TARGET = "10001000"

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

print("="*65)
print("JOB 4 — DYNAMIC RESILIENCE VERIFICATION")
print("="*65)
print(f"""
Adding N extra syndrome rounds identically to Klein and Toric.
Each extra round: 32 CX + 8 resets (identical for both).

Klein target: '{KLEIN_TARGET}'  Toric target: '{TORIC_TARGET}'
N values: {N_ROUNDS}
Total PUBs: {len(N_ROUNDS)*2}
""")

# ── Circuit builder ───────────────────────────────────────────────
def build_resilience_circuit(star_fn, n_extra_rounds):
    """
    prep b-anyon → [n_extra_rounds × (syndrome + reset)] → final syndrome
    """
    qr_d = QuantumRegister(N_DATA, 'd')
    qr_s = QuantumRegister(N_SYN,  's')
    cr   = ClassicalRegister(N_SYN, 'c')
    qc   = QuantumCircuit(qr_d, qr_s, cr)

    # Prepare b-anyon
    qc.x(qr_d[PREP_EDGE])
    qc.barrier()

    # N extra syndrome rounds (noise source)
    for _ in range(n_extra_rounds):
        for y in range(LY):
            for x in range(LX):
                anc = vi(x, y)
                for e in star_fn(x, y):
                    qc.cx(qr_d[e], qr_s[anc])
        # Reset ancilla (not measuring — just adding noise)
        for i in range(N_SYN):
            qc.reset(qr_s[i])
        qc.barrier()

    # Final syndrome measurement
    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])
    qc.measure(qr_s, cr)
    return qc

# ── Build 10 circuits ─────────────────────────────────────────────
print("Building 10 circuits...")
circuits   = []
pub_labels = []

for n in N_ROUNDS:
    for code, star_fn in [("Klein", klein_star), ("Toric", toric_star)]:
        qc = build_resilience_circuit(star_fn, n)
        circuits.append(qc)
        pub_labels.append(f"{code} N={n}")

print(f"  Each circuit: {circuits[0].num_qubits} qubits")

# ── Connect and transpile ─────────────────────────────────────────
print(f"\nConnecting to IBM Fez...")
service = QiskitRuntimeService()
backend = service.backend("ibm_fez")
print(f"✅ {backend.num_qubits}q, {backend.status().pending_jobs} pending")

pm = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=SEED)

print(f"Transpiling (seed={SEED})...")
isa_circuits = [pm.run(qc) for qc in circuits]

print(f"\n  {'Circuit':<16} {'Depth':>8} {'CX':>6}")
print("  " + "─"*34)
for label, isa in zip(pub_labels, isa_circuits):
    ops = isa.count_ops()
    print(f"  {label:<16} {isa.depth():>8} {ops.get('cx',0):>6}")

# ── Submit ────────────────────────────────────────────────────────
print(f"\nSubmitting {len(circuits)} PUBs × {SHOTS} shots...")
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

print("\n" + "="*65)
print("RESULTS — SIGNAL vs EXTRA ROUNDS")
print("="*65)

klein_f = []
toric_f  = []
klein_d = []
toric_d  = []

print(f"\n  {'Circuit':<16} {'f':>8} {'Depth':>8}  Dominant")
print("  " + "─"*50)

for i, (label, isa) in enumerate(zip(pub_labels, isa_circuits)):
    counts = result[i].data.c.get_counts()
    is_klein = 'Klein' in label
    target = KLEIN_TARGET if is_klein else TORIC_TARGET
    f = freq(counts, target)
    dom = max(counts, key=counts.get)
    depth = isa.depth()

    print(f"  {label:<16} {f:>7.4f}  {depth:>8}  '{dom}'")

    if is_klein:
        klein_f.append(f)
        klein_d.append(depth)
    else:
        toric_f.append(f)
        toric_d.append(depth)

# ── Fit exponential decay ─────────────────────────────────────────
print(f"\n{'='*65}")
print("DECAY ANALYSIS")
print(f"{'='*65}")

def fit_decay(N_vals, f_vals, label):
    """Fit f(N) = f0 * exp(-lambda * N)."""
    if f_vals[0] <= 0:
        return None, None
    log_f = np.log(np.maximum(f_vals, 1e-6) / f_vals[0])
    # Linear fit: log(f/f0) = -lambda * N
    N = np.array(N_vals, dtype=float)
    lam = -np.polyfit(N, log_f, 1)[0]
    f0 = f_vals[0]
    print(f"\n  {label}:")
    print(f"    f(N=0)  = {f0:.4f}")
    print(f"    λ       = {lam:.4f} per extra round")
    print(f"    f(N=1)  = {f0*np.exp(-lam):.4f} predicted")
    print(f"    half-life at N = {np.log(2)/lam:.1f} rounds")
    for n, f in zip(N_vals, f_vals):
        pred = f0 * np.exp(-lam * n)
        print(f"    N={n}: measured={f:.4f}  predicted={pred:.4f}  "
              f"{'✓' if abs(f-pred)<0.05 else '?'}")
    return lam, f0

print()
lam_k, f0_k = fit_decay(N_ROUNDS, klein_f, "Klein")
lam_t, f0_t  = fit_decay(N_ROUNDS, toric_f,  "Toric")

print(f"\n{'='*65}")
print("RESILIENCE VERDICT")
print(f"{'='*65}")

if lam_k is not None and lam_t is not None:
    ratio = lam_t / lam_k
    print(f"""
  Klein decay constant: λ_K = {lam_k:.4f} per extra round
  Toric decay constant: λ_T = {lam_t:.4f} per extra round
  Ratio λ_T/λ_K = {ratio:.2f}×
""")
    if ratio > 1.3:
        print(f"✅ KLEIN IS MORE RESILIENT")
        print(f"   Toric signal decays {ratio:.1f}× faster per extra syndrome round.")
        print(f"   The non-orientable stabilizer structure provides")
        print(f"   genuine dynamical resilience to repeated measurement.")
        print(f"   This is path-dependent — NOT purely circuit-depth-driven.")
    elif ratio > 0.8:
        print(f"→ EQUAL RESILIENCE")
        print(f"   Both codes decay at the same rate per extra round.")
        print(f"   The Job 3 finding was circuit-structure-dependent,")
        print(f"   not a genuine path advantage.")
        print(f"   The holonomy advantage is in gate COUNT only (1 vs 2).")
    else:
        print(f"→ TORIC MORE RESILIENT")
        print(f"   Unexpected. Check if toric static depth is much larger.")

import json
out = {
    'job_id': job.job_id(),
    'shots': SHOTS, 'seed': SEED,
    'n_rounds': N_ROUNDS,
    'klein': {'f': klein_f, 'depths': klein_d,
              'lambda': float(lam_k) if lam_k else None},
    'toric':  {'f': toric_f,  'depths': toric_d,
              'lambda': float(lam_t)  if lam_t  else None},
    'ratio': float(lam_t/lam_k) if (lam_k and lam_t and lam_k > 0) else None,
}
with open('job4_resilience_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to job4_resilience_results.json")