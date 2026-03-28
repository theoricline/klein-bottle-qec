"""
app.py — KleinCode Demo API v2.0
==================================
v1.0: predict, capacity, analyse, hardware, family
v2.0: + circuit (QASM export), colab (ready-to-run script), benchmark

All v1.0 routes unchanged.
New:
  GET /api/circuit   → QASM circuit string, paste into any Qiskit pipeline
  GET /api/colab     → complete ready-to-run Colab cell (add IBM token + run)
  GET /api/benchmark → expected f_K, Z, depth per δ on each backend
"""

from flask import Flask, jsonify, request, render_template_string
from kbcode.core import (
    predicted_pattern, compute_gsd, analyse_counts,
    capacity, all_capacities, KNOWN_BACKENDS,
    klein_star, toric_star, h, v, vi
)
import numpy as np

app = Flask(__name__)

# ── Pre-recorded hardware results ─────────────────────────────────

HARDWARE_RESULTS = {
    'primary': {
        'job_id':   'd70qt62f84ks73dgn3j0',
        'backend':  'ibm_fez',
        'shots':    4096,
        'seed':     77,
        'depth':    112,
        'f_K':      0.4419,
        'f_T':      0.0032,
        'Z':        499,
        'enhancement': 138,
        'pattern':  '10000001',
        'delta':    0,
        'paper':    'zenodo:10.5281/zenodo.19284050',
    },
    'delta_family': {
        'job_id': 'd71582469uic73cl1q5g',
        'backend': 'ibm_fez',
        'shots':   8192,
        0: {'f_K': 0.4214, 'Z': 606, 'pattern': '10000001', 'depth': 112},
        1: {'f_K': 0.2754, 'Z': 394, 'pattern': '00010001', 'depth': 240},
        2: {'f_K': 0.2216, 'Z': 316, 'pattern': '00100001', 'depth': 133},
        3: {'f_K': 0.3323, 'Z': 476, 'pattern': '01000001', 'depth': 164},
    },
    'parallel': {
        'job_id': 'd711ljaf84ks73dgujf0',
        'backend': 'ibm_fez',
        'shots':   8192,
        'n_codes': 4,
        'codes': [
            {'seed': 77, 'f_K': 0.4510, 'Z': 721, 'pattern': '00001001'},
            {'seed': 43, 'f_K': 0.3705, 'Z': 508, 'pattern': '00001001'},
            {'seed': 19, 'f_K': 0.2734, 'Z': 404, 'pattern': '00001001'},
            {'seed':  4, 'f_K': 0.3143, 'Z': 621, 'pattern': '00001001'},
        ],
        'mean_fK': 0.3523,
        'cv':      0.19,
        'n_logical_verified': 8,
    },
    'kill_test': {
        'job_id': 'd73rfc4vllmc73ansvk0', 'backend': 'ibm_fez',
        'shots': 8192, 'seed': 77,
        'klein_f': 0.4799, 'fake_f': 0.0039,
        'enhancement': 122.8, 'Z': 691,
        'paper': 'zenodo:10.5281/zenodo.19287977',
    },
    'holonomy': {
        'job_id': 'd73rqh5koquc73e22ni0', 'backend': 'ibm_fez',
        'shots': 8192, 'klein_r2': '10000010', 'toric_r2': '10001011',
        'klein_f': 0.1179, 'toric_f': 0.2296, 'klein_Z': 90, 'toric_Z': 272,
        'paper': 'zenodo:10.5281/zenodo.19287977',
    },
}

# Benchmark: expected results per backend per δ
BENCHMARK = {
    'ibm_fez': {
        0: {'f_K': 0.4214, 'Z': 606, 'depth': 112, 'seed': 77},
        1: {'f_K': 0.2754, 'Z': 394, 'depth': 240, 'seed': 77},
        2: {'f_K': 0.2216, 'Z': 316, 'depth': 133, 'seed': 77},
        3: {'f_K': 0.3323, 'Z': 476, 'depth': 164, 'seed': 77},
    },
    'ibm_marrakesh': {
        0: {'f_K': 0.036, 'Z': 20, 'depth': None, 'seed': None},
    },
    'ibm_torino': {
        0: {'f_K': 0.047, 'Z': 18, 'depth': None, 'seed': None},
    },
}

# ── Circuit builder (no Qiskit needed server-side) ────────────────

