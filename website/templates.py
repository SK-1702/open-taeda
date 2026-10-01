# Open TAEDA Research Platform HTML Templates & Scripts (Iteration 1)

BASE_HEADER = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} | Open TAEDA Research Platform</title>
    <style>
        :root {
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --border-color: #30363d;
            --text-main: #c9d1d9;
            --text-heading: #f0f6fc;
            --text-muted: #8b949e;
            --accent-blue: #58a6ff;
            --accent-cyan: #39c5cf;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --accent-orange: #d29922;
            --accent-purple: #bc8cff;
            --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: var(--font-sans);
            line-height: 1.6;
            padding: 0;
            margin: 0;
        }

        header {
            background-color: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .logo {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-heading);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-badge {
            background: linear-gradient(135deg, #1f6feb, #238636);
            color: #fff;
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-family: var(--font-mono);
        }

        nav { display: flex; gap: 1.5rem; }
        nav a {
            color: var(--text-muted);
            text-decoration: none;
            font-weight: 500;
            font-size: 0.95rem;
            transition: color 0.2s;
        }
        nav a:hover, nav a.active { color: var(--accent-blue); }

        .container {
            max-width: 1380px;
            margin: 2rem auto;
            padding: 0 1.5rem;
        }

        .card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }

        h1, h2, h3, h4 { color: var(--text-heading); margin-bottom: 1rem; }
        h1 { font-size: 1.8rem; }
        h2 { font-size: 1.35rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; margin-top: 0.5rem; }

        .badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            font-family: var(--font-mono);
        }
        .badge-success { background: rgba(63, 185, 80, 0.15); color: var(--accent-green); border: 1px solid rgba(63, 185, 80, 0.4); }
        .badge-failed { background: rgba(248, 81, 73, 0.15); color: var(--accent-red); border: 1px solid rgba(248, 81, 73, 0.4); }
        .badge-incomplete { background: rgba(210, 153, 34, 0.15); color: var(--accent-orange); border: 1px solid rgba(210, 153, 34, 0.4); }
        .badge-tech { background: rgba(88, 166, 255, 0.15); color: var(--accent-blue); border: 1px solid rgba(88, 166, 255, 0.4); }
        .badge-comparable { background: rgba(63, 185, 80, 0.15); color: var(--accent-green); border: 1px solid rgba(63, 185, 80, 0.4); }
        .badge-partial { background: rgba(210, 153, 34, 0.15); color: var(--accent-orange); border: 1px solid rgba(210, 153, 34, 0.4); }
        .badge-not-comparable { background: rgba(248, 81, 73, 0.15); color: var(--accent-red); border: 1px solid rgba(248, 81, 73, 0.4); }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.88rem;
        }
        th, td {
            text-align: left;
            padding: 0.65rem 0.75rem;
            border-bottom: 1px solid var(--border-color);
        }
        th { background-color: rgba(255, 255, 255, 0.02); color: var(--text-muted); font-weight: 600; cursor: pointer; user-select: none; }
        th:hover { color: var(--accent-blue); }
        tr:hover { background-color: rgba(255, 255, 255, 0.02); }

        .toolbar {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            align-items: center;
            background-color: var(--bg-dark);
            border: 1px solid var(--border-color);
            padding: 0.75rem 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
        }

        .toolbar select, .toolbar input[type="text"], .btn {
            background-color: var(--bg-card);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            padding: 0.4rem 0.75rem;
            border-radius: 4px;
            font-size: 0.85rem;
            font-family: var(--font-sans);
        }
        .toolbar select:focus, .toolbar input:focus { outline: none; border-color: var(--accent-blue); }

        .btn {
            cursor: pointer;
            font-weight: 600;
            transition: background 0.2s, border 0.2s;
        }
        .btn-primary { background-color: #238636; color: #fff; border-color: rgba(240, 246, 252, 0.1); }
        .btn-primary:hover { background-color: #2ea043; }
        .btn-secondary { background-color: #21262d; color: var(--text-main); }
        .btn-secondary:hover { background-color: #30363d; }

        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
        .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
        .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }

        .stat-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.25rem;
            text-align: center;
        }
        .stat-value { font-size: 2rem; font-weight: 700; color: var(--text-heading); font-family: var(--font-mono); }
        .stat-label { font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }

        .flow-node {
            background-color: var(--bg-dark);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 1rem;
            text-align: center;
        }

        pre, code {
            font-family: var(--font-mono);
            background-color: #010409;
            border-radius: 4px;
        }
        pre {
            padding: 1rem;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            color: #e6edf3;
            font-size: 0.85rem;
        }

        a { color: var(--accent-blue); text-decoration: none; }
        a:hover { text-decoration: underline; }

        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid var(--border-color);
            margin-top: 3rem;
        }

        #layoutCanvas {
            background-color: #05070a;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            cursor: crosshair;
            width: 100%;
            height: 500px;
        }
    </style>
</head>
<body>
    <header>
        <a href="/" class="logo">
            <span>Open TAEDA</span>
            <span class="logo-badge">v0.1</span>
        </a>
        <nav>
            <a href="/" class="{% if active=='home' %}active{% endif %}">Dashboard</a>
            <a href="/experiments" class="{% if active=='experiments' %}active{% endif %}">Experiments</a>
            <a href="/technologies" class="{% if active=='technologies' %}active{% endif %}">Technologies</a>
            <a href="/designs" class="{% if active=='designs' %}active{% endif %}">Designs</a>
        </nav>
    </header>
    <div class="container">
"""

BASE_FOOTER = """
    </div>
    <footer>
        <p>Open TAEDA — Technology-Aware Semiconductor EDA Research Platform</p>
        <p>GitHub Repository: <a href="https://github.com/SK-1702/open-taeda" target="_blank">git@github.com:SK-1702/open-taeda.git</a></p>
    </footer>
</body>
</html>
"""
