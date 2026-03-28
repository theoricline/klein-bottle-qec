# ⬡ Klein Bottle Quantum Error-Correcting Code

**First experimental demonstration of a non-orientable stabilizer code on quantum hardware.**

[![Zenodo](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19202945-blue)](https://doi.org/10.5281/zenodo.19284050)
[![License: MIT](https://img.shields.io/badge/Code-MIT-green)](LICENSE)
[![License: CC BY 4.0](https://img.shields.io/badge/Paper-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/)
[![API](https://img.shields.io/badge/Live%20Demo-kleincode.pythonanywhere.com-purple)](https://kleincode.pythonanywhere.com)
[![Colab](https://img.shields.io/badge/Colab-Ready-orange)](https://kleincode.pythonanywhere.com/api/colab?delta=0&backend=ibm_fez&shots=8192)

---

## What this is

A Klein bottle stabilizer code encodes the boundary conditions of a Klein bottle — a compact non-orientable surface — directly into a stabilizer circuit. The result is a code that:

- uses **25% fewer physical qubits** than the square toric code at the same code distance
- achieves **138× enhancement** of its topological syndrome signature (Z=499σ) on IBM Fez
- fits **3× more logical qubits** on a 156-qubit chip than the surface code d=4
- produces **distinct, hardware-verifiable syndrome fingerprints** for each boundary condition δ

All results are independently reproducible via public IBM Quantum job IDs.

---

## Live demo

**[kleincode.pythonanywhere.com](https://kleincode.pythonanywhere.com)**

No IBM credentials needed. Predict syndrome fingerprints, check chip capacity, generate Colab scripts, get QASM circuits, view hardware benchmarks.

---

## Results at a glance

| Metric | Value | Job ID |
|--------|-------|--------|
| Best antipodal frequency | **44.2%** | `d70qt62f84ks73dgn3j0` |
| Enhancement vs toric | **138×** | |
| Statistical significance | **Z = 499σ** | |
| Parallel codes (4 simultaneous) | Z = 404–721σ each | `d711ljaf84ks73dgujf0` |
| δ-family fingerprints (4 configs) | Z = 316–606σ each | `d71582469uic73cl1q5g` |
| Logical qubits on IBM Fez (156q) | **12 Klein vs 4 surface** | |
| Processors confirmed | IBM Fez, Marrakesh, Torino | |

---

## Quick start

```bash
pip install qiskit qiskit-aer numpy
```

```python
from klein_bottle_code import KleinBottleCode, ToricCode

# Create a Klein bottle code on a 4×2 lattice
kb = KleinBottleCode(Lx=4, Ly=2)
print(kb)
# KleinBottleCode(Lx=4, Ly=2, N_data=16, N_syn=8, GSD=4)

# Build the b-anyon circuit (orientation-odd sector)
# The b-anyon is a topological excitation whose syndrome pattern
# is determined entirely by the lattice boundary condition δ
qc = kb.circuit('b_anyon')
print(kb.expected_syndrome('b_anyon'))  # '00001001'
print(kb.cp_class('b_anyon'))           # 'CP-odd'

# Compare with toric code (orientation-preserving control)
tc = ToricCode(Lx=4, Ly=2)
qc_toric = tc.circuit('b_anyon')

# Run noiseless simulation — verify all 4 logical sectors
kb.verify()
# vacuum      00000000  ✓
# a_anyon     00000011  ✓
# b_anyon     00001001  ✓
# both        00001010  ✓
```

### Reproduce the primary result from IBM hardware

```bash
# Requires IBM Quantum account: https://quantum.ibm.com
python verify_195sigma.py
# → f_K = 26.3%  f_T = 0.71%  Z = 34  (job d6uekv2tnsts73es36jg)
```

---

## API v2.0

Base URL: `https://kleincode.pythonanywhere.com`

All endpoints are public and require no authentication.

---

### v1.0 endpoints

#### `GET /api/predict`

Predict the syndrome fingerprint for a given δ, Lx, Ly. No IBM credentials needed.

The **predicted pattern** is the syndrome bitstring expected to dominate when the b-anyon topological excitation is prepared. It is determined entirely by the circuit wiring (the boundary condition δ) — not the quantum state — so it is immune to local quantum errors. Changing δ changes which syndrome qubit pair fires; this is the topological encoding.

**Parameters:** `delta` (0–Lx-1), `Lx` (2–8), `Ly` (1–4)

```bash
curl "https://kleincode.pythonanywhere.com/api/predict?delta=1&Lx=4&Ly=2"
```

```json
{
  "delta": 1,
  "Lx": 4,
  "Ly": 2,
  "predicted_pattern": "00010001",
  "firing_syndromes": [0, 4],
  "prep_edge": 12,
  "GSD": 4,
  "n_logical_qubits": 2,
  "topology": "Klein bottle",
  "hardware_result": {
    "f_K": 0.2754,
    "Z": 394,
    "depth": 240,
    "pattern": "00010001"
  }
}
```

> `firing_syndromes`: the two syndrome qubit indices that fire when the b-anyon is prepared. Always includes qubit 0 (vertex (0,0) is always in the antipodal star) plus one other qubit that steps as δ increases: 7→4→5→6 for δ=0,1,2,3.

---

#### `GET /api/capacity`

Calculate Klein code logical qubit capacity for any backend. Compares Klein bottle vs surface code d=4 (32 qubits, 1 logical qubit).

**Parameters:** `backend` (name or `all`), `Lx`, `Ly`

```bash
curl "https://kleincode.pythonanywhere.com/api/capacity?backend=ibm_fez&Lx=4&Ly=2"
```

```json
{
  "backend": "ibm_fez",
  "architecture": "Heron r2",
  "n_physical_qubits": 156,
  "qubits_per_klein_code": 24,
  "max_klein_codes": 6,
  "max_logical_qubits": 12,
  "max_surface_codes_d4": 4,
  "surface_logical_qubits": 4,
  "klein_advantage": 3.0,
  "note": "Klein advantage vs surface code d=4: 32 physical qubits, 1 logical qubit"
}
```

> `max_logical_qubits`: total logical qubits from all Klein codes running simultaneously on this chip. On IBM Fez: 6 codes × 2 logical qubits = 12, vs 4 surface codes × 1 = 4. Hardware-verified at 4 simultaneous codes (job `d711ljaf84ks73dgujf0`).

---

#### `GET /api/family`

Full δ-family results for Lx=4, Ly=2 — all four fingerprints with hardware verification from a single job.

The δ-family C(δ) is a set of Klein bottle codes that share the same topology (GSD=4, Klein bottle) but produce distinct syndrome fingerprints. Each δ shifts the antipodal edge by one lattice site, creating a different pair of firing syndrome qubits. Hardware-verified in a single job at Z=316–606σ.

```bash
curl "https://kleincode.pythonanywhere.com/api/family"
```

---

#### `GET /api/hardware`

All pre-recorded hardware results from both papers: job IDs, frequencies, Z-scores, backend details.

```bash
curl "https://kleincode.pythonanywhere.com/api/hardware"
```

---

#### `POST /api/analyse`

Analyse your own syndrome counts from an IBM Quantum job. No credentials needed — you provide the raw counts dict, the API returns f_K, Z, enhancement, and match verification against the theoretical prediction for your chosen δ.

**Fields:** `klein_counts` (required), `toric_counts` (optional, used for enhancement ratio), `shots`, `Lx`, `Ly`, `delta`

```bash
curl -X POST "https://kleincode.pythonanywhere.com/api/analyse" \
  -H "Content-Type: application/json" \
  -d '{
    "klein_counts": {"10000001": 3620, "00000000": 200},
    "toric_counts": {"10000001": 26, "00000000": 3800},
    "shots": 8192,
    "Lx": 4,
    "Ly": 2,
    "delta": 0
  }'
```

```json
{
  "delta": 0,
  "f_K": 0.4419,
  "f_T": 0.0032,
  "Z": 635.5,
  "enhancement": 139.2,
  "predicted_pattern": "10000001",
  "dominant_pattern": "10000001",
  "match": true,
  "verified": true,
  "GSD": 4,
  "n_logical_qubits": 2
}
```

> `verified`: true if the dominant pattern matches the theoretical prediction AND Z > 100σ. `enhancement`: f_K / f_T, how many times more often the antipodal pattern appears in Klein vs toric. `match`: dominant pattern equals predicted pattern.

---

### v2.0 endpoints

#### `GET /api/circuit` ⚗ NEW

Get the Klein bottle circuit as QASM or Python code. Paste directly into your own Qiskit pipeline. The circuit is generated server-side from the boundary condition mathematics — no IBM credentials needed.

**Parameters:** `delta`, `Lx`, `Ly`, `sector` (`b_anyon` | `vacuum`), `format` (`qasm` | `python`)

- `b_anyon`: prepares the orientation-odd topological sector (the one with the antipodal signature). This is the sector used in all published experiments.
- `vacuum`: no preparation — measures the ground state. Use as a control to verify the code is working correctly.

```bash
# Get QASM circuit
curl "https://kleincode.pythonanywhere.com/api/circuit?delta=1&Lx=4&Ly=2&format=qasm"

# Get Python/Qiskit code snippet
curl "https://kleincode.pythonanywhere.com/api/circuit?delta=1&Lx=4&Ly=2&format=python"
```

```json
{
  "format": "qasm",
  "delta": 1,
  "predicted_pattern": "00010001",
  "n_data_qubits": 16,
  "n_syndrome_qubits": 8,
  "n_logical_qubits": 2,
  "qasm": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg d[16];\n...",
  "usage": "Load with QuantumCircuit.from_qasm_str(qasm)"
}
```

**Use in Qiskit:**

```python
import requests
from qiskit import QuantumCircuit

resp = requests.get(
    "https://kleincode.pythonanywhere.com/api/circuit",
    params={"delta": 1, "Lx": 4, "Ly": 2, "format": "qasm"}
)
qasm = resp.json()["qasm"]
qc   = QuantumCircuit.from_qasm_str(qasm)

# Transpile and run with your own IBM credentials
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

service = QiskitRuntimeService(token="YOUR_TOKEN")
backend = service.backend("ibm_fez")

# seed_transpiler controls qubit placement and routing.
# seed=77 is optimal for δ=0 on IBM Fez (depth=112 gates).
# Other δ values and backends may benefit from a different seed —
# use /api/benchmark to check published optimal seeds per configuration.
pm      = generate_preset_pass_manager(3, backend=backend, seed_transpiler=77)
isa     = pm.run(qc)
job     = Sampler(backend).run([(isa,)], shots=8192)
counts  = job.result()[0].data.c.get_counts()

# Send back for analysis — no credentials needed for this step
analysis = requests.post(
    "https://kleincode.pythonanywhere.com/api/analyse",
    json={"klein_counts": counts, "shots": 8192, "delta": 1}
).json()
print(f"f_K={analysis['f_K']}  Z={analysis['Z']}σ  match={analysis['match']}")
```

---

#### `GET /api/colab` ⚗ NEW

Get a complete, ready-to-run Google Colab script. Add your IBM token on one line and run — the circuit is built, submitted to IBM hardware, and results are automatically sent to `/api/analyse`. Nothing else needed.

**Parameters:** `delta`, `Lx`, `Ly`, `backend`, `shots`

The script uses `seed_transpiler=77` as a starting point. This seed is optimal for δ=0 on IBM Fez. For other δ values the circuit topology differs, so the optimal seed may vary — the script will still run correctly with seed=77 but may not achieve minimum depth. Check `/api/benchmark` for per-δ optimal seeds.

```bash
curl "https://kleincode.pythonanywhere.com/api/colab?delta=1&backend=ibm_fez&shots=8192"
```

```json
{
  "delta": 1,
  "backend": "ibm_fez",
  "predicted_pattern": "00010001",
  "expected_fK": 0.2754,
  "expected_Z": 394,
  "instructions": [
    "1. Copy the script field",
    "2. Paste into a new Google Colab cell",
    "3. Replace YOUR_TOKEN_HERE with your IBM Quantum token",
    "4. Run the cell",
    "5. Results are automatically analysed by the API"
  ],
  "ibm_token_url": "https://quantum.ibm.com (Account → API token)",
  "script": "# Klein Bottle QEC — Generated by kleincode.pythonanywhere.com\n..."
}
```

**Python usage:**

```python
import requests

resp   = requests.get(
    "https://kleincode.pythonanywhere.com/api/colab",
    params={"delta": 1, "backend": "ibm_fez", "shots": 8192}
)
script = resp.json()["script"]

# Save as a Python file and add your token
with open("klein_experiment.py", "w") as f:
    f.write(script.replace("YOUR_TOKEN_HERE", "your_actual_token"))

# Or print directly and paste into a Colab cell
print(script)
```

The generated script:

1. Builds the Klein bottle circuit for your chosen δ
2. Transpiles against your backend (seed=77 by default — see note above)
3. Submits to IBM Quantum with your credentials
4. Collects syndrome counts
5. POSTs counts to `/api/analyse` and prints the full analysis

---

#### `GET /api/benchmark` ⚗ NEW

Expected performance metrics per δ per backend, from published hardware experiments. Use this before running on your hardware to know what pattern, frequency, and Z-score to expect — and which transpiler seed produced the best circuit depth in the published experiments.

> **Important:** `optimal_seed` is the seed that minimised circuit depth in our published experiments on that specific backend and calibration session. IBM hardware recalibrates between sessions, so optimal seed is session-dependent. The published seed is a strong starting point; a per-session depth scan (4 seconds, no circuit execution) may further improve results on other backends or calibration states.

**Parameters:** `backend` (name or `all`)

```bash
# Single backend
curl "https://kleincode.pythonanywhere.com/api/benchmark?backend=ibm_fez"

# All backends
curl "https://kleincode.pythonanywhere.com/api/benchmark?backend=all"
```

```json
{
  "backend": "ibm_fez",
  "architecture": "Heron r2",
  "n_qubits": 156,
  "delta_benchmarks": [
    {
      "delta": 0,
      "predicted_pattern": "10000001",
      "firing_syndromes": [0, 7],
      "expected_f_K": 0.4214,
      "expected_Z": 606,
      "circuit_depth": 112,
      "optimal_seed": 77,
      "verified": true
    },
    {
      "delta": 1,
      "predicted_pattern": "00010001",
      "firing_syndromes": [0, 4],
      "expected_f_K": 0.2754,
      "expected_Z": 394,
      "circuit_depth": 240,
      "optimal_seed": 77,
      "verified": true
    }
  ],
  "note": "Based on published experiments — your results may vary with calibration"
}
```

> `circuit_depth`: native gate depth after transpilation with the published optimal seed. Lower depth = less decoherence = stronger antipodal signal. δ=1 has depth=240 at seed=77 because seed=77 was optimised for δ=0; a per-δ seed scan would reduce this. `verified`: pattern confirmed on hardware at Z > 100σ.

---

## Integrate into your pipeline

### Minimal example — full loop in 15 lines

```python
import requests
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

API = "https://kleincode.pythonanywhere.com"
DELTA, SHOTS = 1, 8192

# 1. Get circuit from API (no credentials needed)
qasm = requests.get(f"{API}/api/circuit",
    params={"delta": DELTA, "format": "qasm"}).json()["qasm"]
qc   = QuantumCircuit.from_qasm_str(qasm)

# 2. Run on IBM hardware (your credentials)
service = QiskitRuntimeService(token="YOUR_TOKEN")
backend = service.backend("ibm_fez")
# seed=77 is optimal for δ=0 on IBM Fez.
# Use /api/benchmark to find published seeds for other δ/backend combinations.
pm      = generate_preset_pass_manager(3, backend=backend, seed_transpiler=77)
counts  = Sampler(backend).run(
    [(pm.run(qc),)], shots=SHOTS).result()[0].data.c.get_counts()

# 3. Analyse via API (no credentials needed)
result = requests.post(f"{API}/api/analyse",
    json={"klein_counts": counts, "shots": SHOTS, "delta": DELTA}).json()

print(f"Pattern: {result['dominant_pattern']}  f_K: {result['f_K']:.3f}"
      f"  Z: {result['Z']:.0f}σ  Verified: {result['verified']}")
```

### One-step Colab script

```python
import requests

# Get a complete script — paste into Colab, add token, run
script = requests.get(
    "https://kleincode.pythonanywhere.com/api/colab",
    params={"delta": 0, "backend": "ibm_fez", "shots": 8192}
).json()["script"]

print(script)  # paste this into a Colab cell
```

---

## The key idea — one line of code

The entire Klein bottle topology is encoded in a single modification to the toric code star operator:

```python
def klein_star(x, y, Lx, Ly, delta=0):
    edges = [h(x, y, Lx), h(x-1, y, Lx), v(x, y, Lx, Ly)]
    if y == 0:
        anti_x = (Lx - 1 - x + delta) % Lx
        edges.append(v(anti_x, Ly - 1, Lx, Ly))  # ← antipodal edge
    else:
        edges.append(v(x, y - 1, Lx, Ly))
    return list(set(edges))
```

At `y=0`, instead of connecting to the periodic neighbour `v(x, Ly-1)`, the star connects to the **antipodal vertex** `v(Lx-1-x+δ, Ly-1)`. This single non-local edge is the orientation-reversing identification of the Klein bottle. It produces the 44.2% antipodal signal and all other results in the papers.

Setting `delta > 0` shifts the antipodal connection, producing the δ-family C(δ) — different physical circuit layouts of the same topological code, each with a distinct, hardware-verifiable syndrome fingerprint.

---

## Repository structure

```
├── klein_bottle_code.py       # Core module — circuits, stabilizers, classes
│                              #   KleinBottleCode, ToricCode, verify()
├── verify_195sigma.py         # Reproduce primary result from IBM job IDs
│                              #   Connects to IBM, pulls raw counts, runs z-test
├── logical_error_scaling.py   # MWPM logical error rate simulation
│                              #   Klein vs toric under depolarizing noise
├── kbcode/
│   ├── core.py                # Library — klein_star, predicted_pattern,
│   │                          #   compute_gsd, analyse_counts, capacity
│   └── __init__.py
├── app.py                     # Flask API v2.0 (8 endpoints)
├── requirements.txt           # flask, numpy, gunicorn
├── render.yaml                # Render.com deployment config
└── README.md
```

---

## Complete hardware job ID table

### Paper 1

| Experiment | Job ID | Shots | Key result |
|-----------|--------|-------|-----------|
| Klein syndrome (primary) | `d6uekv2tnsts73es36jg` | 4096 | f_K=26.3%, Z=195σ |
| Toric control (primary) | `d6uel3469uic73ci5mc0` | 4096 | f_T=0.71% |
| GSD=4 / eraser | `d6vr4hgv5rlc73f5aqk0` | 6×8192 | All 4 sectors confirmed |
| No-signalling verification | `d6vrasgv5rlc73f5b0lg` | 6×8192 | 6.4σ pre-erasure |
| Replication Klein | `d70oofaf84ks73dgkov0` | 8192 | f_K=37.4%, Z=69σ |
| Replication Toric | `d70oofitnsts73euhj7g` | 8192 | f_T=0.31% |
| Seed opt seed=43 | `d70qq6qf84ks73dgn06g` | 4096 | f_K=40.8%, Z=331σ |
| **Seed opt seed=77 (best)** | **`d70qt62f84ks73dgn3j0`** | **4096** | **f_K=44.2%, Z=499σ ★** |
| 4 parallel codes | `d711ljaf84ks73dgujf0` | 8192 | Z=404–721σ each |
| Fez Lx=4 vacuum | `d70lugc69uic73ckgu00` | 8192 | Z=20 |
| Fez Lx=6 vacuum | `d70lrk0v5rlc73f675ig` | 8192 | Z=19 |
| Marrakesh Lx=4 | `d70lfjk69uic73ckg7h0` | 8192 | Z=20 |
| Marrakesh Lx=6 | `d70lfg8v5rlc73f66iug` | 8192 | Z=10 |
| Torino Lx=4 | `d70l9p2f84ks73dggoa0` | 8192 | Z=18 |
| Torino Lx=6 | `d70l9m0v5rlc73f66b0g` | 8192 | Z=6.5 |

### Paper 2 — δ-family

| Experiment | Job ID | Shots | Key result |
|-----------|--------|-------|-----------|
| δ-family all 4 configs | `d71582469uic73cl1q5g` | 4×8192 | Z=316–606σ, all patterns match theory |

---

## Papers

**Paper 1:** Non-Orientable Topology in a Stabilizer Circuit: Experimental Demonstration of a Klein Bottle Quantum Error-Correcting Code  
→ [doi:10.5281/zenodo.19284050](https://doi.org/10.5281/zenodo.19284050)

**Paper 2:** Topologically Robust Syndrome-Based Readout of a Classical Parameter in a Family of Non-Orientable Stabilizer Codes  
→ [10.5281/zenodo.19286677](https://doi.org/10.5281/zenodo.19286677)

**Paper 3:** Logical Operator Holonomy and Non-Orientable Algebra in a Klein Bottle Stabilizer Code  
→ [10.5281/zenodo.19287977](https://doi.org/10.5281/zenodo.19287977)

---

## Citation

```bibtex
@misc{roma2026klein,
  author    = {Roma, Leonardo},
  title     = {Non-Orientable Topology in a Stabilizer Circuit:
               Experimental Demonstration of a Klein Bottle
               Quantum Error-Correcting Code},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.19284050},
  url       = {https://doi.org/10.5281/zenodo.19284050}
}
```

---

## License

Code: [MIT](LICENSE) · Paper: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)  
Author: Leonardo Roma · March 2026  
GitHub: [theoricline/klein-bottle-qec](https://github.com/theoricline/klein-bottle-qec)  
API: [kleincode.pythonanywhere.com](https://kleincode.pythonanywhere.com)
