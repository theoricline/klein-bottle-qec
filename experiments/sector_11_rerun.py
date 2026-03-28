"""
sector_11_rerun.py
==================
PAPER 3 — Targeted re-run of |11>_L sector

The |11>_L sector requires flipping BOTH edges 0 and 3.
Syndrome 0 fires from both edges and cancels (GF(2) XOR).

CORRECTED PREDICTIONS:
  |11>_L Round 1: syndromes {1,3} → '00001010'  (NOT '00001011')
  |11>_L Klein R2: '10001010' (gate fires {0,7}, XOR {1,3} = {0,1,3,7}... check)
  |11>_L Toric R2: '10000011' (gate fires {3,7}, XOR {1,3} = {1,7}... check)

Previous job: d73u5ttkoquc73e251eg
  |11>_L R1 dominant was '00001010' at 4.9% → sector correctly prepared
  |11>_L R2 was weak (Z=5σ) due to noise from 2-edge prep
  This run: 16384 shots + seed scan for lower depth
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
SHOTS   = 16384       # double shots for weaker sector
SEEDS   = [77, 42, 12, 99]   # scan for lowest depth

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

# ── Corrected |11>_L predictions ─────────────────────────────────
PREP_11 = [h(0,0), h(3,0)]   # edges [0, 3]
X_L2    = v(3, 1)             # = 15

def compute_r1(prep, star_fn):
    syn = set()
    for e in prep:
        for y in range(LY):
            for x in range(LX):
                if e in star_fn(x, y):
                    syn.add(vi(x, y))
    b = [0]*8
    for s in syn: b[s] = 1
    return ''.join(str(x) for x in reversed(b)), sorted(syn)

def compute_r2(prep, gate_edge, star_fn):
    r1_syn = set()
    for e in prep:
        for y in range(LY):
            for x in range(LX):
                if e in star_fn(x, y):
                    r1_syn.add(vi(x, y))
    gate_syn = set()
    for y in range(LY):
        for x in range(LX):
            if gate_edge in star_fn(x, y):
                gate_syn.add(vi(x, y))
    combined = r1_syn ^ gate_syn
    b = [0]*8
    for s in combined: b[s] = 1
    return ''.join(str(x) for x in reversed(b)), sorted(combined)

r1_pat, r1_syn = compute_r1(PREP_11, klein_star)
klein_r2, klein_r2_syn = compute_r2(PREP_11, X_L2, klein_star)
toric_r2, toric_r2_syn = compute_r2(PREP_11, X_L2, toric_star)

print("="*60)
print("|11>_L SECTOR — CORRECTED RE-RUN")
print("="*60)
print(f"""
Prep edges: {PREP_11}  (h(0,0)=0 and h(3,0)=3)

Corrected predictions:
  Round 1: '{r1_pat}'  syndromes {r1_syn}
  Klein R2: '{klein_r2}'  syndromes {klein_r2_syn}
  Toric R2: '{toric_r2}'  syndromes {toric_r2_syn}
  Hamming(Klein, Toric): {sum(a!=b for a,b in zip(klein_r2,toric_r2))}

Previous run: R1 dominant was '00001010' = '{r1_pat}' ✓ (correct)
  R2 was weak (Z=5σ) — this run uses 2× shots + seed scan
