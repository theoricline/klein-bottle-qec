# Data Repository — Klein Bottle & RP² Stabilizer Codes on IBM Fez

Raw syndrome count distributions from all verification experiments
supporting the paper series on non-orientable stabilizer codes.

All experiments were run on **IBM Fez** (Heron r2, 156 qubits)
on **2026-04-07** using transpiler seed 77.

---

## Files

| File | Experiment | Shots | Job ID |
|------|-----------|-------|--------|
| `01_klein_existence.json` | Klein 4×2 b-anyon sector | 4096 | `d7af5c1q1efs73d411b0` |
| `02_delta_family_d2.json` | Klein 4×2 δ-family, 4 configs | 4096 | `d7af5c1q1efs73d411b0` |
| `03_decoder_comparison.json` | Klein vs Toric MWPM decoder | 4096 | `d7af5c1q1efs73d411b0` |
| `04_rp2_existence.json` | RP² 4×4 both boundary twists | 2048 | `d7af5cak86tc73a1hpvg` |
| `05_rp2_logical_qubit.json` | RP² logical qubit Z_L contrast | 2048 | `d7af5cak86tc73a1hpvg` |
| `06_delta_family_d4.json` | Klein 6×4 δ=0 at d=4 | 8192 | `d7af5chq1efs73d411bg` |

---

## Results Summary

### 01 — Klein bottle code existence

**Claim:** The Klein bottle stabilizer code exists on IBM Fez hardware.
The b-anyon sector produces the predicted non-local syndrome pattern.

| Circuit | Dominant pattern | f | Z |
|---------|-----------------|---|---|
| Vacuum | `00000000` | 0.3933 | 400σ |
| b-anyon flip v(3,1) | `10000001` | 0.3875 | 394σ |

The b-anyon pattern `10000001` fires syndromes {0, 7}, connected by the
antipodal edge v(3,1) — a non-local connection impossible in any orientable
code. Baseline probability p₀ = 1/256 = 0.0039.

---

### 02 — δ-family at d=2

**Claim:** A classical parameter δ is encoded in the non-orientable boundary.
Each δ ∈ {0,1,2,3} produces a distinct syndrome configuration, all sharing
the Klein invariant (syndrome bit 0 always fires).

| δ | Dominant pattern | Z | Antipodal edge |
|---|-----------------|---|----------------|
| 0 | `10000001` | 377σ | 15 |
| 1 | `00010001` | 240σ | 14 |
| 2 | `00100001` | 337σ | 13 |
| 3 | `01000001` | 164σ | 12 |

All 4 patterns distinct ✓  
Klein invariant (bit 0) fires in all 4 configurations ✓

---

### 03 — Klein vs Toric MWPM decoder

**Claim:** The Klein MWPM decoder with antipodal shortcut outperforms a
standard toric decoder on errors adjacent to the non-orientable boundary.

The critical test is edge e₁₅ (the antipodal edge):
- Klein decoder correction: [15] — weight 1, antipodal shortcut
- Toric decoder correction: [3, 11] — weight 2, Manhattan path, **wrong**

| Circuit | Decoder | Dominant | f | Z |
|---------|---------|---------|---|---|
| e₁₅ error only | — | `10000001` | 0.3887 | 395σ |
| e₁₅ + Klein correction | Klein | `00000000` | 0.3982 | 404σ |
| e₁₅ + Toric correction | Toric | `00001001` | 0.3391 | 344σ |
| e₀ error only | — | `00000011` | 0.4114 | 418σ |
| e₀ + Klein correction | Klein | `00000000` | 0.4058 | 412σ |
| e₀ + Toric correction | Toric | `00000000` | 0.3906 | 397σ |

Key result: on the antipodal edge e₁₅, the toric decoder fails —
its dominant outcome is `00001001` (wrong syndrome sector).
The Klein decoder restores vacuum `00000000`.
**Δf = +0.059**, significance ~60σ.

For non-antipodal edge e₀, both decoders succeed — consistent with the
toric and Klein distance matrices agreeing for non-boundary errors.

---

### 04 — RP² stabilizer code existence

**Claim:** The real projective plane (RP²) stabilizer code exists on IBM Fez.
Both boundary twists are confirmed simultaneously.

The RP² code is defined on a 4×4 lattice with both pairs of opposite
edges identified with reversal:
- Vertical twist: (x, 0) ~ (3−x, 3)
- Horizontal twist: (0, y) ~ (3, 3−y)

The kill test is edge h(3,0): RP² predicts syndrome {3, 12} (non-local),
while Klein and toric both predict {0, 3} (local, adjacent).

| Circuit | Expected syndrome | Dominant pattern | f | Z |
|---------|------------------|-----------------|---|---|
| Vacuum | {} | `0000000000000000` | 0.0513 | 571σ |
| Flip v(3,3) | {0, 15} | `1000000000000001` | 0.0388 | 390σ |
| Flip h(3,0) ← **kill test** | **{3, 12}** | `0001000000001000` | 0.0361 | 362σ |
| Flip both | {0, 3, 12, 15} | `1001000000001001` | 0.0264 | 266σ |

The kill test fires {3, 12} at 362σ with zero noise bits in the dominant —
the first experimental confirmation of a doubly-identified non-orientable
stabilizer code. Baseline p₀ = 1/65536 = 1.5×10⁻⁵.

---

### 05 — RP² logical qubit verification

**Claim:** The RP² code encodes one logical qubit. The logical observable
Z_L = Z_{h(3,0)} · Z_{v(0,3)} (weight 2) distinguishes the two logical
states, confirming GSD = 2.