def build_circuit_qasm(Lx, Ly, delta=0, b_anyon=True):
    """
    Build the Klein bottle syndrome measurement circuit
    and return it as an OpenQASM 2.0 string.
    No Qiskit needed on the server — pure string generation.
    """
    N_data = 2 * Lx * Ly
    N_syn  = Lx * Ly
    anti_x, prep_edge = (Lx-1+delta) % Lx, None

    # Prep edge for b-anyon
    if b_anyon:
        anti_x    = (Lx - 1 - 0 + delta) % Lx
        prep_edge = v(anti_x, Ly-1, Lx, Ly)

    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg d[{N_data}];",
        f"qreg s[{N_syn}];",
        f"creg c[{N_syn}];",
        "",
        f"// Klein bottle code  delta={delta}  Lx={Lx}  Ly={Ly}",
        f"// b-anyon prepared:  {b_anyon}",
        f"// Prep edge:         {prep_edge}",
        f"// Reference: doi:10.5281/zenodo.19284050",
        "",
    ]

    if b_anyon and prep_edge is not None:
        lines.append(f"// Prepare b-anyon sector (orientation-odd)")
        lines.append(f"x d[{prep_edge}];")
        lines.append("barrier d;")
        lines.append("")

    lines.append("// Syndrome measurement — star operators")
    for y in range(Ly):
        for x in range(Lx):
            anc = vi(x, y, Lx)
            star = klein_star(x, y, Lx, Ly, delta)
            lines.append(f"// Star({x},{y}) → ancilla s[{anc}]")
            for e in star:
                lines.append(f"cx d[{e}],s[{anc}];")

    lines.append("")
    lines.append("// Measure syndrome qubits")
    lines.append(f"measure s -> c;")

    return "\n".join(lines)


def build_circuit_python(Lx, Ly, delta=0, b_anyon=True):
    """
    Build the circuit as a Python/Qiskit code string
    (for embedding in the /api/colab response).
    """
    N_data = 2 * Lx * Ly
    N_syn  = Lx * Ly
    anti_x = (Lx - 1 - 0 + delta) % Lx
    prep_edge = v(anti_x, Ly-1, Lx, Ly) if b_anyon else None

    # Build star operator lines
    star_lines = []
    for y in range(Ly):
        for x in range(Lx):
            anc  = vi(x, y, Lx)
            star = klein_star(x, y, Lx, Ly, delta)
            for e in star:
                star_lines.append(f"    qc.cx(qr_d[{e}], qr_s[{anc}])")

    star_code = "\n".join(star_lines)
    prep_code = f"qc.x(qr_d[{prep_edge}])  # b-anyon preparation\n    qc.barrier()" \
                if b_anyon else "# vacuum state — no preparation"

    return f"""# ── Klein bottle circuit  δ={delta}  Lx={Lx}  Ly={Ly} ──────────────
N_DATA, N_SYN = {N_data}, {N_syn}
qr_d = QuantumRegister(N_DATA, 'd')
qr_s = QuantumRegister(N_SYN,  's')
cr   = ClassicalRegister(N_SYN, 'c')
qc   = QuantumCircuit(qr_d, qr_s, cr)

{prep_code}

# Syndrome measurement — Klein bottle star operators (δ={delta})
{star_code}

qc.measure(qr_s, cr)"""


# ── v1.0 routes (unchanged) ───────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(LANDING_PAGE)


@app.route('/api/predict')
def predict():
    try:
        delta = int(request.args.get('delta', 0))
        Lx    = int(request.args.get('Lx', 4))
        Ly    = int(request.args.get('Ly', 2))
    except ValueError:
        return jsonify({'error': 'Invalid parameters'}), 400

    if not (0 <= delta < Lx):
        return jsonify({'error': f'delta must be 0..{Lx-1}'}), 400
    if not (2 <= Lx <= 8 and 1 <= Ly <= 4):
        return jsonify({'error': 'Lx must be 2-8, Ly must be 1-4'}), 400

    pattern, firing, prep_edge = predicted_pattern(Lx, Ly, delta)
    gsd, rank, k = compute_gsd(Lx, Ly, delta)

    all_patterns = {}
    for d in range(Lx):
        p, f, e = predicted_pattern(Lx, Ly, d)
        all_patterns[d] = {'pattern': p, 'firing': f, 'prep_edge': e}

    hw = None
    if Lx == 4 and Ly == 2 and delta in HARDWARE_RESULTS['delta_family']:
        hw = HARDWARE_RESULTS['delta_family'][delta]

    return jsonify({
        'delta': delta, 'Lx': Lx, 'Ly': Ly,
        'predicted_pattern': pattern, 'firing_syndromes': firing,
        'prep_edge': prep_edge, 'GSD': gsd,
        'stabilizer_rank': rank, 'n_logical_qubits': k,
        'topology': 'Klein bottle', 'all_patterns': all_patterns,
        'hardware_result': hw,
    })


@app.route('/api/capacity')
def capacity_endpoint():
    backend = request.args.get('backend', 'all')
    Lx = int(request.args.get('Lx', 4))
    Ly = int(request.args.get('Ly', 2))
    if backend == 'all':
        return jsonify({'Lx': Lx, 'Ly': Ly, 'backends': all_capacities(Lx, Ly)})
    return jsonify(capacity(backend, Lx, Ly))