""")

# ── Circuit builder ───────────────────────────────────────────────
def build_11_circuit(star_fn):
    qr_d = QuantumRegister(N_DATA, 'd')
    qr_s = QuantumRegister(N_SYN,  's')
    cr1  = ClassicalRegister(N_SYN, 'r1')
    cr2  = ClassicalRegister(N_SYN, 'r2')
    qc   = QuantumCircuit(qr_d, qr_s, cr1, cr2)

    # Prepare |11>_L — flip both edges
    for e in PREP_11:
        qc.x(qr_d[e])
    qc.barrier()

    # Round 1
    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])
    qc.measure(qr_s, cr1)
    qc.barrier()

    # Reset
    for i in range(N_SYN):
        qc.reset(qr_s[i])
    qc.barrier()

    # X_L2 gate
    qc.x(qr_d[X_L2])
    qc.barrier()

    # Round 2
    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])
    qc.measure(qr_s, cr2)
    return qc

# ── Build ─────────────────────────────────────────────────────────
print("Building circuits...")
qc_klein = build_11_circuit(klein_star)
qc_toric  = build_11_circuit(toric_star)
print(f"  Each: {qc_klein.num_qubits} qubits, "
      f"{qc_klein.count_ops().get('cx',0)} CX, "
      f"{qc_klein.count_ops().get('reset',0)} resets")

# ── Connect ───────────────────────────────────────────────────────
print("\nConnecting to IBM Fez...")
service = QiskitRuntimeService()
backend = service.backend("ibm_fez")
print(f"✅ {backend.num_qubits}q, {backend.status().pending_jobs} pending")

# ── Seed scan ─────────────────────────────────────────────────────
print(f"\nSeed scan {SEEDS} for minimum depth...")
best_seed, best_depth = SEEDS[0], 9999
for seed in SEEDS:
    pm  = generate_preset_pass_manager(
        optimization_level=3, backend=backend, seed_transpiler=seed)
    isa = pm.run(qc_klein)
    d   = isa.depth()
    print(f"  seed={seed}: Klein depth={d}")
    if d < best_depth:
        best_seed, best_depth = seed, d

print(f"\nBest seed: {best_seed} (depth={best_depth})")
pm = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=best_seed)

isa_klein = pm.run(qc_klein)
isa_toric  = pm.run(qc_toric)
print(f"  Klein depth: {isa_klein.depth()}")
print(f"  Toric depth:  {isa_toric.depth()}")

# ── Submit ────────────────────────────────────────────────────────
print(f"\nSubmitting 2 PUBs × {SHOTS} shots...")
sampler = Sampler(backend)
job = sampler.run([(isa_klein,), (isa_toric,)], shots=SHOTS)
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

def z_score(f_sig, f_noise):
    p0 = max(f_noise, 1/2**N_SYN)
    return (f_sig*SHOTS - SHOTS*p0) / np.sqrt(SHOTS*p0*(1-p0))

k_r1 = result[0].data.r1.get_counts()
k_r2 = result[0].data.r2.get_counts()
t_r1 = result[1].data.r1.get_counts()
t_r2 = result[1].data.r2.get_counts()

fk_r1 = freq(k_r1, r1_pat)
ft_r1 = freq(t_r1, r1_pat)
fk_r2 = freq(k_r2, klein_r2)
ft_r2 = freq(t_r2, toric_r2)

# Cross-contamination
fk_cross = freq(k_r2, toric_r2)
ft_cross  = freq(t_r2, klein_r2)

Zk = z_score(fk_r2, fk_cross)
Zt = z_score(ft_r2, ft_cross)

dom_k_r1 = max(k_r1, key=k_r1.get)
dom_t_r1 = max(t_r1, key=t_r1.get)
dom_k_r2 = max(k_r2, key=k_r2.get)
dom_t_r2 = max(t_r2, key=t_r2.get)

print("\n" + "="*60)
print("RESULTS")
print("="*60)
print(f"""
ROUND 1 — |11>_L sector confirmation:
  Target: '{r1_pat}'
  Klein: {fk_r1:.4f} ({fk_r1*100:.2f}%)  dominant='{dom_k_r1}'
  Toric:  {ft_r1:.4f} ({ft_r1*100:.2f}%)  dominant='{dom_t_r1}'

ROUND 2 — Holonomy:
  Klein target '{klein_r2}': {fk_r2:.4f} ({fk_r2*100:.2f}%)  Z={Zk:.0f}σ
  Toric target  '{toric_r2}':  {ft_r2:.4f} ({ft_r2*100:.2f}%)  Z={Zt:.0f}σ

  Klein on Toric target: {fk_cross:.4f} (cross-contamination)
  Toric on Klein target:  {ft_cross:.4f} (cross-contamination)

  Klein dominant: '{dom_k_r2}'  match={dom_k_r2==klein_r2}
  Toric dominant:  '{dom_t_r2}'  match={dom_t_r2==toric_r2}
""")

print("="*60)
print("VERDICT")
print("="*60)

k_match = dom_k_r2 == klein_r2
t_match = dom_t_r2 == toric_r2

if k_match and t_match and Zk > 20 and Zt > 20:
    print(f"""
✅ |11>_L CONFIRMED

  Klein '{klein_r2}' at {fk_r2*100:.2f}%, Z={Zk:.0f}σ  ✓
  Toric  '{toric_r2}'  at {ft_r2*100:.2f}%, Z={Zt:.0f}σ  ✓

  Combined with previous 6/8 confirmation, ALL FOUR SECTORS
  now confirm the non-orientable holonomy map:

  Klein X_L2 flips BOTH Z_L1 and Z_L2 (non-orientable) ✓
  Toric X_L2 flips ONLY Z_L2 (orientable) ✓

  Full sector transition table confirmed on hardware.
  Paper 3 holonomy evidence is complete.
""")
elif k_match or t_match:
    print(f"\n✓ PARTIAL — {'Klein' if k_match else 'Toric'} confirmed, "
          f"{'Toric' if k_match else 'Klein'} borderline")
    print(f"  Klein Z={Zk:.0f}σ  Toric Z={Zt:.0f}σ")
else:
    print(f"\n⚠️  Still weak — Klein Z={Zk:.0f}σ  Toric Z={Zt:.0f}σ")
    print("  |11>_L sector may require lower-noise backend or")
    print("  per-circuit seed optimisation to resolve cleanly.")
    print("  The 6/8 result from the main run is sufficient for Paper 3.")

import json
out = {
    'job_id':  job.job_id(),
    'shots':   SHOTS,
    'seed':    best_seed,
    'predictions': {'r1': r1_pat, 'klein_r2': klein_r2, 'toric_r2': toric_r2},
    'results': {
        'klein_r1': fk_r1, 'toric_r1': ft_r1,
        'klein_r2': fk_r2, 'toric_r2': ft_r2,
        'Zk': round(Zk,1), 'Zt': round(Zt,1),
        'klein_match': k_match, 'toric_match': t_match,
    }
}
with open('sector_11_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to sector_11_results.json")