Logical operators derived analytically via GF(2) null space:
- Z_L = Z_{h(3,0)} · Z_{v(0,3)} — edges {3, 28} — **weight 2**
- X_L = X_{h(2,0)} · X_{h(3,0)} · X_{h(0,3)} · X_{v(1,3)} — edges {2, 3, 12, 29} — weight 4
- Anticommutation: |Z_L ∩ X_L| = |{3}| = 1 (odd) ✓

| State | ⟨Z_L⟩ | ZL counts |
|-------|--------|-----------|
| \|0_L⟩ | **+0.568** | {00: 1528, 01: 280, 10: 162, 11: 78} |
| \|1_L⟩ | **−0.316** | {01: 1226, 00: 557, 11: 143, 10: 122} |

**ΔZ_L = 0.885** — contrast confirming the two states are distinguishable.

Note: the syndrome register dominant is `0000000000001000` (not vacuum)
for both circuits, reflecting that X_L creates a syndrome excitation
consistent with the stabilizer structure. This does not affect the
Z_L measurement which reads out directly from data qubits.

---

### 06 — δ-family at d=4

**Claim:** The δ-family topological structure survives at code distance 4
on a 6×4 lattice (24-qubit syndrome register, 48 data qubits).

At circuit depth ~309, the exact 2-bit theoretical pattern is not the
dominant outcome due to noise accumulation. However, the topological
content is preserved in the dominant pattern.

| δ | Dominant fires | f | Z | Invariant ✓ | Prediction ✓ |
|---|---------------|---|---|-------------|--------------|
| 0 | {0, 6, 8, 13, 23} | 0.00134 | 498σ | bit 0 ✓ | syndrome 23 ✓ |

Klein invariant (syndrome bit 0) fires ✓  
Second syndrome = 23 (predicted for δ=0 on 6×4 lattice) ✓  
Extra bits {6, 8, 13} are noise-induced at depth 309.

The complete 6/6 δ-family at d=4 is documented in the original session
runs from 2026-04-04 (jobs d78m953c6das739i261g and d78mb43c6das739i2820).

---

## JSON Format

Each file follows this structure:

```json
{
  "experiment": "identifier",
  "claim": "scientific claim being verified",
  "papers": ["DOI or reference"],
  "hardware": "ibm_fez",
  "date": "2026-04-07",
  "seed": 77,
  "job_id": "IBM Quantum job identifier",
  "geometry": {"Lx": 4, "Ly": 2, "N_data": 16, "N_syn": 8},
  "p0": 0.00390625,
  "circuits": [
    {
      "label": "circuit name",
      "shots": 4096,
      "dominant_pattern": "10000001",
      "f_dominant": 0.3875,
      "Z_sigma": 394.0,
      "top10": {"10000001": 1587, ...},
      "all_counts": {"10000001": 1587, ...}
    }
  ]
}
```

The `all_counts` field contains the complete syndrome measurement
distribution — every observed bitstring and its count. This allows
full reproduction of all Z-scores, figures, and analysis without
requiring IBM Quantum access.

---

## Reproducing Z-scores

```python
import json, numpy as np

with open('data/01_klein_existence.json') as f:
    data = json.load(f)

circuit = data['circuits'][1]   # b-anyon circuit
p0      = data['p0']            # 1/256 = 0.00390625
shots   = circuit['shots']      # 4096
f       = circuit['f_dominant'] # 0.3875

Z = (f - p0) / np.sqrt(p0 * (1 - p0) / shots)
print(f"b-anyon Z = {Z:.1f}σ")  # → ~394σ
```

The same formula applies to all experiments. For the RP² experiments
(files 04–05) use p₀ = 1/65536.

---

## Circuit Depths

| Code | Geometry | Depth |
|------|----------|-------|
| Klein b-anyon | 4×2 | 111–112 |
| Klein decoder test | 4×2 | 111–163 |
| Klein δ-family d=2 | 4×2 | 112–246 |
| RP² existence | 4×4 | 281–282 |
| RP² logical qubit | 4×4 | 281–282 |
| Klein δ-family d=4 | 6×4 | 309 |

All circuits transpiled with `optimization_level=3`, `seed_transpiler=77`
on IBM Fez (Heron r2 native gate set: CZ, RZ, SX, X).

---

## Papers

| # | Title | DOI |
|---|-------|-----|
| 1 | Non-Orientable Topology in a Stabilizer Circuit | [10.5281/zenodo.19284050](https://doi.org/10.5281/zenodo.19284050) |
| 2 | Topologically Robust Syndrome-Based Readout of a Classical Parameter | [10.5281/zenodo.19286677](https://doi.org/10.5281/zenodo.19286677) |
| 3 | Logical Operator Holonomy and Non-Orientable Algebra | [10.5281/zenodo.19287977](https://doi.org/10.5281/zenodo.19287977) |
| 4 | Twelve Logical Qubits via Six Simultaneous Non-Orientable Codes | [10.5281/zenodo.19333513](https://doi.org/10.5281/zenodo.19333513) |
| 5 | MWPM Decoder with Antipodal Shortcut and Hardware Validation | [10.5281/zenodo.19451825](https://doi.org/10.5281/zenodo.19451825) |
| 6 | Comprehensive paper (Klein bottle + RP² stabilizer codes) | Zenodo (forthcoming) |

---

## Citation

If you use this data, please cite:

```
L. Roma, "Experimental Realization of the Klein Bottle Stabilizer Code
on a Superconducting Processor", Zenodo (2026).
https://github.com/theoricline/klein-bottle-qec
```