@app.route('/api/analyse', methods=['POST'])
def analyse():
    data = request.get_json()
    if not data or 'klein_counts' not in data or 'shots' not in data:
        return jsonify({'error': 'Missing fields: klein_counts, shots'}), 400
    result = analyse_counts(
        data['klein_counts'], data.get('toric_counts', {}),
        int(data['shots']), int(data.get('Lx', 4)),
        int(data.get('Ly', 2)), int(data.get('delta', 0))
    )
    return jsonify(result.to_dict())


@app.route('/api/hardware')
def hardware():
    return jsonify({
        'primary_result':  HARDWARE_RESULTS['primary'],
        'delta_family': {
            'job_id':  HARDWARE_RESULTS['delta_family']['job_id'],
            'backend': HARDWARE_RESULTS['delta_family']['backend'],
            'results': {str(d): HARDWARE_RESULTS['delta_family'][d] for d in range(4)},
        },
        'parallel_codes': HARDWARE_RESULTS['parallel'],
        'kill_test': HARDWARE_RESULTS['kill_test'],
        'holonomy':  HARDWARE_RESULTS['holonomy'],
        'papers': {
            'paper1': 'https://doi.org/10.5281/zenodo.19284050',
            'paper2': 'https://doi.org/10.5281/zenodo.19286677',
            'paper3': 'https://doi.org/10.5281/zenodo.19287977',
        },
    })


@app.route('/api/family')
def family():
    Lx, Ly = 4, 2
    table = []
    for delta in range(Lx):
        pattern, firing, prep_edge = predicted_pattern(Lx, Ly, delta)
        gsd, rank, k = compute_gsd(Lx, Ly, delta)
        hw = HARDWARE_RESULTS['delta_family'].get(delta, {})
        table.append({
            'delta': delta, 'predicted_pattern': pattern,
            'firing_syndromes': firing, 'prep_edge': prep_edge,
            'GSD': gsd, 'n_logical_qubits': k,
            'hardware': {
                'f_K': hw.get('f_K'), 'Z': hw.get('Z'),
                'depth': hw.get('depth'),
                'verified': hw.get('Z', 0) > 100,
            },
        })
    return jsonify({
        'Lx': Lx, 'Ly': Ly, 'topology': 'Klein bottle (all δ)',
        'job_id': HARDWARE_RESULTS['delta_family']['job_id'],
        'family': table,
        'result': 'All 4 patterns distinct and hardware-verified',
    })


# ── v2.0 routes ───────────────────────────────────────────────────

@app.route('/api/circuit')
def circuit():
    """
    GET /api/circuit?delta=0&Lx=4&Ly=2&sector=b_anyon&format=qasm

    Returns the Klein bottle syndrome circuit as QASM or Python.
    Paste directly into your own Qiskit pipeline.
    No IBM credentials needed — circuit generation is pure Python.

    Params:
      delta:  0..Lx-1  (boundary condition shift)
      Lx:     2..8     (lattice width)
      Ly:     1..4     (lattice height)
      sector: b_anyon (default) | vacuum
      format: qasm (default) | python
    """
    try:
        delta  = int(request.args.get('delta', 0))
        Lx     = int(request.args.get('Lx', 4))
        Ly     = int(request.args.get('Ly', 2))
        sector = request.args.get('sector', 'b_anyon')
        fmt    = request.args.get('format', 'qasm')
    except ValueError:
        return jsonify({'error': 'Invalid parameters'}), 400

    b_anyon = (sector == 'b_anyon')
    pattern, firing, prep_edge = predicted_pattern(Lx, Ly, delta)
    gsd, _, k = compute_gsd(Lx, Ly, delta)

    if fmt == 'python':
        code = build_circuit_python(Lx, Ly, delta, b_anyon)
        return jsonify({
            'format':           'python',
            'delta':            delta,
            'Lx':               Lx,
            'Ly':               Ly,
            'sector':           sector,
            'predicted_pattern': pattern,
            'firing_syndromes': firing,
            'n_logical_qubits': k,
            'circuit_code':     code,
            'usage': 'Paste circuit_code into a Qiskit script. Add IBM credentials and submit.',
        })

    qasm = build_circuit_qasm(Lx, Ly, delta, b_anyon)
    return jsonify({
        'format':            'qasm',
        'delta':             delta,
        'Lx':                Lx,
        'Ly':                Ly,
        'sector':            sector,
        'predicted_pattern': pattern,
        'firing_syndromes':  firing,
        'n_data_qubits':     2 * Lx * Ly,
        'n_syndrome_qubits': Lx * Ly,
        'n_logical_qubits':  k,
        'GSD':               gsd,
        'qasm':              qasm,
        'usage': 'Load qasm string into Qiskit with QuantumCircuit.from_qasm_str(qasm)',
    })


