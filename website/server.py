import json
import sqlite3
import re
import yaml
from typing import Any, Dict, List
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from website.templates import BASE_HEADER, BASE_FOOTER

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
        # Silence verbose standard http log unless needed
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
        elif path.startswith("/experiments/"):
            exp_id = path.split("/")[-1]
            self.render_experiment_detail(exp_id)
        elif path == "/technologies":
            self.render_technologies_list()
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
        elif path.startswith("/api/experiments/"):
            exp_id = path.split("/")[-1]
            self.api_get_experiment(exp_id)
        elif path == "/api/matrix":
            self.api_matrix()
        else:
            self.send_html("<h1>404 Not Found</h1><p>The requested research page does not exist.</p>", 404)

    def render_home(self):
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT count(*) FROM experiments")
        total_exp = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM experiments WHERE status='SUCCESS'")
        success_exp = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM technologies")
        total_tech = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM designs")
        total_des = cur.fetchone()[0]

        # Get matrix: Technologies x Designs
        cur.execute("SELECT technology_id, name FROM technologies ORDER BY node_nm DESC")
        techs = cur.fetchall()
        cur.execute("SELECT design_id, name FROM designs ORDER BY design_id")
        designs = cur.fetchall()

        matrix = {}
        for t in techs:
            matrix[t["technology_id"]] = {}
            for d in designs:
                cur.execute("""
                    SELECT experiment_id, status, name FROM experiments 
                    WHERE technology_id=? AND design_id=?
                    ORDER BY experiment_id DESC LIMIT 1
                """, (t["technology_id"], d["design_id"]))
                row = cur.fetchone()
                matrix[t["technology_id"]][d["design_id"]] = row

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
            <p style="font-size: 1.1rem; color: var(--text-muted);">
                Open Technology-Aware Semiconductor EDA Research Platform. Systematic physical design synthesis, memory footprint optimization, failure forensics, and cross-PDK experimental provenance tracking across Sky130, ICsprout55, NanGate45, ASAP7 FinFET, and GT3/GT2N GAAFET technologies.
            </p>
            <div style="margin-top: 1rem; display: flex; gap: 1rem;">
                <a href="/experiments/EXP-000022" class="badge badge-success" style="padding: 0.5rem 1rem; font-size: 0.9rem;">⭐ View Spotlight: EXP-000022 ASAP7 7nm Signoff</a>
                <a href="/experiments" class="badge badge-tech" style="padding: 0.5rem 1rem; font-size: 0.9rem;">Browse All 64 Experiments</a>
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
                <div class="stat-value" style="color: var(--accent-blue);">{total_tech}</div>
                <div class="stat-label">Technology Nodes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--accent-purple);">{total_des}</div>
                <div class="stat-label">RTL Designs</div>
            </div>
        </div>

        <div class="card">
            <h2>Research Matrix (Technology × Design Coverage)</h2>
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
                row = matrix[t["technology_id"]][d["design_id"]]
                if row:
                    st_cls = "badge-success" if row["status"] == "SUCCESS" else ("badge-failed" if row["status"] == "FAILED" else "badge-incomplete")
                    content += f"<td><a href='/experiments/{row['experiment_id']}' class='badge {st_cls}'>{row['experiment_id']} ({row['status']})</a></td>"
                else:
                    content += "<td><span style='color: var(--text-muted);'>-</span></td>"
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
        content += "</tbody></table></div>"

        self.send_html(render_page("Research Platform Dashboard", content, active="home"))

    def render_experiments_list(self, query_str: str):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT e.experiment_id, e.name, e.technology_id, e.design_id, e.experiment_type, e.status,
                   (SELECT value FROM metrics WHERE experiment_id=e.experiment_id AND name='cell_count') as cell_count,
                   (SELECT value FROM metrics WHERE experiment_id=e.experiment_id AND name='core_area_um2') as core_area,
                   (SELECT value FROM metrics WHERE experiment_id=e.experiment_id AND name='wns_ns') as wns,
                   (SELECT value FROM metrics WHERE experiment_id=e.experiment_id AND name='drc_errors') as drc,
                   (SELECT value FROM metrics WHERE experiment_id=e.experiment_id AND name='antenna_violations') as ant
            FROM experiments e
            ORDER BY e.experiment_id ASC
        """)
        rows = cur.fetchall()
        conn.close()

        content = """
        <div class="card">
            <h1>Experiment Explorer</h1>
            <p style="color: var(--text-muted);">Browsing all normalized, provenance-preserved EDA experiments across technology nodes.</p>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Technology</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Cell Count</th>
                        <th>Core Area (μm²)</th>
                        <th>WNS (ns)</th>
                        <th>DRC</th>
                        <th>Antenna</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
        """
        for r in rows:
            st_cls = "badge-success" if r["status"] == "SUCCESS" else ("badge-failed" if r["status"] == "FAILED" else "badge-incomplete")
            cell = int(r["cell_count"]) if r["cell_count"] is not None else "-"
            area = f"{float(r['core_area']):,.1f}" if r["core_area"] is not None else "-"
            wns = f"{float(r['wns']):.2f}" if r["wns"] is not None else "-"
            drc = int(r["drc"]) if r["drc"] is not None else "-"
            ant = int(r["ant"]) if r["ant"] is not None else "-"

            content += f"""
            <tr>
                <td><a href="/experiments/{r['experiment_id']}"><strong>{r['experiment_id']}</strong></a></td>
                <td>{r['name']}</td>
                <td><span class="badge badge-tech">{r['technology_id']}</span></td>
                <td><span style="font-family: var(--font-mono); font-size: 0.85rem;">{r['experiment_type']}</span></td>
                <td><span class="badge {st_cls}">{r['status']}</span></td>
                <td style="font-family: var(--font-mono);">{cell}</td>
                <td style="font-family: var(--font-mono);">{area}</td>
                <td style="font-family: var(--font-mono);">{wns}</td>
                <td style="font-family: var(--font-mono);">{drc}</td>
                <td style="font-family: var(--font-mono);">{ant}</td>
                <td><a href="/experiments/{r['experiment_id']}">View Page &rarr;</a></td>
            </tr>
            """
        content += "</tbody></table></div>"
        self.send_html(render_page("Experiment Explorer", content, active="experiments"))

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

        st_cls = "badge-success" if status == "SUCCESS" else ("badge-failed" if status == "FAILED" else "badge-incomplete")

        # Custom rendering logic for EXP-000022 spotlight
        is_spotlight = (exp_id == "EXP-000022")

        content = f"""
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1>{exp_id}: {exp.get('name')}</h1>
                    <p style="color: var(--text-muted);">
                        Campaign: <strong>{exp.get('campaign')}</strong> | Type: <strong>{exp.get('type')}</strong>
                    </p>
                </div>
                <span class="badge {st_cls}" style="font-size: 1rem; padding: 0.4rem 1rem;">{status}</span>
            </div>
        </div>
        """

        if is_spotlight:
            content += """
            <div class="card" style="border: 2px solid var(--accent-green); background: rgba(63, 185, 80, 0.05);">
                <h2>🌟 Landmark Research Experiment: ASAP7 7nm FinFET Memory Footprint Optimization</h2>
                <p>This experiment demonstrates a major Category A physical design resolution for 7nm FinFET technology in OpenROAD/OpenLane.</p>
                <div class="grid-2" style="margin-top: 1rem;">
                    <div style="background-color: var(--bg-dark); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-color);">
                        <h4 style="color: var(--accent-red);">Baseline Experiment (EXP-000020 / exp1)</h4>
                        <ul>
                            <li><strong>Physical Component Count:</strong> 414,131 instances (390,943 filler cells)</li>
                            <li><strong>Filler Cell Area:</strong> 94.4% of total database components</li>
                            <li><strong>Execution Result:</strong> TritonRoute crashed due to 15.0 GB Host RAM Out-Of-Memory (OOM) limit in Step 23 detailed routing.</li>
                        </ul>
                    </div>
                    <div style="background-color: var(--bg-dark); padding: 1rem; border-radius: 6px; border: 1px solid var(--border-color);">
                        <h4 style="color: var(--accent-green);">Optimized Experiment (EXP-000022 / exp6)</h4>
                        <ul>
                            <li><strong>Intervention:</strong> <code>FILL_CELL=""</code> (Pre-routing filler cell suppression)</li>
                            <li><strong>Database Components:</strong> 23,188 instances (17.86× reduction)</li>
                            <li><strong>Peak RAM:</strong> ~6.5 GB peak (3.2× memory relief)</li>
                            <li><strong>Routing & Signoff:</strong> TritonRoute Step 23 completed cleanly (124,707 μm wire length, 126,938 vias, 0 Pin & 0 Net ARC antenna violations).</li>
                        </ul>
                    </div>
                </div>
            </div>
            """

        content += """
        <div class="card">
            <h2>Four Scientific Truths</h2>
            <div class="grid-2">
                <div>
                    <h3>1. Design Truth</h3>
                    <table>
                        <tr><td>Design ID / Name</td><td><strong>""" + des.get("id", "") + " / " + des.get("name", "") + """</strong></td></tr>
                        <tr><td>Top Module</td><td><code>""" + des.get("top", "") + """</code></td></tr>
                        <tr><td>Revision</td><td>""" + des.get("revision", "") + """</td></tr>
                        <tr><td>RTL Source</td><td><code>""" + data.get("inputs", {}).get("rtl", "") + """</code></td></tr>
                        <tr><td>SDC Constraints</td><td><code>""" + data.get("inputs", {}).get("constraints", "") + """</code></td></tr>
                    </table>
                </div>
                <div>
                    <h3>2. Technology Truth</h3>
                    <table>
                        <tr><td>Technology ID</td><td><span class="badge badge-tech">""" + tech.get("id", "") + """</span></td></tr>
                        <tr><td>Revision</td><td>""" + tech.get("revision", "") + """</td></tr>
                        <tr><td>Flow Framework</td><td>""" + flow.get("name", "") + " (" + flow.get("version", "") + """)</td></tr>
                        <tr><td>Clock Period</td><td>""" + str(data.get("configuration", {}).get("clock_period_ns")) + """ ns</td></tr>
                        <tr><td>Core Utilization</td><td>""" + str(data.get("configuration", {}).get("core_utilization")) + """ %</td></tr>
                    </table>
                </div>
            </div>

            <div class="grid-2" style="margin-top: 1.5rem;">
                <div>
                    <h3>3. Tool Truth</h3>
                    <table>
                        <tr><td>Yosys Version</td><td><code>""" + tools.get("yosys", "") + """</code></td></tr>
                        <tr><td>OpenROAD Version</td><td><code>""" + tools.get("openroad", "") + """</code></td></tr>
                        <tr><td>OpenSTA Version</td><td><code>""" + tools.get("opensta", "") + """</code></td></tr>
                        <tr><td>OS Environment</td><td>""" + data.get("environment", {}).get("os", "") + """</td></tr>
                    </table>
                </div>
                <div>
                    <h3>4. Physical / Experimental Truth</h3>
                    <table>
                        <tr><td>Cell Count</td><td><code>""" + str(metrics.get("cell_count", "-")) + """</code></td></tr>
                        <tr><td>Core Area</td><td><code>""" + str(metrics.get("core_area_um2", "-")) + """ μm²</code></td></tr>
                        <tr><td>Wire Length</td><td><code>""" + str(metrics.get("wirelength_um", "-")) + """ μm</code></td></tr>
                        <tr><td>Vias Count</td><td><code>""" + str(metrics.get("vias_count", "-")) + """</code></td></tr>
                        <tr><td>DRC Errors</td><td><code>""" + str(metrics.get("drc_errors", "0")) + """</code></td></tr>
                        <tr><td>Antenna Violations</td><td><code>""" + str(metrics.get("antenna_violations", "0")) + """</code></td></tr>
                    </table>
                </div>
            </div>
        </div>
        """

        # Stage Execution Timeline
        content += """
        <div class="card">
            <h2>Stage Execution Timeline</h2>
            <table>
                <thead>
                    <tr><th>Sequence</th><th>Stage Name</th><th>Status</th></tr>
                </thead>
                <tbody>
        """
        seq = 1
        for st_name, st_info in stages.items():
            st_val = st_info.get("status", "NOT_RUN") if isinstance(st_info, dict) else str(st_info)
            badge_c = "badge-success" if st_val == "COMPLETED" else ("badge-failed" if st_val == "FAILED" else "badge-incomplete")
            content += f"<tr><td>{seq}</td><td><strong>{st_name}</strong></td><td><span class='badge {badge_c}'>{st_val}</span></td></tr>"
            seq += 1
        content += "</tbody></table></div>"

        # Failure & Interventions
        if failure or interventions:
            content += "<div class='card'><h2>Forensics & Interventions</h2>"
            if failure:
                content += f"""
                <div style="background-color: rgba(248, 81, 73, 0.1); border: 1px solid var(--accent-red); padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
                    <h3 style="color: var(--accent-red);">Failure Forensics ({failure.get('error_code')})</h3>
                    <p><strong>Stage:</strong> {failure.get('stage')} | <strong>Tool:</strong> {failure.get('tool')}</p>
                    <p><strong>Error Message:</strong> {failure.get('error_message')}</p>
                    <p><strong>Root Cause Class:</strong> <span class="badge badge-failed">{failure.get('root_cause_class')}</span></p>
                </div>
                """
            if interventions:
                for inv in interventions:
                    content += f"""
                    <div style="background-color: rgba(88, 166, 255, 0.1); border: 1px solid var(--accent-blue); padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
                        <h3 style="color: var(--accent-blue);">Intervention: {inv.get('intervention_id')} ({inv.get('classification')})</h3>
                        <p><strong>Parent Experiment:</strong> {inv.get('parent_experiment')}</p>
                        <p><strong>Parameter Changed:</strong> <code>{inv.get('changed_parameter')}</code> in <code>{inv.get('changed_file')}</code> ({inv.get('before_value')} &rarr; {inv.get('after_value')})</p>
                        <p><strong>Reason:</strong> {inv.get('reason')}</p>
                        <p><strong>Result:</strong> {inv.get('result')}</p>
                    </div>
                    """
            content += "</div>"

        # Evidence & Artifacts
        content += f"""
        <div class="card">
            <h2>Evidence & Artifact References</h2>
            <table>
                <tr><td>Source Run Directory</td><td><code>{exp.get('source_run_path')}</code></td></tr>
                <tr><td>Layout DEF File</td><td><code>{artifacts.get('def', '-')}</code></td></tr>
                <tr><td>Database ODB File</td><td><code>{artifacts.get('odb', '-')}</code></td></tr>
                <tr><td>Configuration Hash</td><td><code>{data.get('configuration', {}).get('config_hash', '-')}</code></td></tr>
            </table>
        </div>
        """

        self.send_html(render_page(f"Experiment {exp_id}", content, active="experiments"))

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
