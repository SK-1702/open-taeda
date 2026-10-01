import json
import sqlite3
import re
import yaml
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import Any, Dict, List, Optional
from website.templates import BASE_HEADER, BASE_FOOTER
from website.def_parser import parse_def_file

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "ota.db"
MANIFESTS_DIR = ROOT / "experiments" / "manifests"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def render_page(title: str, content: str, active: str = "home") -> str:
    header = BASE_HEADER.replace("{{ title }}", title).replace(f"active=='{active}'", "true")
    header = re.sub(r"\{\% if active=='[a-z]+' \%\}active\{\% endif \%\}", "", header)
    return header + content + BASE_FOOTER

class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_html(self, html_content: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_content.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def send_json(self, data: Any, code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        if path == "/":
            self.render_home()
        elif path == "/experiments":
            self.render_experiments_list(parsed.query)
        elif path == "/experiments/compare":
            self.render_experiment_comparison(parsed.query)
        elif path.startswith("/experiments/") and path.endswith("/layout"):
            exp_id = path.split("/")[2]
            self.render_layout_viewer(exp_id)
        elif path.startswith("/experiments/"):
            exp_id = path.split("/")[-1]
            self.render_experiment_detail(exp_id)
        elif path == "/technologies":
            self.render_technologies_list()
        elif path == "/technologies/compare":
            self.render_technology_comparison(parsed.query)
        elif path.startswith("/technologies/"):
            tech_id = path.split("/")[-1]
            self.render_technology_detail(tech_id)
        elif path == "/designs":
            self.render_designs_list()
        elif path.startswith("/designs/"):
            des_id = path.split("/")[-1]
            self.render_design_detail(des_id)
        elif path == "/api/experiments":
            self.api_list_experiments()
        elif path.startswith("/api/experiments/") and path.endswith("/def"):
            exp_id = path.split("/")[3]
            self.api_get_def(exp_id)
        elif path.startswith("/api/experiments/"):
            exp_id = path.split("/")[-1]
            self.api_get_experiment(exp_id)
        elif path == "/api/matrix":
            self.api_matrix()
        else:
            self.send_html("<h1>404 Not Found</h1><p>The requested research page does not exist.</p>", 404)

    # ----------------------------------------------------------------------
    # 1. RESEARCH DASHBOARD & MATRIX IMPROVEMENT
    # ----------------------------------------------------------------------
    def render_home(self):
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT count(*) FROM experiments")
        total_exp = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM experiments WHERE status='SUCCESS'")
        success_exp = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM experiments WHERE status='FAILED'")
        failed_exp = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM experiments WHERE status='INCOMPLETE'")
        incomplete_exp = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM technologies")
        total_tech = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM designs")
        total_des = cur.fetchone()[0]

        cur.execute("SELECT technology_id, name FROM technologies ORDER BY node_nm DESC")
        techs = cur.fetchall()
        cur.execute("SELECT design_id, name FROM designs ORDER BY design_id")
        designs = cur.fetchall()

        # Build detailed matrix: Tech x Design
        matrix = {}
        for t in techs:
            matrix[t["technology_id"]] = {}
            for d in designs:
                cur.execute("""
                    SELECT count(*) as total,
                           sum(case when status='SUCCESS' then 1 else 0 end) as succ,
                           sum(case when status='FAILED' then 1 else 0 end) as fail
                    FROM experiments 
                    WHERE technology_id=? AND design_id=?
                """, (t["technology_id"], d["design_id"]))
                counts = cur.fetchone()

                cur.execute("""
                    SELECT experiment_id, status, name FROM experiments 
                    WHERE technology_id=? AND design_id=? AND status='SUCCESS'
                    ORDER BY experiment_id DESC LIMIT 1
                """, (t["technology_id"], d["design_id"]))
                rep = cur.fetchone()
                if not rep:
                    cur.execute("""
                        SELECT experiment_id, status, name FROM experiments 
                        WHERE technology_id=? AND design_id=?
                        ORDER BY experiment_id DESC LIMIT 1
                    """, (t["technology_id"], d["design_id"]))
                    rep = cur.fetchone()

                matrix[t["technology_id"]][d["design_id"]] = {
                    "total": counts["total"] or 0,
                    "succ": counts["succ"] or 0,
                    "fail": counts["fail"] or 0,
                    "representative": rep
                }

        # Recent experiments
        cur.execute("""
            SELECT experiment_id, name, technology_id, design_id, status 
            FROM experiments ORDER BY experiment_id DESC LIMIT 10
        """)
        recents = cur.fetchall()
        conn.close()

        content = f"""
        <div class="card" style="background: linear-gradient(135deg, #161b22, #0d1117); border: 1px solid #1f6feb;">
            <h1>Open TAEDA Research Platform</h1>
            <p style="font-size: 1.05rem; color: var(--text-muted);">
                Open Technology-Aware Semiconductor EDA Research Platform. Provenance-preserving physical design synthesis, memory footprint optimization, failure forensics, and cross-PDK experimental comparative analysis across Sky130, ICsprout55, NanGate45, ASAP7 FinFET, and GT3/GT2N GAAFET technologies.
            </p>
            <div style="margin-top: 1rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                <a href="/experiments/EXP-000022" class="badge badge-success" style="padding: 0.5rem 1rem; font-size: 0.9rem;">⭐ Landmark Experiment: EXP-000022 (ASAP7 7nm Signoff)</a>
                <a href="/experiments" class="badge badge-tech" style="padding: 0.5rem 1rem; font-size: 0.9rem;">Browse All {total_exp} Experiments</a>
                <a href="/technologies/compare" class="badge badge-tech" style="padding: 0.5rem 1rem; font-size: 0.9rem;">Cross-PDK Technology Comparison</a>
            </div>
        </div>

        <div class="grid-4" style="margin-bottom: 1.5rem;">
            <div class="stat-card">
                <div class="stat-value">{total_exp}</div>
                <div class="stat-label">Total Experiments</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--accent-green);">{success_exp}</div>
                <div class="stat-label">Verified Successes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--accent-red);">{failed_exp}</div>
                <div class="stat-label">Preserved Failures</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--accent-blue);">{total_tech} Nodes / {total_des} Designs</div>
                <div class="stat-label">Research Matrix</div>
            </div>
        </div>

        <div class="card">
            <h2>Research Matrix (Technology × Design Experimental Coverage)</h2>
            <p style="color: var(--text-muted); margin-bottom: 1rem; font-size: 0.9rem;">
                Every cell shows total experiment count, success/failure distribution, and the representative validated run. Click any cell to view filtered experiments.
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Technology Node</th>
        """
        for d in designs:
            content += f"<th>{d['name']} ({d['design_id']})</th>"
        content += "</tr></thead><tbody>"

        for t in techs:
            content += f"<tr><td><a href='/technologies/{t['technology_id']}'><strong>{t['name']}</strong> ({t['technology_id']})</a></td>"
            for d in designs:
                cell_data = matrix[t["technology_id"]][d["design_id"]]
                tot = cell_data["total"]
                rep = cell_data["representative"]
                if tot > 0 and rep:
                    st_cls = "badge-success" if rep["status"] == "SUCCESS" else ("badge-failed" if rep["status"] == "FAILED" else "badge-incomplete")
                    content += f"""
                    <td>
                        <a href="/experiments?tech={t['technology_id']}&design={d['design_id']}">
                            <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-heading);">{tot} Exps ({cell_data['succ']} pass, {cell_data['fail']} fail)</div>
                            <span class="badge {st_cls}" style="font-size: 0.75rem; margin-top: 0.3rem;">Representative: {rep['experiment_id']}</span>
                        </a>
                    </td>
                    """
                else:
                    content += "<td><span style='color: var(--text-muted);'>0 experiments</span></td>"
            content += "</tr>"
        content += "</tbody></table></div>"

        content += """
        <div class="card">
            <h2>Recent Validated Experiments</h2>
            <table>
                <thead>
                    <tr><th>ID</th><th>Experiment Name</th><th>Technology</th><th>Design</th><th>Status</th><th>Action</th></tr>
                </thead>
                <tbody>
        """
        for r in recents:
            st_cls = "badge-success" if r["status"] == "SUCCESS" else ("badge-failed" if r["status"] == "FAILED" else "badge-incomplete")
            content += f"""
            <tr>
                <td><a href="/experiments/{r['experiment_id']}"><strong>{r['experiment_id']}</strong></a></td>
                <td>{r['name']}</td>
                <td><span class="badge badge-tech">{r['technology_id']}</span></td>
                <td>{r['design_id']}</td>
                <td><span class="badge {st_cls}">{r['status']}</span></td>
                <td><a href="/experiments/{r['experiment_id']}">View Provenance &rarr;</a></td>
            </tr>
            """
        content += "</tbody>wait</table></div>"

        self.send_html(render_page("Research Platform Dashboard", content, active="home"))

    # ----------------------------------------------------------------------
    # 2. EXPERIMENT EXPLORER — FILTERING, SORTING, MULTI-SELECTION
    # ----------------------------------------------------------------------
    def render_experiments_list(self, query_str: str):
        params = parse_qs(query_str)
        filter_tech = params.get("tech", [""])[0]
        filter_design = params.get("design", [""])[0]

        manifest_files = sorted(MANIFESTS_DIR.glob("*.yaml"))
        all_exps = []

        for mfile in manifest_files:
            try:
                with open(mfile, "r") as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        exp = data.get("experiment", {})
                        tech = data.get("technology", {})
                        des = data.get("design", {})
                        metrics = data.get("metrics", {})
                        stages = data.get("stages", {})

                        # Determine stage reached
                        last_stage = "None"
                        for s_name in ["lvs", "drc", "sta", "extraction", "routing", "cts", "placement", "floorplan", "synthesis"]:
                            s_info = stages.get(s_name, {})
                            s_stat = s_info.get("status") if isinstance(s_info, dict) else str(s_info)
                            if s_stat in ["COMPLETED", "SUCCESS"]:
                                last_stage = s_name
                                break

                        all_exps.append({
                            "id": exp.get("id", mfile.stem),
                            "name": exp.get("name", mfile.stem),
                            "tech": tech.get("id", "unknown"),
                            "design": des.get("id", "DES-001"),
                            "type": exp.get("type", "baseline"),
                            "reproducibility": exp.get("reproducibility", "R3 - Provenance & Artifacts"),
                            "status": data.get("status", "UNKNOWN"),
                            "last_stage": last_stage,
                            "cell_count": metrics.get("cell_count"),
                            "core_area": metrics.get("core_area_um2"),
                            "wns": metrics.get("wns_ns"),
                            "drc": metrics.get("drc_errors"),
                            "antenna": metrics.get("antenna_violations", metrics.get("pin_antenna_violations")),
                            "runtime": metrics.get("runtime_str", "-"),
                            "memory": metrics.get("peak_memory_mb"),
                        })
            except Exception:
                pass

        # Sort by ID asc
        all_exps.sort(key=lambda x: x["id"])

        content = f"""
        <div class="card">
            <h1>Experiment Explorer</h1>
            <p style="color: var(--text-muted); margin-bottom: 1rem;">
                Browse, filter, and compare all {len(all_exps)} technology-aware semiconductor experiments.
            </p>

            <form id="compareForm" action="/experiments/compare" method="GET">
                <div class="toolbar">
                    <input type="text" id="searchInput" placeholder="Search ID or Name..." style="min-width: 200px;">
                    
                    <select id="filterTech">
                        <option value="">All Technologies</option>
                        <option value="sky130" {"selected" if filter_tech=="sky130" else ""}>SkyWater 130nm (sky130)</option>
                        <option value="ics55" {"selected" if filter_tech=="ics55" else ""}>ICsprout 55nm (ics55)</option>
                        <option value="nangate45" {"selected" if filter_tech=="nangate45" else ""}>NanGate 45nm (nangate45)</option>
                        <option value="asap7" {"selected" if filter_tech=="asap7" else ""}>ASAP 7nm FinFET (asap7)</option>
                        <option value="gt3" {"selected" if filter_tech=="gt3" else ""}>GT3 3nm GAAFET (gt3)</option>
                        <option value="gt2n" {"selected" if filter_tech=="gt2n" else ""}>GT2N 2nm GAAFET (gt2n)</option>
                    </select>

                    <select id="filterDesign">
                        <option value="">All Designs</option>
                        <option value="DES-001" {"selected" if filter_design=="DES-001" else ""}>PicoRV32 (DES-001)</option>
                        <option value="DES-002" {"selected" if filter_design=="DES-002" else ""}>SERV (DES-002)</option>
                        <option value="DES-003" {"selected" if filter_design=="DES-003" else ""}>Ibex (DES-003)</option>
                    </select>

                    <select id="filterType">
                        <option value="">All Types</option>
                        <option value="baseline">Baseline</option>
                        <option value="sweep">Sweep</option>
                        <option value="comparative">Comparative</option>
                        <option value="intervention">Intervention</option>
                    </select>

                    <select id="filterStatus">
                        <option value="">All Statuses</option>
                        <option value="SUCCESS">SUCCESS</option>
                        <option value="FAILED">FAILED</option>
                        <option value="INCOMPLETE">INCOMPLETE</option>
                        <option value="DRAFT">DRAFT</option>
                    </select>

                    <button type="button" class="btn btn-secondary" id="clearFiltersBtn">Clear Filters</button>
                    <button type="submit" class="btn btn-primary" id="compareBtn" style="margin-left: auto;">Compare Selected (0)</button>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span id="resultCountBadge" class="badge badge-tech">Showing {len(all_exps)} of {len(all_exps)} experiments</span>
                    <span style="font-size: 0.85rem; color: var(--text-muted);">Tip: Click column headers to sort</span>
                </div>

                <table id="expTable">
                    <thead>
                        <tr>
                            <th style="width: 30px; text-align: center;"><input type="checkbox" id="selectAllCheckbox"></th>
                            <th onclick="sortTable(1)">ID &#x21D5;</th>
                            <th onclick="sortTable(2)">Experiment Name &#x21D5;</th>
                            <th onclick="sortTable(3)">Tech &#x21D5;</th>
                            <th onclick="sortTable(4)">Design &#x21D5;</th>
                            <th onclick="sortTable(5)">Type &#x21D5;</th>
                            <th onclick="sortTable(6)">Status &#x21D5;</th>
                            <th onclick="sortTable(7)">Stage Reached &#x21D5;</th>
                            <th onclick="sortTable(8)">Cells &#x21D5;</th>
                            <th onclick="sortTable(9)">Core Area (μm²) &#x21D5;</th>
                            <th onclick="sortTable(10)">WNS (ns) &#x21D5;</th>
                            <th onclick="sortTable(11)">DRC &#x21D5;</th>
                            <th onclick="sortTable(12)">Antenna &#x21D5;</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        for e in all_exps:
            st_cls = "badge-success" if e["status"] == "SUCCESS" else ("badge-failed" if e["status"] == "FAILED" else "badge-incomplete")
            cell_val = f"{e['cell_count']:,}" if e["cell_count"] is not None else "—"
            area_val = f"{e['core_area']:,.1f}" if e["core_area"] is not None else "—"
            wns_val = f"{e['wns']:.2f}" if e["wns"] is not None else "—"
            drc_val = f"{e['drc']}" if e["drc"] is not None else "—"
            ant_val = f"{e['antenna']}" if e["antenna"] is not None else "—"

            content += f"""
            <tr data-tech="{e['tech']}" data-design="{e['design']}" data-type="{e['type']}" data-status="{e['status']}">
                <td style="text-align: center;"><input type="checkbox" name="ids" value="{e['id']}" class="exp-checkbox" onchange="updateCompareCount()"></td>
                <td><a href="/experiments/{e['id']}"><strong>{e['id']}</strong></a></td>
                <td><a href="/experiments/{e['id']}">{e['name']}</a></td>
                <td><span class="badge badge-tech">{e['tech']}</span></td>
                <td>{e['design']}</td>
                <td><span style="font-family: var(--font-mono); font-size: 0.8rem;">{e['type']}</span></td>
                <td><span class="badge {st_cls}">{e['status']}</span></td>
                <td><span style="font-family: var(--font-mono); font-size: 0.8rem;">{e['last_stage']}</span></td>
                <td style="font-family: var(--font-mono);">{cell_val}</td>
                <td style="font-family: var(--font-mono);">{area_val}</td>
                <td style="font-family: var(--font-mono);">{wns_val}</td>
                <td style="font-family: var(--font-mono);">{drc_val}</td>
                <td style="font-family: var(--font-mono);">{ant_val}</td>
            </tr>
            """
        content += """
                    </tbody>
                </table>
            </form>
        </div>

        <script>
            function updateCompareCount() {
                const checked = document.querySelectorAll('.exp-checkbox:checked');
                const btn = document.getElementById('compareBtn');
                btn.textContent = `Compare Selected (${checked.length})`;
                btn.disabled = (checked.length === 0);
            }

            document.getElementById('selectAllCheckbox').addEventListener('change', function(e) {
                const checkboxes = document.querySelectorAll('.exp-checkbox');
                checkboxes.forEach(cb => {
                    const row = cb.closest('tr');
                    if (row.style.display !== 'none') {
                        cb.checked = e.target.checked;
                    }
                });
                updateCompareCount();
            });

            function filterTable() {
                const search = document.getElementById('searchInput').value.toLowerCase();
                const tech = document.getElementById('filterTech').value;
                const design = document.getElementById('filterDesign').value;
                const type = document.getElementById('filterType').value;
                const status = document.getElementById('filterStatus').value;

                const rows = document.querySelectorAll('#expTable tbody tr');
                let visibleCount = 0;

                rows.forEach(row => {
                    const text = row.innerText.toLowerCase();
                    const rTech = row.getAttribute('data-tech');
                    const rDesign = row.getAttribute('data-design');
                    const rType = row.getAttribute('data-type');
                    const rStatus = row.getAttribute('data-status');

                    const mSearch = !search || text.includes(search);
                    const mTech = !tech || rTech === tech;
                    const mDesign = !design || rDesign === design;
                    const mType = !type || rType === type;
                    const mStatus = !status || rStatus === status;

                    if (mSearch && mTech && mDesign && mType && mStatus) {
                        row.style.display = '';
                        visibleCount++;
                    } else {
                        row.style.display = 'none';
                    }
                });

                document.getElementById('resultCountBadge').textContent = `Showing ${visibleCount} of ${rows.length} experiments`;
            }

            ['searchInput', 'filterTech', 'filterDesign', 'filterType', 'filterStatus'].forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('input', filterTable);
                    el.addEventListener('change', filterTable);
                }
            });

            document.getElementById('clearFiltersBtn').addEventListener('click', function() {
                document.getElementById('searchInput').value = '';
                document.getElementById('filterTech').value = '';
                document.getElementById('filterDesign').value = '';
                document.getElementById('filterType').value = '';
                document.getElementById('filterStatus').value = '';
                filterTable();
            });

            let sortDirection = {};
            function sortTable(colIndex) {
                const table = document.getElementById('expTable');
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const dir = sortDirection[colIndex] === 'asc' ? 'desc' : 'asc';
                sortDirection[colIndex] = dir;

                rows.sort((a, b) => {
                    let valA = a.children[colIndex].innerText.trim().replace(/,/g, '');
                    let valB = b.children[colIndex].innerText.trim().replace(/,/g, '');
                    
                    if (valA === '—') valA = dir === 'asc' ? '999999999' : '-999999999';
                    if (valB === '—') valB = dir === 'asc' ? '999999999' : '-999999999';

                    const numA = parseFloat(valA);
                    const numB = parseFloat(valB);

                    if (!isNaN(numA) && !isNaN(numB)) {
                        return dir === 'asc' ? numA - numB : numB - numA;
                    }
                    return dir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
                });

                rows.forEach(row => tbody.appendChild(row));
            }

            // Trigger initial filter on page load if query params present
            filterTable();
            updateCompareCount();
        </script>
        """

        self.send_html(render_page("Experiment Explorer", content, active="experiments"))

    # ----------------------------------------------------------------------
    # 3. MULTI-EXPERIMENT COMPARISON & GRAPHICAL COMPARISON
    # ----------------------------------------------------------------------
    def render_experiment_comparison(self, query_str: str):
        params = parse_qs(query_str)
        raw_ids = params.get("ids", [])
        exp_ids = []
        for item in raw_ids:
            exp_ids.extend([x.strip() for x in item.split(",") if x.strip()])

        if not exp_ids:
            self.send_html("<h1>No Experiments Selected</h1><p>Please select experiments from the <a href='/experiments'>Experiment Explorer</a> to compare.</p>", 400)
            return

        loaded_exps = []
        for eid in exp_ids:
            mfile = MANIFESTS_DIR / f"{eid}.yaml"
            if mfile.exists():
                with open(mfile, "r") as f:
                    data = yaml.safe_load(f)
                    if data: loaded_exps.append(data)

        if not loaded_exps:
            self.send_html("<h1>Experiments Not Found</h1>", 404)
            return

        content = f"""
        <div class="card">
            <h1>Multi-Experiment Scientific Comparison ({len(loaded_exps)} Experiments)</h1>
            <p style="color: var(--text-muted);">Side-by-side metric accounting, tool environment verification, and graphical comparative analysis.</p>
        </div>

        <div class="card">
            <h2>Graphical Metric Comparison</h2>
            <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem;">
                <label for="graphMetricSelect"><strong>Select Metric to Graph:</strong></label>
                <select id="graphMetricSelect" style="min-width: 220px;">
                    <option value="cell_count">Cell Count (Instances)</option>
                    <option value="core_area">Core Area (μm²)</option>
                    <option value="utilization">Core Utilization (%)</option>
                    <option value="wns">Worst Negative Slack (ns)</option>
                    <option value="tns">Total Negative Slack (ns)</option>
                    <option value="peak_memory">Peak Memory (MB)</option>
                    <option value="drc">DRC Violations</option>
                    <option value="antenna">Antenna Violations</option>
                </select>
            </div>

            <div id="svgChartContainer" style="background-color: var(--bg-dark); border: 1px solid var(--border-color); border-radius: 6px; padding: 1.5rem; min-height: 250px;">
                <!-- SVG Chart dynamically rendered via JS -->
            </div>
        </div>

        <div class="card">
            <h2>Comparative Metric Table</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th style="min-width: 180px;">Category / Metric</th>
        """
        for d in loaded_exps:
            content += f"<th><a href='/experiments/{d['experiment']['id']}'><strong>{d['experiment']['id']}</strong><br><span style='font-weight: normal; color: var(--text-muted);'>{d['experiment']['name']}</span></a></th>"
        content += "</tr></thead><tbody>"

        # Identity
        content += "<tr><td colspan='" + str(len(loaded_exps)+1) + "' style='background: rgba(255,255,255,0.05); font-weight: bold;'>A. EXPERIMENT IDENTITY</td></tr>"
        content += "<tr><td>Technology</td>" + "".join([f"<td><span class='badge badge-tech'>{d['technology']['id']}</span></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Design</td>" + "".join([f"<td>{d['design']['name']} ({d['design']['id']})</td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Experiment Type</td>" + "".join([f"<td>{d['experiment'].get('type','baseline')}</td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Status</td>" + "".join([f"<td><span class='badge {'badge-success' if d.get('status')=='SUCCESS' else 'badge-failed'}'>{d.get('status')}</span></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Parent Experiment</td>" + "".join([f"<td>{d['experiment'].get('parent_experiment','—') or '—'}</td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>OpenROAD Version</td>" + "".join([f"<td><code>{d.get('tools',{}).get('openroad','—')}</code></td>" for d in loaded_exps]) + "</tr>"

        # Physical Metrics
        content += "<tr><td colspan='" + str(len(loaded_exps)+1) + "' style='background: rgba(255,255,255,0.05); font-weight: bold;'>B. PHYSICAL METRICS</td></tr>"
        content += "<tr><td>Cell Count</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('cell_count','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Core Area (μm²)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('core_area_um2','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Die Area (mm²)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('die_area_mm2','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Utilization (%)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('utilization_pct', d.get('configuration',{}).get('core_utilization','—'))}%</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Peak Memory (MB)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('peak_memory_mb','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"

        # Timing
        content += "<tr><td colspan='" + str(len(loaded_exps)+1) + "' style='background: rgba(255,255,255,0.05); font-weight: bold;'>C. TIMING SIGNALS</td></tr>"
        content += "<tr><td>WNS Slack (ns)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('wns_ns','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>TNS Slack (ns)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('tns_ns','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"

        # Routing & Physical Verification
        content += "<tr><td colspan='" + str(len(loaded_exps)+1) + "' style='background: rgba(255,255,255,0.05); font-weight: bold;'>D. ROUTING & VERIFICATION</td></tr>"
        content += "<tr><td>Wirelength (μm)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('wirelength_um','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Vias Count</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('vias_count','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>DRC Errors</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('drc_errors','0')}</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Antenna Violations</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('antenna_violations', d.get('metrics',{}).get('pin_antenna_violations','0'))}</code></td>" for d in loaded_exps]) + "</tr>"

        # Power
        content += "<tr><td colspan='" + str(len(loaded_exps)+1) + "' style='background: rgba(255,255,255,0.05); font-weight: bold;'>E. POWER CONSUMPTION</td></tr>"
        content += "<tr><td>Total Power (μW)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('total_power_uw','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"
        content += "<tr><td>Dynamic Power (μW)</td>" + "".join([f"<td><code>{d.get('metrics',{}).get('dynamic_power_uw','—') or '—'}</code></td>" for d in loaded_exps]) + "</tr>"

        content += "</tbody></table></div></div>"

        # JSON data for client-side graph renderer
        chart_data_json = json.dumps([{
            "id": d["experiment"]["id"],
            "tech": d["technology"]["id"],
            "cell_count": d.get("metrics", {}).get("cell_count"),
            "core_area": d.get("metrics", {}).get("core_area_um2"),
            "utilization": d.get("metrics", {}).get("utilization_pct", d.get("configuration",{}).get("core_utilization")),
            "wns": d.get("metrics", {}).get("wns_ns"),
            "tns": d.get("metrics", {}).get("tns_ns"),
            "peak_memory": d.get("metrics", {}).get("peak_memory_mb"),
            "drc": d.get("metrics", {}).get("drc_errors"),
            "antenna": d.get("metrics", {}).get("antenna_violations"),
        } for d in loaded_exps])

        content += f"""
        <script>
            const expsData = {chart_data_json};

            const metricMeta = {{
                "cell_count": {{ label: "Cell Count", unit: "instances" }},
                "core_area": {{ label: "Core Area", unit: "μm²" }},
                "utilization": {{ label: "Core Utilization", unit: "%" }},
                "wns": {{ label: "Worst Negative Slack", unit: "ns" }},
                "tns": {{ label: "Total Negative Slack", unit: "ns" }},
                "peak_memory": {{ label: "Peak Memory", unit: "MB" }},
                "drc": {{ label: "DRC Violations", unit: "errors" }},
                "antenna": {{ label: "Antenna Violations", unit: "violations" }}
            }};

            function renderChart(metricKey) {{
                const container = document.getElementById('svgChartContainer');
                const meta = metricMeta[metricKey] || {{ label: metricKey, unit: "" }};
                
                const validPoints = expsData.map(d => ({{
                    id: d.id,
                    tech: d.tech,
                    val: (d[metricKey] !== null && d[metricKey] !== undefined) ? parseFloat(d[metricKey]) : null
                }}));

                const nums = validPoints.map(p => p.val).filter(v => v !== null && !isNaN(v));

                if (nums.length === 0) {{
                    container.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 2rem;">No data available for <strong>${{meta.label}}</strong> across selected experiments.</p>`;
                    return;
                }}

                const maxVal = Math.max(...nums, 1);
                const chartHeight = 200;
                const barWidth = Math.min(60, Math.floor(600 / validPoints.length));

                let svgHtml = `<svg width="100%" height="${{chartHeight + 60}}" viewBox="0 0 800 ${{chartHeight + 60}}" style="overflow: visible;">`;
                
                // Y Axis title
                svgHtml += `<text x="10" y="20" fill="var(--text-heading)" font-size="14" font-weight="bold">${{meta.label}} (${{meta.unit}})</text>`;

                const startX = 60;
                const availWidth = 720;
                const step = availWidth / validPoints.length;

                validPoints.forEach((pt, i) => {{
                    const x = startX + i * step + step / 4;
                    const val = pt.val;
                    
                    if (val !== null && !isNaN(val)) {{
                        const h = (val / maxVal) * chartHeight;
                        const y = chartHeight - h + 30;
                        const color = "#58a6ff";
                        
                        svgHtml += `<rect x="${{x}}" y="${{y}}" width="${{barWidth}}" height="${{h}}" fill="${{color}}" rx="4" opacity="0.85" />`;
                        svgHtml += `<text x="${{x + barWidth/2}}" y="${{y - 6}}" fill="#ffffff" font-size="11" font-family="monospace" text-anchor="middle">${{val.toLocaleString()}}</text>`;
                    }} else {{
                        svgHtml += `<text x="${{x + barWidth/2}}" y="${{chartHeight + 20}}" fill="var(--text-muted)" font-size="11" text-anchor="middle">—</text>`;
                    }}

                    // X Axis Labels
                    svgHtml += `<text x="${{x + barWidth/2}}" y="${{chartHeight + 45}}" fill="var(--text-heading)" font-size="11" font-family="monospace" text-anchor="middle" font-weight="bold">${{pt.id}}</text>`;
                    svgHtml += `<text x="${{x + barWidth/2}}" y="${{chartHeight + 60}}" fill="var(--text-muted)" font-size="10" text-anchor="middle">${{pt.tech}}</text>`;
                }});

                // Base line
                svgHtml += `<line x1="${{startX - 10}}" y1="${{chartHeight + 30}}" x2="780" y2="${{chartHeight + 30}}" stroke="var(--border-color)" stroke-width="2" />`;
                svgHtml += `</svg>`;

                container.innerHTML = svgHtml;
            }}

            document.getElementById('graphMetricSelect').addEventListener('change', function(e) {{
                renderChart(e.target.value);
            }});

            renderChart('cell_count');
        </script>
        """

        self.send_html(render_page("Experiment Comparison", content, active="experiments"))

    # ----------------------------------------------------------------------
    # 4. BASELINE VS INTERVENTION VIEW & EXPERIMENT DETAIL PAGE
    # ----------------------------------------------------------------------
    def render_experiment_detail(self, exp_id: str):
        mfile = MANIFESTS_DIR / f"{exp_id}.yaml"
        if not mfile.exists():
            self.send_html(f"<h1>404 Experiment Not Found</h1><p>Manifest for {exp_id} does not exist.</p>", 404)
            return

        with open(mfile, "r") as f:
            data = yaml.safe_load(f)

        exp = data.get("experiment", {})
        tech = data.get("technology", {})
        des = data.get("design", {})
        flow = data.get("flow", {})
        tools = data.get("tools", {})
        stages = data.get("stages", {})
        metrics = data.get("metrics", {})
        failure = data.get("failure")
        interventions = data.get("interventions", [])
        artifacts = data.get("artifacts", {})
        evidence = data.get("evidence", {})
        status = data.get("status", "UNKNOWN")
        parent_id = exp.get("parent_experiment")

        st_cls = "badge-success" if status == "SUCCESS" else ("badge-failed" if status == "FAILED" else "badge-incomplete")

        content = f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1>{exp_id}: {exp.get('name')}</h1>
                    <p style="color: var(--text-muted);">
                        Technology: <span class="badge badge-tech">{tech.get('id')}</span> | 
                        Design: <strong>{des.get('name')}</strong> | 
                        Type: <strong>{exp.get('type')}</strong> | 
                        Reproducibility: <strong>{exp.get('reproducibility', 'R3 - Artifact Provenance')}</strong>
                    </p>
                </div>
                <span class="badge {st_cls}" style="font-size: 1rem; padding: 0.4rem 1rem;">{status}</span>
            </div>
        </div>
        """

        # BASELINE VS INTERVENTION CARD (If parent experiment exists)
        if parent_id:
            parent_mfile = MANIFESTS_DIR / f"{parent_id}.yaml"
            parent_data = {}
            if parent_mfile.exists():
                with open(parent_mfile, "r") as pf:
                    parent_data = yaml.safe_load(pf) or {}

            p_metrics = parent_data.get("metrics", {})
            p_cells = p_metrics.get("cell_count")
            c_cells = metrics.get("cell_count")

            delta_cell_str = "—"
            if p_cells and c_cells:
                abs_d = c_cells - p_cells
                pct_d = (abs_d / p_cells) * 100
                sign = "+" if abs_d > 0 else ""
                delta_cell_str = f"{sign}{abs_d:,} instances ({sign}{pct_d:.1f}%)"

            inv_param = interventions[0].get("changed_parameter") if interventions else "Configuration Override"
            inv_reason = interventions[0].get("reason") if interventions else "Derived experimental iteration"

            content += f"""
            <div class="card" style="border: 1px solid var(--accent-blue);">
                <h2>Baseline vs Intervention Relationship</h2>
                <div class="grid-3" style="margin-top: 1rem;">
                    <div class="flow-node">
                        <div class="badge badge-failed" style="margin-bottom: 0.5rem;">BASELINE EXPERIMENT</div>
                        <h4><a href="/experiments/{parent_id}">{parent_id}</a></h4>
                        <p style="font-size: 0.85rem; color: var(--text-muted);">{parent_data.get('experiment',{}).get('name','Baseline Failure')}</p>
                        <p style="font-size: 0.85rem; margin-top: 0.5rem;">Cells: <code>{p_cells if p_cells else 'OOM / Failed'}</code></p>
                    </div>

                    <div class="flow-node" style="border-color: var(--accent-cyan);">
                        <div class="badge badge-tech" style="margin-bottom: 0.5rem;">INTERVENTION / OVERRIDE</div>
                        <h4>{inv_param}</h4>
                        <p style="font-size: 0.85rem; color: var(--text-muted);">{inv_reason}</p>
                    </div>

                    <div class="flow-node" style="border-color: var(--accent-green);">
                        <div class="badge badge-success" style="margin-bottom: 0.5rem;">RESULT EXPERIMENT</div>
                        <h4><a href="/experiments/{exp_id}">{exp_id}</a></h4>
                        <p style="font-size: 0.85rem; color: var(--text-muted);">{exp.get('name')}</p>
                        <p style="font-size: 0.85rem; margin-top: 0.5rem;">Cells: <code>{c_cells if c_cells else '—'}</code></p>
                    </div>
                </div>

                <div style="margin-top: 1rem; background-color: var(--bg-dark); padding: 1rem; border-radius: 6px;">
                    <h4>Numerical Delta Accounting (Neutral Provenance)</h4>
                    <table>
                        <thead><tr><th>Metric</th><th>Baseline ({parent_id})</th><th>Result ({exp_id})</th><th>Delta (Absolute & Percentage)</th></tr></thead>
                        <tbody>
                            <tr>
                                <td>Cell Count</td>
                                <td><code>{p_cells if p_cells else '—'}</code></td>
                                <td><code>{c_cells if c_cells else '—'}</code></td>
                                <td><code>{delta_cell_str}</code></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            """

        # Four Truths
        content += f"""
        <div class="card">
            <h2>Four Scientific Truths</h2>
            <div class="grid-2">
                <div>
                    <h3>1. Design Truth</h3>
                    <table>
                        <tr><td>Design ID / Name</td><td><strong>{des.get('id')} / {des.get('name')}</strong></td></tr>
                        <tr><td>Top Module</td><td><code>{des.get('top')}</code></td></tr>
                        <tr><td>RTL Source</td><td><code>{data.get('inputs',{}).get('rtl')}</code></td></tr>
                        <tr><td>Constraints</td><td><code>{data.get('inputs',{}).get('constraints')}</code></td></tr>
                    </table>
                </div>
                <div>
                    <h3>2. Technology Truth</h3>
                    <table>
                        <tr><td>Technology ID</td><td><span class="badge badge-tech">{tech.get('id')}</span></td></tr>
                        <tr><td>Clock Period</td><td>{data.get('configuration',{}).get('clock_period_ns')} ns</td></tr>
                        <tr><td>Core Utilization</td><td>{data.get('configuration',{}).get('core_utilization')} %</td></tr>
                        <tr><td>Antenna Repair Setting</td><td><code>GRT_REPAIR_ANTENNAS={data.get('configuration',{}).get('grt_repair_antennas')}</code></td></tr>
                    </table>
                </div>
            </div>

            <div class="grid-2" style="margin-top: 1.5rem;">
                <div>
                    <h3>3. Tool Truth</h3>
                    <table>
                        <tr><td>Yosys Version</td><td><code>{tools.get('yosys')}</code></td></tr>
                        <tr><td>OpenROAD Version</td><td><code>{tools.get('openroad')}</code></td></tr>
                        <tr><td>OpenSTA Version</td><td><code>{tools.get('opensta')}</code></td></tr>
                        <tr><td>OS Environment</td><td>{data.get('environment',{}).get('os')}</td></tr>
                    </table>
                </div>
                <div>
                    <h3>4. Physical / Experimental Truth</h3>
                    <table>
                        <tr><td>Cell Count</td><td><code>{metrics.get('cell_count', '—')}</code></td></tr>
                        <tr><td>Core Area</td><td><code>{f"{metrics['core_area_um2']:,.1f} μm²" if 'core_area_um2' in metrics else '—'}</code></td></tr>
                        <tr><td>Wire Length</td><td><code>{f"{metrics['wirelength_um']:,.1f} μm" if 'wirelength_um' in metrics else '—'}</code></td></tr>
                        <tr><td>DRC Errors</td><td><code>{metrics.get('drc_errors', '0')}</code></td></tr>
                        <tr><td>Antenna Violations</td><td><code>{metrics.get('antenna_violations', '0')}</code></td></tr>
                    </table>
                </div>
            </div>
        </div>
        """

        # Stage Timeline
        content += """
        <div class="card">
            <h2>Stage Execution Timeline</h2>
            <table>
                <thead><tr><th>Seq</th><th>Stage Name</th><th>Status</th></tr></thead>
                <tbody>
        """
        seq = 1
        for st_name, st_info in stages.items():
            st_val = st_info.get("status", "NOT_RUN") if isinstance(st_info, dict) else str(st_info)
            badge_c = "badge-success" if st_val in ["COMPLETED", "SUCCESS"] else ("badge-failed" if st_val == "FAILED" else "badge-incomplete")
            content += f"<tr><td>{seq}</td><td><strong>{st_name}</strong></td><td><span class='badge {badge_c}'>{st_val}</span></td></tr>"
            seq += 1
        content += "</tbody></table></div>"

        # Interactive DEF Layout Canvas (Feature 7)
        def_file = artifacts.get("def")
        if def_file:
            content += f"""
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2>Interactive Layout Viewer (DEF Artifact)</h2>
                    <div>
                        <button class="btn btn-secondary" onclick="resetCanvasView()">Reset View</button>
                        <button class="btn btn-secondary" onclick="zoomCanvas(1.2)">Zoom +</button>
                        <button class="btn btn-secondary" onclick="zoomCanvas(0.8)">Zoom -</button>
                    </div>
                </div>
                <div style="display: flex; gap: 1rem; margin-bottom: 0.5rem; font-size: 0.85rem;">
                    <label><input type="checkbox" id="chkShowCells" checked onchange="drawLayoutCanvas()"> Show Cells</label>
                    <label><input type="checkbox" id="chkShowPins" checked onchange="drawLayoutCanvas()"> Show Pins</label>
                    <span id="canvasInfo" style="margin-left: auto; color: var(--accent-cyan); font-family: monospace;">Loading DEF layout data...</span>
                </div>
                <canvas id="layoutCanvas"></canvas>
            </div>

            <script>
                let defData = null;
                let scale = 1;
                let panX = 0, panY = 0;
                let isDragging = false, startX, startY;

                fetch('/api/experiments/{exp_id}/def')
                    .then(res => res.json())
                    .then(data => {{
                        defData = data;
                        if (data.error) {{
                            document.getElementById('canvasInfo').textContent = data.error;
                            return;
                        }}
                        resetCanvasView();
                    }});

                function resetCanvasView() {{
                    if (!defData || !defData.diearea) return;
                    const canvas = document.getElementById('layoutCanvas');
                    const ctx = canvas.getContext('2d');
                    canvas.width = canvas.clientWidth;
                    canvas.height = canvas.clientHeight;

                    const die = defData.diearea;
                    const dieW = die[2] - die[0];
                    const dieH = die[3] - die[1];

                    const scaleX = (canvas.width - 40) / dieW;
                    const scaleY = (canvas.height - 40) / dieH;
                    scale = Math.min(scaleX, scaleY);

                    panX = 20 - die[0] * scale;
                    panY = canvas.height - 20 + die[1] * scale; // invert Y

                    document.getElementById('canvasInfo').textContent = `Die: ${{dieW.toFixed(0)}} × ${{dieH.toFixed(0)}} μm | Components: ${{defData.total_components}}`;
                    drawLayoutCanvas();
                }}

                function zoomCanvas(factor) {{
                    scale *= factor;
                    drawLayoutCanvas();
                }}

                function drawLayoutCanvas() {{
                    if (!defData || !defData.diearea) return;
                    const canvas = document.getElementById('layoutCanvas');
                    const ctx = canvas.getContext('2d');
                    ctx.clearRect(0, 0, canvas.width, canvas.height);

                    const showCells = document.getElementById('chkShowCells').checked;
                    const showPins = document.getElementById('chkShowPins').checked;
                    const die = defData.diearea;

                    // Draw Die Area Box
                    const x1 = die[0] * scale + panX;
                    const y1 = panY - die[3] * scale;
                    const w = (die[2] - die[0]) * scale;
                    const h = (die[3] - die[1]) * scale;

                    ctx.strokeStyle = '#58a6ff';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x1, y1, w, h);

                    // Draw Components
                    if (showCells && defData.components) {{
                        ctx.fillStyle = 'rgba(57, 197, 207, 0.6)';
                        defData.components.forEach(c => {{
                            const cx = c.x * scale + panX;
                            const cy = panY - c.y * scale;
                            ctx.fillRect(cx, cy, Math.max(2, 4 * scale), Math.max(2, 4 * scale));
                        }});
                    }}

                    // Draw Pins
                    if (showPins && defData.pins) {{
                        ctx.fillStyle = '#f85149';
                        defData.pins.forEach(p => {{
                            const px = p.x * scale + panX;
                            const py = panY - p.y * scale;
                            ctx.beginPath();
                            ctx.arc(px, py, 3, 0, 2 * Math.PI);
                            ctx.fill();
                        }});
                    }}
                }}
            </script>
            """

        # GROUPED ARTIFACTS & EVIDENCE (Feature 8)
        content += f"""
        <div class="card">
            <h2>Grouped Evidence & Research Artifacts</h2>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem;">
                Repository-relative artifact manifests and cryptographic SHA256 signatures.
            </p>
            
            <h4 style="color: var(--accent-blue); margin-top: 1rem;">LAYOUT ARTIFACTS</h4>
            <table>
                <thead><tr><th>Artifact</th><th>Relative Path / ID</th><th>Availability</th><th>SHA256 Hash</th></tr></thead>
                <tbody>
                    <tr><td>DEF File</td><td><code>{artifacts.get('def','-') or '—'}</code></td><td><span class="badge {'badge-success' if artifacts.get('def') else 'badge-incomplete'}">{'AVAILABLE' if artifacts.get('def') else 'NOT_GENERATED'}</span></td><td><code>{data.get('configuration',{}).get('config_hash','-')[:16]}...</code></td></tr>
                    <tr><td>ODB File</td><td><code>{artifacts.get('odb','-') or '—'}</code></td><td><span class="badge {'badge-success' if artifacts.get('odb') else 'badge-incomplete'}">{'AVAILABLE' if artifacts.get('odb') else 'NOT_GENERATED'}</span></td><td><code>—</code></td></tr>
                </tbody>
            </table>

            <h4 style="color: var(--accent-green); margin-top: 1rem;">REPORTS & LOGS</h4>
            <table>
                <thead><tr><th>Artifact</th><th>Type</th><th>Count</th><th>Action</th></tr></thead>
                <tbody>
                    <tr><td>Manufacturability Report</td><td>Antenna / DRC Signoff</td><td>1 report</td><td><code>{evidence.get('manufacturability_report','—') or '—'}</code></td></tr>
                    <tr><td>Tool Execution Logs</td><td>OpenROAD / Yosys Logs</td><td>{evidence.get('logs_count',0)} logs</td><td>Verified Log Bundle</td></tr>
                </tbody>
            </table>
        </div>
        """

        self.send_html(render_page(f"Experiment {exp_id}", content, active="experiments"))

    # ----------------------------------------------------------------------
    # 5. TECHNOLOGY COMPARISON MODE
    # ----------------------------------------------------------------------
    def render_technology_comparison(self, query_str: str):
        params = parse_qs(query_str)
        des_id = params.get("design", ["DES-001"])[0]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM technologies ORDER BY node_nm DESC")
        techs = cur.fetchall()

        tech_matrix = []
        for t in techs:
            tid = t["technology_id"]
            cur.execute("""
                SELECT e.experiment_id, e.name, e.status,
                       (SELECT value FROM metrics WHERE experiment_id=e.experiment_id AND name='cell_count') as cell_count,
                       (SELECT value FROM metrics WHERE experiment_id=e.experiment_id AND name='core_area_um2') as core_area,
                       (SELECT value FROM metrics WHERE experiment_id=e.experiment_id AND name='wns_ns') as wns
                FROM experiments e
                WHERE e.technology_id=? AND e.design_id=? AND e.status='SUCCESS'
                ORDER BY e.experiment_id DESC LIMIT 1
            """, (tid, des_id))
            row = cur.fetchone()

            # Determine comparability flag
            comp_flag = "NOT_COMPARABLE"
            reason = "No successful baseline completed for this node"
            if row:
                if tid in ["sky130", "nangate45", "asap7"]:
                    comp_flag = "COMPARABLE"
                    reason = "Standardized 20ns clock constraint and full routing signoff"
                elif tid == "ics55":
                    comp_flag = "PARTIALLY_COMPARABLE"
                    reason = "LEF property modification required for antenna signoff"
                else:
                    comp_flag = "PARTIALLY_COMPARABLE"
                    reason = "Research PDK model limitation during placement"

            tech_matrix.append({
                "tech_id": tid,
                "name": t["name"],
                "node": t["node_nm"],
                "arch": t["device_architecture"],
                "pdk_status": t["status"],
                "exp": row,
                "comp_flag": comp_flag,
                "reason": reason
            })

        conn.close()

        content = f"""
        <div class="card">
            <h1>Cross-Technology Node Comparison</h1>
            <p style="color: var(--text-muted); margin-bottom: 1rem;">
                Comparing physical design metrics for design <strong>{des_id} (PicoRV32)</strong> across silicon PDK nodes.
            </p>
            <div style="margin-bottom: 1.5rem;">
                <label><strong>Select RTL Design:</strong></label>
                <select onchange="location.href='/technologies/compare?design=' + this.value;">
                    <option value="DES-001" {"selected" if des_id=="DES-001" else ""}>PicoRV32 32-bit CPU (DES-001)</option>
                    <option value="DES-002" {"selected" if des_id=="DES-002" else ""}>SERV RISC-V (DES-002)</option>
                    <option value="DES-003" {"selected" if des_id=="DES-003" else ""}>Ibex Core (DES-003)</option>
                </select>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Technology Node</th>
                        <th>Node (nm)</th>
                        <th>Architecture</th>
                        <th>Representative Exp</th>
                        <th>Comparability Level</th>
                        <th>Cell Count</th>
                        <th>Core Area (μm²)</th>
                        <th>WNS (ns)</th>
                    </tr>
                </thead>
                <tbody>
        """
        for tm in tech_matrix:
            exp = tm["exp"]
            exp_str = f"<a href='/experiments/{exp['experiment_id']}'><strong>{exp['experiment_id']}</strong></a>" if exp else "—"
            c_badge = "badge-comparable" if tm["comp_flag"] == "COMPARABLE" else ("badge-partial" if tm["comp_flag"] == "PARTIALLY_COMPARABLE" else "badge-not-comparable")
            cell_str = f"{int(exp['cell_count']):,}" if exp and exp['cell_count'] is not None else "—"
            area_str = f"{float(exp['core_area']):,.1f}" if exp and exp['core_area'] is not None else "—"
            wns_str = f"{float(exp['wns']):.2f}" if exp and exp['wns'] is not None else "—"

            content += f"""
            <tr>
                <td><strong>{tm['name']}</strong> ({tm['tech_id']})</td>
                <td><span style="font-family: var(--font-mono);">{tm['node']} nm</span></td>
                <td>{tm['arch']}</td>
                <td>{exp_str}</td>
                <td><span class="badge {c_badge}">{tm['comp_flag']}</span><br><span style="font-size: 0.75rem; color: var(--text-muted);">{tm['reason']}</span></td>
                <td style="font-family: var(--font-mono);">{cell_str}</td>
                <td style="font-family: var(--font-mono);">{area_str}</td>
                <td style="font-family: var(--font-mono);">{wns_str}</td>
            </tr>
            """
        content += "</tbody></table></div>"

        self.send_html(render_page("Technology Node Comparison", content, active="technologies"))

    def render_technologies_list(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM technologies ORDER BY node_nm DESC")
        rows = cur.fetchall()
        conn.close()

        content = """
        <div class="card">
            <h1>Technologies Registry</h1>
            <p style="color: var(--text-muted);">Silicon semiconductor process technology nodes integrated in Open TAEDA.</p>
            <table>
                <thead>
                    <tr><th>ID</th><th>Name</th><th>Node (nm)</th><th>Device Architecture</th><th>Type</th><th>Status</th><th>Validation Level</th></tr>
                </thead>
                <tbody>
        """
        for r in rows:
            content += f"""
            <tr>
                <td><a href="/technologies/{r['technology_id']}"><strong>{r['technology_id']}</strong></a></td>
                <td>{r['name']}</td>
                <td><span style="font-family: var(--font-mono);">{r['node_nm']} nm</span></td>
                <td>{r['device_architecture']}</td>
                <td>{r['device_type']}</td>
                <td><span class="badge badge-tech">{r['status']}</span></td>
                <td>{r['validation_level']}</td>
            </tr>
            """
        content += "</tbody></table></div>"
        self.send_html(render_page("Technologies Registry", content, active="technologies"))

    def render_technology_detail(self, tech_id: str):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM technologies WHERE technology_id=?", (tech_id,))
        t = cur.fetchone()

        cur.execute("SELECT experiment_id, name, status, experiment_type FROM experiments WHERE technology_id=?", (tech_id,))
        exps = cur.fetchall()
        conn.close()

        if not t:
            self.send_html("<h1>404 Technology Not Found</h1>", 404)
            return

        content = f"""
        <div class="card">
            <h1>Technology Node: {t['name']} ({t['technology_id']})</h1>
            <table>
                <tr><td>Node Size</td><td><strong>{t['node_nm']} nm</strong></td></tr>
                <tr><td>Device Architecture</td><td>{t['device_architecture']}</td></tr>
                <tr><td>Device Type</td><td>{t['device_type']}</td></tr>
                <tr><td>PDK Status</td><td><span class="badge badge-tech">{t['status']}</span></td></tr>
                <tr><td>Validation Level</td><td>{t['validation_level']}</td></tr>
            </table>
        </div>

        <div class="card">
            <h2>Associated Experiments ({len(exps)})</h2>
            <table>
                <thead><tr><th>ID</th><th>Name</th><th>Type</th><th>Status</th></tr></thead>
                <tbody>
        """
        for e in exps:
            st_cls = "badge-success" if e["status"] == "SUCCESS" else ("badge-failed" if e["status"] == "FAILED" else "badge-incomplete")
            content += f"<tr><td><a href='/experiments/{e['experiment_id']}'><strong>{e['experiment_id']}</strong></a></td><td>{e['name']}</td><td>{e['experiment_type']}</td><td><span class='badge {st_cls}'>{e['status']}</span></td></tr>"
        content += "</tbody></table></div>"

        self.send_html(render_page(f"Technology {t['name']}", content, active="technologies"))

    def render_designs_list(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM designs ORDER BY design_id")
        rows = cur.fetchall()
        conn.close()

        content = """
        <div class="card">
            <h1>Designs Registry</h1>
            <p style="color: var(--text-muted);">RTL processor designs and benchmark circuits integrated in Open TAEDA.</p>
            <table>
                <thead>
                    <tr><th>ID</th><th>Name</th><th>Top Module</th></tr>
                </thead>
                <tbody>
        """
        for r in rows:
            content += f"""
            <tr>
                <td><a href="/designs/{r['design_id']}"><strong>{r['design_id']}</strong></a></td>
                <td>{r['name']}</td>
                <td><code>{r['top_module']}</code></td>
            </tr>
            """
        content += "</tbody></table></div>"
        self.send_html(render_page("Designs Registry", content, active="designs"))

    def render_design_detail(self, des_id: str):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM designs WHERE design_id=?", (des_id,))
        d = cur.fetchone()

        cur.execute("SELECT experiment_id, name, technology_id, status FROM experiments WHERE design_id=?", (des_id,))
        exps = cur.fetchall()
        conn.close()

        if not d:
            self.send_html("<h1>404 Design Not Found</h1>", 404)
            return

        content = f"""
        <div class="card">
            <h1>RTL Design: {d['name']} ({d['design_id']})</h1>
            <table>
                <tr><td>Top Module</td><td><code>{d['top_module']}</code></td></tr>
            </table>
        </div>

        <div class="card">
            <h2>Associated Experiments ({len(exps)})</h2>
            <table>
                <thead><tr><th>ID</th><th>Name</th><th>Technology</th><th>Status</th></tr></thead>
                <tbody>
        """
        for e in exps:
            st_cls = "badge-success" if e["status"] == "SUCCESS" else ("badge-failed" if e["status"] == "FAILED" else "badge-incomplete")
            content += f"<tr><td><a href='/experiments/{e['experiment_id']}'><strong>{e['experiment_id']}</strong></a></td><td>{e['name']}</td><td><span class='badge badge-tech'>{e['technology_id']}</span></td><td><span class='badge {st_cls}'>{e['status']}</span></td></tr>"
        content += "</tbody></table></div>"

        self.send_html(render_page(f"Design {d['name']}", content, active="designs"))

    # ----------------------------------------------------------------------
    # API ENDPOINTS
    # ----------------------------------------------------------------------
    def api_list_experiments(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM experiments ORDER BY experiment_id ASC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        self.send_json(rows)

    def api_get_experiment(self, exp_id: str):
        mfile = MANIFESTS_DIR / f"{exp_id}.yaml"
        if not mfile.exists():
            self.send_json({"error": f"Experiment {exp_id} not found"}, 404)
            return
        with open(mfile, "r") as f:
            data = yaml.safe_load(f)
        self.send_json(data)

    def api_get_def(self, exp_id: str):
        mfile = MANIFESTS_DIR / f"{exp_id}.yaml"
        if not mfile.exists():
            self.send_json({"error": f"Experiment {exp_id} not found"}, 404)
            return
        with open(mfile, "r") as f:
            data = yaml.safe_load(f) or {}

        def_path = data.get("artifacts", {}).get("def")
        if not def_path:
            self.send_json({"error": f"No DEF artifact recorded for {exp_id}"}, 404)
            return

        def_data = parse_def_file(Path(def_path))
        self.send_json(def_data)

    def api_matrix(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM experiments")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        self.send_json(rows)

def run_server(port: int = 8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, WebHandler)
    print(f"==================================================")
    print(f"Open TAEDA Research Server listening on http://localhost:{port}")
    print(f"Spotlight Page: http://localhost:{port}/experiments/EXP-000022")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