@app.route('/api/colab')
def colab():
    """
    GET /api/colab?delta=1&Lx=4&Ly=2&backend=ibm_fez&shots=8192

    Returns a complete, ready-to-run Python script.
    Paste into a Colab cell, add your IBM token, run.
    Results are automatically sent to /api/analyse for verification.

    Params:
      delta:   0..Lx-1     (boundary condition)
      Lx, Ly:  lattice size (default 4×2)
      backend: IBM backend name (default ibm_fez)
      shots:   number of shots (default 8192)
    """
    try:
        delta   = int(request.args.get('delta', 0))
        Lx      = int(request.args.get('Lx', 4))
        Ly      = int(request.args.get('Ly', 2))
        backend = request.args.get('backend', 'ibm_fez')
        shots   = int(request.args.get('shots', 8192))
    except ValueError:
        return jsonify({'error': 'Invalid parameters'}), 400

    pattern, firing, prep_edge = predicted_pattern(Lx, Ly, delta)
    gsd, _, k = compute_gsd(Lx, Ly, delta)
    hw = HARDWARE_RESULTS['delta_family'].get(delta, {})
    circuit_code = build_circuit_python(Lx, Ly, delta, b_anyon=True)

    # Expected result for this configuration
    expected_fK = hw.get('f_K', 'unknown')
    expected_Z  = hw.get('Z',   'unknown')

    script = f'''# ══════════════════════════════════════════════════════════════════
# Klein Bottle QEC — Generated by kleincode.pythonanywhere.com
# δ={delta}  Lx={Lx}  Ly={Ly}  backend={backend}  shots={shots}
#
# Expected results (from published hardware experiments):
#   Predicted pattern: {pattern}
#   Firing syndromes:  {firing}
#   Expected f_K:      {expected_fK}  (IBM Fez, seed=77)
#   Expected Z:        {expected_Z}σ
#
# Reference: doi:10.5281/zenodo.19284050
# ══════════════════════════════════════════════════════════════════

# ── 1. Install dependencies (run once) ────────────────────────────
# !pip install qiskit qiskit-ibm-runtime requests -q

# ── 2. Imports ────────────────────────────────────────────────────
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import requests, json

# ── 3. IBM credentials ────────────────────────────────────────────
# Get your token at: https://quantum.ibm.com → Account → API token
IBM_TOKEN = "YOUR_TOKEN_HERE"   # ← paste your token here

service = QiskitRuntimeService(token=IBM_TOKEN)
backend = service.backend("{backend}")
print(f"Connected: {{backend.name}} ({{backend.num_qubits}} qubits)")

# ── 4. Build Klein bottle circuit ─────────────────────────────────
{circuit_code}

print(f"Circuit: {{qc.num_qubits}} qubits, {{qc.depth()}} depth (pre-transpile)")

# ── 5. Transpile ──────────────────────────────────────────────────
# seed=77 is optimal for δ=0 on IBM Fez — scan seeds for best result
pm  = generate_preset_pass_manager(optimization_level=3, backend=backend,
                                    seed_transpiler=77)
isa = pm.run(qc)
print(f"Transpiled depth: {{isa.depth()}}")

# ── 6. Run on hardware ────────────────────────────────────────────
sampler = Sampler(backend)
job     = sampler.run([(isa,)], shots={shots})
print(f"Job submitted: {{job.job_id()}}")
print("Waiting for results...")

result = job.result()
counts = result[0].data.c.get_counts()
dom    = max(counts, key=counts.get)
f_K    = counts.get("{pattern}", 0) / {shots}

print(f"\\nRaw results:")
print(f"  Dominant pattern: {{dom}}")
print(f"  Expected pattern: {pattern}")
print(f"  f_K (target):     {{f_K:.4f}} ({expected_fK} expected)")
print(f"  Match:            {{dom == '{pattern}'}}")

# ── 7. Analyse via KleinCode API ──────────────────────────────────
resp = requests.post(
    "https://kleincode.pythonanywhere.com/api/analyse",
    json={{
        "klein_counts": counts,
        "shots":        {shots},
        "Lx":           {Lx},
        "Ly":           {Ly},
        "delta":        {delta},
    }}
)
analysis = resp.json()

print(f"\\nAPI Analysis:")
print(f"  f_K:         {{analysis['f_K']}}")
print(f"  Z-score:     {{analysis['Z']}}σ")
print(f"  Enhancement: {{analysis['enhancement']}}×")
print(f"  Match:       {{analysis['match']}}")
print(f"  Verified:    {{analysis['verified']}}")
print(f"\\nFull analysis:")
print(json.dumps(analysis, indent=2))
'''

    return jsonify({
        'delta':             delta,
        'Lx':                Lx,
        'Ly':                Ly,
        'backend':           backend,
        'shots':             shots,
        'predicted_pattern': pattern,
        'firing_syndromes':  firing,
        'expected_fK':       expected_fK,
        'expected_Z':        expected_Z,
        'n_logical_qubits':  k,
        'script':            script,
        'instructions': [
            '1. Copy the script field',
            '2. Paste into a new Google Colab cell',
            f'3. Replace YOUR_TOKEN_HERE with your IBM Quantum token',
            '4. Run the cell',
            '5. Results are automatically analysed by the API',
        ],
        'ibm_token_url': 'https://quantum.ibm.com (Account → API token)',
    })


