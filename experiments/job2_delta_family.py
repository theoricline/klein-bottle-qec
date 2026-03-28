"""
job2_delta_family.py
====================
Job 2: Gate depth advantage across the δ-family

Tests whether the 1-gate vs 2-gate advantage holds for all
δ values in the C(δ) family.

PREDICTIONS (δ=2 skipped — Klein and Toric give same pattern
for that gate choice):
  δ=0: Klein '10000001'  Toric '10001011'  Hamming=2  ✓ (confirmed)
  δ=1: Klein '00010001'  Toric '00010010'  Hamming=2
  δ=3: Klein '01000001'  Toric '01000111'  Hamming=2

Each PUB:
  Klein 1-gate: prep vacuum, flip antipodal edge (X_L2 only)
  Toric 2-gate: prep vacuum, flip edge 0 (X_L1) + antipodal edge (X_L2)
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

# ── Lattice ───────────────────────────────────────────────────────
def h(x, y):  return y * LX + (x % LX)
def v(x, y):  return LX*LY + (y % LY)*LX + (x % LX)
def vi(x, y): return y * LX + (x % LX)

def klein_star(x, y, delta=0):
    edges = [h(x,y), h(x-1,y), v(x,y)]
    if y == 0:
        edges.append(v((LX-1-x+delta) % LX, LY-1))
    else:
        edges.append(v(x, y-1))
    return list(set(edges))

def toric_star(x, y):
    return list(set([h(x,y), h(x-1,y), v(x,y), v(x,y-1)]))

# ── Verified predictions ──────────────────────────────────────────
DELTAS = [0, 1, 3]   # skip δ=2 (Hamming=0 for this gate choice)

PREDICTIONS = {
    0: {'prep': v(3,1), 'klein': '10000001', 'toric': '10001011'},
    1: {'prep': v(0,1), 'klein': '00010001', 'toric': '00010010'},
    3: {'prep': v(2,1), 'klein': '01000001', 'toric': '01000111'},
}

print("="*65)
print("JOB 2 — δ-FAMILY GATE DEPTH ADVANTAGE")
print("="*65)
print(f"\n{'δ':<5} {'Prep edge':<12} {'Klein target':<16} {'Toric target':<16} Hamming")
print("─"*65)
for d in DELTAS:
    p = PREDICTIONS[d]
    ham = sum(a!=b for a,b in zip(p['klein'], p['toric']))
    print(f"  δ={d}  edge {p['prep']:<8}  '{p['klein']}'       '{p['toric']}'       {ham}")
print(f"\n  (δ=2 skipped: same pattern for both codes with this gate)")

# ── Circuit builder ───────────────────────────────────────────────
def build_circuit(star_fn, gate_edges):
    """
    Static circuit: prep + gate(s) + syndrome measurement.
    gate_edges: list of data qubit indices to flip (the logical gate).
    """
    qr_d = QuantumRegister(N_DATA, 'd')
    qr_s = QuantumRegister(N_SYN,  's')
    cr   = ClassicalRegister(N_SYN, 'c')
    qc   = QuantumCircuit(qr_d, qr_s, cr)

    # Apply logical gate(s) — no b-anyon prep, start from vacuum
    for e in gate_edges:
        qc.x(qr_d[e])
    qc.barrier()

    # Syndrome measurement
    for y in range(LY):
        for x in range(LX):
            anc = vi(x, y)
            for e in star_fn(x, y):
                qc.cx(qr_d[e], qr_s[anc])
    qc.measure(qr_s, cr)
    return qc

# ── Build 6 circuits (3 δ × Klein + Toric) ───────────────────────
print(f"\nBuilding 6 circuits (3 δ values × Klein + Toric)...")
circuits  = []
pub_labels = []

for delta in DELTAS:
    p = PREDICTIONS[delta]
    gate_edge = p['prep']   # X_L2 = flip the antipodal edge

    # Klein 1-gate
    qc_k = build_circuit(
        lambda x, y, d=delta: klein_star(x, y, d),
        [gate_edge])
    circuits.append(qc_k)
    pub_labels.append(f"Klein δ={delta}")

    # Toric 2-gate (X_L1=edge 0, X_L2=gate_edge)
    qc_t = build_circuit(toric_star, [0, gate_edge])
    circuits.append(qc_t)
    pub_labels.append(f"Toric δ={delta}")

cx_count = circuits[0].count_ops().get('cx', 0)
print(f"  Each circuit: {circuits[0].num_qubits} qubits, ~{cx_count} CX gates")

# ── Connect and transpile ─────────────────────────────────────────
print(f"\nConnecting to IBM Fez...")
service = QiskitRuntimeService()
backend = service.backend("ibm_fez")
print(f"✅ {backend.num_qubits}q, {backend.status().pending_jobs} pending")

pm = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=SEED)

print(f"Transpiling (seed={SEED})...")
isa_circuits = [pm.run(qc) for qc in circuits]

print(f"\n  {'Circuit':<18} {'Depth':>6}")
print("  " + "─"*26)
for label, isa in zip(pub_labels, isa_circuits):
    print(f"  {label:<18} {isa.depth():>6}")

# ── Submit ────────────────────────────────────────────────────────
print(f"\nSubmitting 6 PUBs × {SHOTS} shots...")
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

def z_score(f_sig, f_noise):
    p0 = max(f_noise, 1/2**N_SYN)
    return (f_sig*SHOTS - SHOTS*p0) / np.sqrt(SHOTS*p0*(1-p0))

print("\n" + "="*65)
print("RESULTS")
print("="*65)
print(f"\n  {'Circuit':<18} {'Target':<12} {'f':>8} {'Z':>8}  {'Match'}")
print("  " + "─"*56)

results_table = {}
for i, (label, isa) in enumerate(zip(pub_labels, isa_circuits)):
    counts = result[i].data.c.get_counts()
    is_klein = 'Klein' in label
    delta_val = int(label.split('=')[1])
    p = PREDICTIONS[delta_val]
    target = p['klein'] if is_klein else p['toric']
    noise  = p['toric'] if is_klein else p['klein']

    f_sig   = freq(counts, target)
    f_noise = freq(counts, noise)
    Z       = z_score(f_sig, f_noise)
    dom     = max(counts, key=counts.get)
    match   = dom == target
    depth   = isa.depth()

    print(f"  {label:<18} '{target}'   {f_sig:>6.3f}   {Z:>6.0f}σ  {'✓' if match else '✗'}")
    results_table[label] = {
        'delta': delta_val, 'depth': depth,
        'target': target, 'f': f_sig, 'Z': Z, 'match': match,
    }

# Summary
print(f"\n{'='*65}")
print("δ-FAMILY ADVANTAGE SUMMARY")
print(f"{'='*65}")
print(f"\n  {'δ':<5} {'Klein f':>9} {'Toric f':>9} {'Ratio':>7} "
      f"{'Klein Z':>9} {'Toric Z':>9} {'Consistent?'}")
print("  " + "─"*65)

all_consistent = True
for delta in DELTAS:
    kl = results_table[f"Klein δ={delta}"]
    to = results_table[f"Toric δ={delta}"]
    ratio = kl['f'] / to['f'] if to['f'] > 0 else float('inf')
    consistent = kl['match'] and to['match'] and ratio > 1.0
    if not consistent: all_consistent = False
    print(f"  δ={delta}    {kl['f']:>7.3f}    {to['f']:>7.3f}   {ratio:>6.3f}×"
          f"    {kl['Z']:>6.0f}σ    {to['Z']:>6.0f}σ   {'✓' if consistent else '?'}")

print()
if all_consistent:
    ratios = [results_table[f"Klein δ={d}"]['f'] /
              results_table[f"Toric δ={d}"]['f'] for d in DELTAS]
    print(f"✅ Signal ratio consistent: {np.mean(ratios):.3f} ± {np.std(ratios):.3f}×")
    print("   Holonomy advantage holds across δ-family.")
else:
    print("⚠️  Some sectors inconsistent — check dominants above.")

import json
out = {
    'job_id': job.job_id(),
    'shots': SHOTS, 'seed': SEED,
    'predictions': {str(d): PREDICTIONS[d] for d in DELTAS},
    'results': {k: {kk: (float(v) if isinstance(v, float) else v)
                    for kk, v in val.items()}
                for k, val in results_table.items()},
}
with open('job2_delta_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to job2_delta_results.json")