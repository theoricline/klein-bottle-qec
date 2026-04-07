# ⬡ Klein Bottle & RP² Quantum Error-Correcting Codes

**First experimental demonstration of non-orientable stabilizer codes on superconducting quantum hardware.**

[![Paper 1](https://img.shields.io/badge/Paper%201-Zenodo-blue)](https://doi.org/10.5281/zenodo.19284050)
[![Paper 2](https://img.shields.io/badge/Paper%202-Zenodo-blue)](https://doi.org/10.5281/zenodo.19286677)
[![Paper 3](https://img.shields.io/badge/Paper%203-Zenodo-blue)](https://doi.org/10.5281/zenodo.19287977)
[![Paper 4](https://img.shields.io/badge/Paper%204-Zenodo-blue)](https://doi.org/10.5281/zenodo.19333513)
[![Paper 5](https://img.shields.io/badge/Paper%205-Zenodo-blue)](https://doi.org/10.5281/zenodo.19451825)
[![License: MIT](https://img.shields.io/badge/Code-MIT-green)](LICENSE)
[![License: CC BY 4.0](https://img.shields.io/badge/Paper-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/)
[![API](https://img.shields.io/badge/Live%20Demo-kleincode.pythonanywhere.com-purple)](https://kleincode.pythonanywhere.com)

---

## What this is

A five-paper experimental series establishing the Klein bottle stabilizer code
on IBM Fez (Heron r2, 156 qubits), culminating in the first experimental
demonstration of the RP² (real projective plane) stabilizer code.

Non-orientable stabilizer codes encode the boundary conditions of topological
surfaces — Klein bottle, RP² — directly into stabilizer circuits. The result
is a code family that:

- achieves **transversal logical Hadamard** with O(1) gate overhead (vs O(d²) for surface codes)
- encodes **2 logical qubits per Klein code** with a working MWPM decoder
- fits **12 logical qubits on a 156-qubit chip** — 3× more than surface code d=4
- produces **distinct, hardware-verifiable syndrome fingerprints** for each boundary configuration δ
- implements the **first non-orientable RP² stabilizer code** with GSD=2 confirmed experimentally

All results include raw syndrome count data in `data/` for independent verification
without requiring IBM Quantum access.

---

## Papers

| # | Title | DOI | Key result |
|---|-------|-----|------------|
| 1 | Non-Orientable Topology in a Stabilizer Circuit | [10.5281/zenodo.19284050](https://doi.org/10.5281/zenodo.19284050) | Code exists, b-anyon Z=499σ |
| 2 | Topologically Robust Syndrome-Based Readout | [10.5281/zenodo.19286677](https://doi.org/10.5281/zenodo.19286677) | δ-family Z=316–606σ |
| 3 | Logical Operator Holonomy and Non-Orientable Algebra | [10.5281/zenodo.19287977](https://doi.org/10.5281/zenodo.19287977) | Z₂ holonomy Z=45–312σ |
| 4 | Twelve Logical Qubits via Six Simultaneous Codes | [10.5281/zenodo.19333513](https://doi.org/10.5281/zenodo.19333513) | 12 logical qubits CV=0.01 |
| 5 | MWPM Decoder with Antipodal Shortcut | [10.5281/zenodo.19451825](https://doi.org/10.5281/zenodo.19451825) | 6/6 hardware Z=688–730σ |
| 6 | Comprehensive paper (Klein + RP²) |  [10.5281/zenodo.19454514](https://doi.org/10.5281/zenodo.19454514) | RP² existence + logical qubit |

---

## Results at a glance

### Klein bottle code

| Metric | Value |
|--------|-------|
| b-anyon Z-score (best run) | 499σ |
| δ-family at d=2 | 4/4 distinct configs, Z=316–606σ |
| δ-family at d=3 | 4/4 distinct configs, Z=791–1333σ |
| δ-family at d=4 | 6/6 configs, Klein invariant + correct second syndrome |
| Single-error logical fidelity | 98.57% ± 0.17% across 15/15 scenarios |
| Klein vs Toric on antipodal e₁₅ | Δf = +0.059, Klein dominant = `00000000`, Toric = `00001001` |
| Transversal Hadamard | O(1) overhead, depth 3, contrast 97.1% |
| 12 logical qubits on 156-qubit chip | CV=0.01, Z=620–730σ across 6 sessions |
| Processors confirmed | IBM Fez, Marrakesh, Kingston |

### RP² stabilizer code (first experimental demonstration)

| Metric | Value |
|--------|-------|
| Kill test h(3,0) → syndrome {3,12} | 362σ, zero noise bits |
| All 4 existence circuits | 266–571σ |
| Z_L contrast (logical qubit) | ΔZ_L = 0.885 |
| Z_L operator weight | 2 (weight-2 logical observable) |
| GSD = 2 | Confirmed experimentally |
| Transversal T gate | T^⊗32 ruled out; code deformation required |

---

## Verification data

The `data/` folder contains raw syndrome count distributions for all major
claims, produced in a single verification session on **2026-04-07** on IBM Fez.

| File | Claim | Key number |
|------|-------|------------|
| [`data/01_klein_existence.json`](data/01_klein_existence.json) | Klein b-anyon exists | `10000001` at 394σ |
| [`data/02_delta_family_d2.json`](data/02_delta_family_d2.json) | 4 distinct δ configs | All unique, invariant bit 0 ✓ |
| [`data/03_decoder_comparison.json`](data/03_decoder_comparison.json) | Klein beats toric on e₁₅ | Δf = +0.059 |
| [`data/04_rp2_existence.json`](data/04_rp2_existence.json) | RP² both twists confirmed | h(3,0)→{3,12} at 362σ |
| [`data/05_rp2_logical_qubit.json`](data/05_rp2_logical_qubit.json) | GSD=2 confirmed | ΔZ_L = 0.885 |
| [`data/06_delta_family_d4.json`](data/06_delta_family_d4.json) | δ=0 at d=4 confirmed | syndrome 0+23 at 498σ |

**Verification job IDs (IBM Fez, 2026-04-07):**
```
d7af5c1q1efs73d411b0   experiments 01–03  (4096 shots, 14 PUBs)
d7af5cak86tc73a1hpvg   experiments 04–05  (2048 shots, 6 PUBs)
d7af5chq1efs73d411bg   experiment 06      (8192 shots, 1 PUB)
```

See [`data/README.md`](data/README.md) for full documentation, result tables,
and Z-score reproduction code.

---

## Quick start

```bash
pip install qiskit qiskit-aer numpy
```

```python
from klein_bottle_code import KleinBottleCode

# Klein bottle code on a 4×2 lattice
kb = KleinBottleCode(Lx=4, Ly=2)

# Verify all 4 logical sectors — noiseless simulation
kb.verify()
# vacuum   00000000  ✓
# a_anyon  00000011  ✓
# b_anyon  10000001  ✓
# both     10000010  ✓

# Check the δ-family
for delta in range(4):
    kb_d = KleinBottleCode(Lx=4, Ly=2, delta=delta)
    print(f"δ={delta}  {kb_d.expected_syndrome('b_anyon')}")
# δ=0  10000001
# δ=1  00010001
# δ=2  00100001
# δ=3  01000001
```

### Reproduce any result from raw data (no IBM account needed)

```python
import json, numpy as np

with open('data/01_klein_existence.json') as f:
    data = json.load(f)

circuit = data['circuits'][1]   # b-anyon
p0      = data['p0']            # 1/256
shots   = circuit['shots']
f       = circuit['f_dominant']

Z = (f - p0) / np.sqrt(p0 * (1 - p0) / shots)
print(f"b-anyon Z = {Z:.1f}σ")  # → ~394σ
```

---

## The key idea — one line of code

The Klein bottle topology is a single modification to the toric star operator:

```python
def klein_star(x, y, Lx, Ly, delta=0):
    edges = [h(x, y, Lx), h(x-1, y, Lx), v(x, y, Lx, Ly)]
    if y == 0:
        anti_x = (Lx - 1 - x + delta) % Lx
        edges.append(v(anti_x, Ly-1, Lx, Ly))   # ← antipodal edge
    else:
        edges.append(v(x, y-1, Lx, Ly))
    return list(set(edges))
```

At `y=0`, instead of connecting to the periodic neighbour, the star connects
to the **antipodal vertex**. This single non-local edge is the
orientation-reversing identification of the Klein bottle.

The RP² code adds the same reversal to **both** boundaries:

```python
def rp2_star(x, y, Lx, Ly):
    edges = [h(x, y, Lx), v(x, y, Lx, Ly)]
    edges.append(h(Lx-1, Ly-1-y, Lx) if x == 0 else h(x-1, y, Lx))  # horizontal twist
    edges.append(v(Lx-1-x, Ly-1, Lx, Ly) if y == 0 else v(x, y-1, Lx, Ly))  # vertical twist
    return list(set(edges))
```

---

## Live demo & API

**[kleincode.pythonanywhere.com](https://kleincode.pythonanywhere.com)**

No IBM credentials needed. Predict syndrome fingerprints, generate Colab
scripts, analyse your own counts, view benchmarks.

| Endpoint | Description |
|----------|-------------|
| `GET /api/predict` | Syndrome fingerprint for δ, Lx, Ly |
| `GET /api/capacity` | Logical qubit capacity for any backend |
| `GET /api/family` | Full δ-family results |
| `POST /api/analyse` | Analyse your own syndrome counts |
| `GET /api/circuit` | QASM or Python circuit |
| `GET /api/colab` | Ready-to-run Colab script |
| `GET /api/benchmark` | Expected metrics per δ per backend |

---

## Repository structure

```
├── klein_bottle_code.py         Core module — KleinBottleCode, ToricCode
├── verify_195sigma.py           Reproduce primary result from Paper 1
├── logical_error_scaling.py     MWPM logical error rate simulation
├── rp2_existence.py             RP² existence circuits
├── rp2_logical_qubit.py         RP² logical qubit circuits
├── kbcode/
│   ├── core.py                  klein_star, rp2_star, compute_gsd, analyse_counts
│   └── __init__.py
├── app.py                       Flask API v2.0
├── data/
│   ├── README.md                Data documentation and reproduction guide
│   ├── 01_klein_existence.json
│   ├── 02_delta_family_d2.json
│   ├── 03_decoder_comparison.json
│   ├── 04_rp2_existence.json
│   ├── 05_rp2_logical_qubit.json
│   └── 06_delta_family_d4.json
└── README.md
```

---

## Complete hardware job ID record

### Paper 1 — Code existence

| Experiment | Job ID | Shots | Result |
|------------|--------|-------|--------|
| Klein syndrome (primary) | `d6uekv2tnsts73es36jg` | 4096 | f=26.3%, Z=195σ |
| Toric control | `d6uel3469uic73ci5mc0` | 4096 | f_T=0.71% |
| GSD=4 all sectors | `d6vr4hgv5rlc73f5aqk0` | 6×8192 | All 4 confirmed |
| No-signalling | `d6vrasgv5rlc73f5b0lg` | 6×8192 | 6.4σ pre-erasure |
| Seed=77 optimised | `d70qt62f84ks73dgn3j0` | 4096 | **f=44.2%, Z=499σ ★** |
| 4 parallel codes | `d711ljaf84ks73dgujf0` | 8192 | Z=404–721σ each |
| IBM Marrakesh | `d70lfjk69uic73ckg7h0` | 8192 | Z=20σ |
| IBM Kingston | `d70l9p2f84ks73dggoa0` | 8192 | Z=18σ |

### Paper 2 — δ-family

| Experiment | Job ID | Shots | Result |
|------------|--------|-------|--------|
| δ-family d=2 (4 configs) | `d71582469uic73cl1q5g` | 4×8192 | Z=316–606σ ✓ |

### Paper 3 — Holonomy

| Experiment | Job ID | Shots | Result |
|------------|--------|-------|--------|
| Dual operator / triple holonomy | `d77v8e2k86tc739ulr00` | 8192 | Z=45–312σ |

### Paper 4 — Parallel deployment

| Experiment | Job ID | Shots | Result |
|------------|--------|-------|--------|
| 6 codes, 12 logical qubits | `d741hmp8qmgc73flhrtg` | 8192 | Z=620–641σ, CV=0.01 |
| Day 2 reproducibility | `d7552n5bjrds73ebv320` | 8192 | Z=657–681σ, CV=0.01 |
| IBM Kingston | `d76bgq7q1anc738dd5bg` | 8192 | Z=575–601σ |

### Paper 5 — MWPM decoder

| Experiment | Job ID | Shots | Result |
|------------|--------|-------|--------|
| Main decoder validation | `d74c3l23qcgc73fqe0i0` | 8192 | 6/6, Z=688–730σ |
| Reproducibility day 2 | `d75578tbjrds73ebv8b0` | 8192 | 6/6, Z=694σ |
| Klein vs Toric hardware | `d76c0ku8faus73f13ma0` | 8192 | Δf=0.043–0.055 |
| Double-error / logical fidelity | `d74kkc23qcgc73fqmsn0` | 4096 | 98.57% single-error |

### Verification run — 2026-04-07 (raw data in `data/`)

| Experiments | Job ID | Shots |
|-------------|--------|-------|
| 01–03: Klein existence, δ-family, decoder | `d7af5c1q1efs73d411b0` | 4096 |
| 04–05: RP² existence, logical qubit | `d7af5cak86tc73a1hpvg` | 2048 |
| 06: δ-family d=4 | `d7af5chq1efs73d411bg` | 8192 |

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

Code: [MIT](LICENSE) · Papers: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)  
Author: Leonardo Roma · 2026  
GitHub: [theoricline/klein-bottle-qec](https://github.com/theoricline/klein-bottle-qec)  
API: [kleincode.pythonanywhere.com](https://kleincode.pythonanywhere.com)