@app.route('/api/benchmark')
def benchmark():
    """
    GET /api/benchmark?backend=ibm_fez

    Returns expected performance metrics for each δ value
    based on published hardware experiments.
    Use this to set expectations before running on your hardware.

    Params:
      backend: ibm_fez (default) | ibm_marrakesh | ibm_torino | all
    """
    backend = request.args.get('backend', 'ibm_fez')

    if backend == 'all':
        result = {}
        for b, data in BENCHMARK.items():
            result[b] = {
                'architecture': KNOWN_BACKENDS.get(b, {}).get('arch', 'unknown'),
                'n_qubits':     KNOWN_BACKENDS.get(b, {}).get('n_qubits', 0),
                'results':      {str(d): v for d, v in data.items()},
            }
        return jsonify({
            'note': 'Expected f_K and Z from published experiments (doi:10.5281/zenodo.19284050)',
            'backends': result,
        })

    if backend not in BENCHMARK:
        available = list(BENCHMARK.keys())
        return jsonify({
            'error': f'No benchmark data for {backend}',
            'available': available,
        }), 404

    bdata = BENCHMARK[backend]
    table = []
    for delta in range(4):
        pattern, firing, _ = predicted_pattern(4, 2, delta)
        hw = bdata.get(delta, {})
        table.append({
            'delta':             delta,
            'predicted_pattern': pattern,
            'firing_syndromes':  firing,
            'expected_f_K':      hw.get('f_K'),
            'expected_Z':        hw.get('Z'),
            'circuit_depth':     hw.get('depth'),
            'optimal_seed':      hw.get('seed'),
            'verified':          hw.get('Z', 0) > 100 if hw else False,
        })

    cap = capacity(backend, 4, 2)
    return jsonify({
        'backend':          backend,
        'architecture':     KNOWN_BACKENDS.get(backend, {}).get('arch', 'unknown'),
        'n_qubits':         KNOWN_BACKENDS.get(backend, {}).get('n_qubits', 0),
        'capacity':         cap,
        'delta_benchmarks': table,
        'note':             'Based on published experiments — your results may vary with calibration',
        'paper':            'doi:10.5281/zenodo.19284050',
    })


# ── Landing page (v1.0 working version + v2.0 endpoints added) ────

LANDING_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KleinCode API</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0a0a0f;
  color: #e2e2f0;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  padding: 2rem;
  line-height: 1.5;
}
h1 { font-size: 1.8rem; font-weight: 600; margin-bottom: 0.5rem; }
h1 span { color: #7c6af7; }
.sub { color: #8a8ab0; font-size: 0.9rem; margin-bottom: 0.25rem; }
.amber { color: #fbbf24; }
.green { color: #4ade80; }
a { color: #7c6af7; text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: none; border-top: 1px solid #2a2a3a; margin: 1.5rem 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin: 1.5rem 0; }
.card { background: #12121a; border: 1px solid #2a2a3a; border-radius: 12px; padding: 1.25rem; }
.card h2 { color: #8a8ab0; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem; }
.stat { font-size: 2rem; font-weight: 700; color: #4ade80; line-height: 1.2; }
.label { font-size: 0.7rem; color: #8a8ab0; margin-top: 0.2rem; }
.fingerprint-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid #2a2a3a; }
.fingerprint-row:last-child { border-bottom: none; }
.delta-badge { background: rgba(124,106,247,0.2); color: #7c6af7; border-radius: 4px; padding: 0.2rem 0.5rem; font-size: 0.7rem; font-weight: 600; min-width: 2rem; text-align: center; }
.bits { display: flex; gap: 2px; }
.bit { width: 20px; height: 20px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 600; }
.bit-1 { background: #7c6af7; color: white; }
.bit-0 { background: #2a2a3a; color: #8a8ab0; }
.endpoint { font-size: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid #2a2a3a; }
.endpoint:last-child { border-bottom: none; }
.endpoint.new { border-left: 2px solid #4ade80; padding-left: 0.5rem; }
.method { color: #fbbf24; font-weight: 600; }
.path { color: #7c6af7; }
.badge-new { background: rgba(74,222,128,0.15); color: #4ade80; font-size: 0.6rem; padding: 0.1rem 0.3rem; border-radius: 3px; margin-left: 0.4rem; font-weight: 600; }
.controls { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin: 1rem 0; }
select, button { background: #1e1e2a; color: #e2e2f0; border: 1px solid #2a2a3a; border-radius: 6px; padding: 0.5rem 0.75rem; font-family: inherit; font-size: 0.8rem; cursor: pointer; }
button { background: #7c6af7; border-color: #7c6af7; color: white; font-weight: 500; }
button:hover { opacity: 0.85; }
.btn-outline { background: transparent; border-color: #fbbf24; color: #fbbf24; }
.btn-outline:hover { background: rgba(251,191,36,0.1); }
.btn-green { background: transparent; border-color: #4ade80; color: #4ade80; }
.btn-green:hover { background: rgba(74,222,128,0.1); }
#result { background: #0f0f14; border: 1px solid #2a2a3a; border-radius: 8px; padding: 0.75rem; font-family: monospace; font-size: 0.7rem; color: #4ade80; white-space: pre-wrap; margin-top: 1rem; max-height: 400px; overflow-y: auto; }
.footer { text-align: center; margin-top: 2rem; font-size: 0.7rem; color: #5a5a70; }
.v2-section { border: 1px solid rgba(74,222,128,0.3); border-radius: 12px; padding: 1.25rem; margin-top: 1.5rem; background: rgba(74,222,128,0.03); }
.v2-section h3 { color: #4ade80; font-size: 0.8rem; margin-bottom: 0.75rem; }
.v2-section .sub { font-size: 0.75rem; margin-bottom: 1rem; }
</style>
</head>
<body>

<h1><span>⬡</span> Klein Bottle QEC</h1>
<div class="sub">First non-orientable stabilizer code on quantum hardware</div>
<div class="sub amber">138× antipodal signal · Z=499σ · IBM Fez · 3× logical qubit density</div>
<div style="margin: 0.5rem 0 1rem 0">
  <a href="https://doi.org/10.5281/zenodo.19284050">Paper 1</a> &nbsp;|&nbsp;
  <a href="https://doi.org/10.5281/zenodo.19286677">Paper 2</a> &nbsp;|&nbsp;
  <a href="https://doi.org/10.5281/zenodo.19287977">Paper 3</a> &nbsp;|&nbsp;
  <a href="https://github.com/theoricline/klein-bottle-qec">GitHub</a>
</div>

<div class="grid">
  <div class="card">
    <h2>Primary Result — IBM Fez seed=77</h2>
    <div style="display:flex;gap:1.5rem;margin-bottom:0.5rem">
      <div><div class="stat">44.2%</div><div class="label">f_K antipodal</div></div>
      <div><div class="stat">138×</div><div class="label">vs toric</div></div>
      <div><div class="stat">499σ</div><div class="label">significance</div></div>
    </div>
    <div style="color:#8a8ab0;font-size:0.7rem">job d70qt62f84ks73dgn3j0 · 4096 shots · depth=112 · b-anyon prepared</div>
  </div>

  <div class="card">
    <h2>Logical Qubit Density — IBM Fez (156q)</h2>
    <div style="display:flex;gap:1.5rem;margin-bottom:0.5rem">
      <div><div class="stat">12</div><div class="label">Klein logical (6 codes)</div></div>
      <div><div class="stat amber">4</div><div class="label">Surface d=4 logical</div></div>
      <div><div class="stat">3×</div><div class="label">Klein advantage</div></div>
    </div>
    <div style="color:#8a8ab0;font-size:0.7rem">Hardware-verified · job d711ljaf84ks73dgujf0</div>
  </div>
</div>

<div class="grid">
  <div class="card">
    <h2>δ-Family Syndrome Fingerprints</h2>
    <div id="fingerprints">
      <div class="fingerprint-row"><span class="delta-badge">δ=0</span><div class="bits" id="bits0"></div><span class="green">606σ · 42.1%</span></div>
      <div class="fingerprint-row"><span class="delta-badge">δ=1</span><div class="bits" id="bits1"></div><span class="green">394σ · 27.5%</span></div>
      <div class="fingerprint-row"><span class="delta-badge">δ=2</span><div class="bits" id="bits2"></div><span class="green">316σ · 22.2%</span></div>
      <div class="fingerprint-row"><span class="delta-badge">δ=3</span><div class="bits" id="bits3"></div><span class="green">476σ · 33.2%</span></div>
    </div>
    <div style="color:#8a8ab0;font-size:0.7rem;margin-top:0.75rem">All hardware-verified · job d71582469uic73cl1q5g</div>
  </div>

  <div class="card">
    <h2>API Endpoints</h2>
    <div class="endpoint"><span class="method">GET</span> <span class="path">/api/predict</span> ?delta=0&Lx=4&Ly=2</div>
    <div class="endpoint"><span class="method">GET</span> <span class="path">/api/capacity</span> ?backend=ibm_fez</div>
    <div class="endpoint"><span class="method">GET</span> <span class="path">/api/family</span></div>
    <div class="endpoint"><span class="method">GET</span> <span class="path">/api/hardware</span></div>
    <div class="endpoint"><span class="method">POST</span> <span class="path">/api/analyse</span></div>
    <div class="endpoint new"><span class="method">GET</span> <span class="path">/api/circuit</span> ?delta=0&format=qasm <span class="badge-new">v2</span></div>
    <div class="endpoint new"><span class="method">GET</span> <span class="path">/api/colab</span> ?delta=0&backend=ibm_fez <span class="badge-new">v2</span></div>
    <div class="endpoint new"><span class="method">GET</span> <span class="path">/api/benchmark</span> ?backend=ibm_fez <span class="badge-new">v2</span></div>
  </div>
</div>

<!-- v1 interactive panel -->
<div class="card" style="margin-top:0">
  <h2>Try It — No IBM credentials needed</h2>
  <div class="controls">
    <label>δ:</label>
    <select id="s-delta"><option value="0">0</option><option value="1">1</option><option value="2">2</option><option value="3">3</option></select>
    <label>Lx:</label>
    <select id="s-lx"><option value="4">4</option><option value="6">6</option></select>
    <label>Ly:</label>
    <select id="s-ly"><option value="2">2</option></select>
    <button id="btn-predict">Predict fingerprint</button>
    <button id="btn-capacity" class="btn-outline">Chip capacity</button>
  </div>
  <div id="result">Select parameters and click a button</div>
</div>

<!-- v2 pipeline section -->
<div class="v2-section">
  <h3>⚗ Run on your own hardware <span class="badge-new">v2.0</span></h3>
  <div class="sub">Get a complete Colab script — add your IBM token and run. No credentials stored on our server.</div>
  <div class="controls">
    <label>δ:</label>
    <select id="c-delta"><option value="0">0</option><option value="1">1</option><option value="2">2</option><option value="3">3</option></select>
    <label>Backend:</label>
    <select id="c-backend">
      <option value="ibm_fez">ibm_fez</option>
      <option value="ibm_marrakesh">ibm_marrakesh</option>
      <option value="ibm_torino">ibm_torino</option>
      <option value="ibm_brisbane">ibm_brisbane</option>
      <option value="ibm_kyiv">ibm_kyiv</option>
    </select>
    <label>Shots:</label>
    <select id="c-shots"><option value="4096">4096</option><option value="8192">8192</option></select>
    <button id="btn-colab" class="btn-green">Generate Colab script</button>
    <button id="btn-circuit" class="btn-green" style="border-color:#7c6af7;color:#7c6af7">Get QASM circuit</button>
    <button id="btn-benchmark" class="btn-green" style="border-color:#8a8ab0;color:#8a8ab0">View benchmark</button>
  </div>
  <div id="result2" style="background:#0f0f14;border:1px solid #2a2a3a;border-radius:8px;padding:0.75rem;font-family:monospace;font-size:0.7rem;color:#4ade80;white-space:pre-wrap;margin-top:1rem;max-height:500px;overflow-y:auto">
    ← Generate a Colab script to run Klein bottle QEC on your IBM backend
  </div>
</div>

<div class="footer">
  KleinCode · Leonardo Roma · <a href="https://doi.org/10.5281/zenodo.19284050">doi:10.5281/zenodo.19284050</a> · MIT License · v2.0
</div>

<script>
// Render bit patterns
const patterns = ['10000001','00010001','00100001','01000001'];
for (let i=0; i<4; i++) {
  const container = document.getElementById('bits'+i);
  if (!container) continue;
  for (let bit of patterns[i]) {
    const span = document.createElement('span');
    span.className = 'bit bit-' + bit;
    span.textContent = bit;
    container.appendChild(span);
  }
}

function showResult(id, text) { document.getElementById(id).textContent = text; }

// v1 buttons
document.getElementById('btn-predict').addEventListener('click', async () => {
  showResult('result', 'Loading...');
  const delta = document.getElementById('s-delta').value;
  const Lx = document.getElementById('s-lx').value;
  const Ly = document.getElementById('s-ly').value;
  try {
    const resp = await fetch(`/api/predict?delta=${delta}&Lx=${Lx}&Ly=${Ly}`);
    const data = await resp.json();
    let out = `delta: ${data.delta}  Lx: ${data.Lx}  Ly: ${data.Ly}\n`;
    out += `predicted pattern: ${data.predicted_pattern}\n`;
    out += `firing syndromes:  ${JSON.stringify(data.firing_syndromes)}\n`;
    out += `prep edge: ${data.prep_edge}\n`;
    out += `GSD: ${data.GSD}  |  logical qubits: ${data.n_logical_qubits}\n`;
    if (data.hardware_result) {
      out += `\n[hardware verified on IBM Fez]\n`;
      out += `  f_K=${data.hardware_result.f_K}  |  Z=${data.hardware_result.Z}σ  |  depth=${data.hardware_result.depth}`;
    }
    showResult('result', out);
  } catch(e) { showResult('result', 'Error: ' + e.message); }
});

document.getElementById('btn-capacity').addEventListener('click', async () => {
  showResult('result', 'Loading...');
  const Lx = document.getElementById('s-lx').value;
  const Ly = document.getElementById('s-ly').value;
  try {
    const resp = await fetch(`/api/capacity?backend=all&Lx=${Lx}&Ly=${Ly}`);
    const data = await resp.json();
    const qpc = 3 * data.Lx * data.Ly;
    const k = data.backends[0].k_per_code;
    let out = `Klein capacity — Lx=${data.Lx}  Ly=${data.Ly}\n`;
    out += `${qpc} qubits/code  |  ${k} logical qubits/code  |  GSD=4\n`;
    out += `vs surface code d=4: 32 qubits, 1 logical qubit\n\n`;
    out += `Backend        | Klein logical    | Surface logical | Adv\n`;
    out += `─────────────────────────────────────────────────────────\n`;
    for (const b of data.backends) {
      const name = b.backend.replace('ibm_','').padEnd(12);
      const kl = `${b.max_klein_codes}x${k}=${b.max_logical_qubits}`.padEnd(15);
      const sl = `${b.max_surface_codes_d4}x1=${b.surface_logical_qubits}`.padEnd(14);
      out += `${name} | ${kl} | ${sl} | ${b.klein_advantage}x\n`;
    }
    const best = data.backends.reduce((a,b) => a.max_logical_qubits > b.max_logical_qubits ? a : b);
    out += `\nBest: ${best.backend} → ${best.max_logical_qubits} logical qubits (${best.klein_advantage}x advantage)`;
    showResult('result', out);
  } catch(e) { showResult('result', 'Error: ' + e.message); }
});

// v2 buttons
document.getElementById('btn-colab').addEventListener('click', async () => {
  showResult('result2', 'Generating Colab script...');
  const delta   = document.getElementById('c-delta').value;
  const backend = document.getElementById('c-backend').value;
  const shots   = document.getElementById('c-shots').value;
  try {
    const resp = await fetch(`/api/colab?delta=${delta}&backend=${backend}&shots=${shots}`);
    const data = await resp.json();
    let out = `# ── Instructions ──────────────────────────────────────\n`;
    data.instructions.forEach(i => { out += `# ${i}\n`; });
    out += `# IBM token: ${data.ibm_token_url}\n`;
    out += `# Expected: pattern=${data.predicted_pattern}  f_K≈${data.expected_fK}  Z≈${data.expected_Z}σ\n`;
    out += `# ──────────────────────────────────────────────────────\n\n`;
    out += data.script;
    showResult('result2', out);
  } catch(e) { showResult('result2', 'Error: ' + e.message); }
});

document.getElementById('btn-circuit').addEventListener('click', async () => {
  showResult('result2', 'Loading circuit...');
  const delta = document.getElementById('c-delta').value;
  try {
    const resp = await fetch(`/api/circuit?delta=${delta}&format=qasm`);
    const data = await resp.json();
    let out = `// Klein bottle circuit  δ=${data.delta}  Lx=${data.Lx}  Ly=${data.Ly}\n`;
    out += `// ${data.n_data_qubits} data qubits + ${data.n_syndrome_qubits} syndrome qubits\n`;
    out += `// Predicted pattern: ${data.predicted_pattern}\n`;
    out += `// Usage: QuantumCircuit.from_qasm_str(qasm_string)\n\n`;
    out += data.qasm;
    showResult('result2', out);
  } catch(e) { showResult('result2', 'Error: ' + e.message); }
});

document.getElementById('btn-benchmark').addEventListener('click', async () => {
  showResult('result2', 'Loading benchmark...');
  const backend = document.getElementById('c-backend').value;
  try {
    const resp = await fetch(`/api/benchmark?backend=${backend}`);
    const data = await resp.json();
    if (data.error) { showResult('result2', `No benchmark data for ${backend} yet.\nAvailable: ${data.available.join(', ')}`); return; }
    let out = `Benchmark: ${data.backend} (${data.architecture}, ${data.n_qubits}q)\n`;
    out += `Capacity: ${data.capacity.max_klein_codes} Klein codes = ${data.capacity.max_logical_qubits} logical qubits\n\n`;
    out += `δ  | Pattern    | Expected f_K | Expected Z | Depth | Verified\n`;
    out += `───────────────────────────────────────────────────────────────\n`;
    for (const row of data.delta_benchmarks) {
      const fk  = row.expected_f_K !== null ? (row.expected_f_K*100).toFixed(1)+'%' : 'n/a';
      const z   = row.expected_Z   !== null ? row.expected_Z+'σ' : 'n/a';
      const dep = row.circuit_depth !== null ? row.circuit_depth : 'n/a';
      const ver = row.verified ? '✓' : '—';
      out += `${row.delta}  | ${row.predicted_pattern} | ${fk.padEnd(12)} | ${z.padEnd(10)} | ${String(dep).padEnd(5)} | ${ver}\n`;
    }
    out += `\nNote: ${data.note}`;
    showResult('result2', out);
  } catch(e) { showResult('result2', 'Error: ' + e.message); }
});
</script>
</body>
</html>"""


if __name__ == '__main__':
    app.run(debug=True, port=5000)