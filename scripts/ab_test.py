"""A/B testing app for comparing HTML-based vs screenshot-based bookmark summaries."""

import base64
import math
import os
import random
import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cache.sqlite")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ab_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guid TEXT NOT NULL,
            summary_type TEXT NOT NULL,
            rating INTEGER NOT NULL,
            content_length INTEGER,
            created_at DATETIME DEFAULT (datetime('now'))
        )"""
    )
    # Migrate existing tables missing the content_length column
    cols = [r[1] for r in conn.execute("PRAGMA table_info(ab_ratings)").fetchall()]
    if "content_length" not in cols:
        conn.execute("ALTER TABLE ab_ratings ADD COLUMN content_length INTEGER")
    conn.commit()
    return conn


def get_eligible_guids(conn):
    """Get GUIDs that have both summary types and a screenshot."""
    cursor = conn.execute(
        """SELECT s.guid, s.url
           FROM summaries s
           JOIN screenshot_summaries ss ON s.guid = ss.guid
           JOIN link_cache lc ON s.url = lc.url
           WHERE lc.screenshot IS NOT NULL
             AND s.summary IS NOT NULL
             AND ss.summary IS NOT NULL"""
    )
    return cursor.fetchall()


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/api/trial")
def trial():
    conn = get_db()
    eligible = get_eligible_guids(conn)
    if not eligible:
        conn.close()
        return jsonify({"error": "No eligible bookmarks found"}), 404

    guid, url = random.choice(eligible)
    summary_type = random.choice(["html", "screenshot"])

    if summary_type == "html":
        row = conn.execute("SELECT summary FROM summaries WHERE guid = ?", (guid,)).fetchone()
    else:
        row = conn.execute("SELECT summary FROM screenshot_summaries WHERE guid = ?", (guid,)).fetchone()

    cache_row = conn.execute("SELECT screenshot, length(content) FROM link_cache WHERE url = ?", (url,)).fetchone()
    conn.close()

    screenshot_b64 = base64.b64encode(cache_row[0]).decode("ascii") if cache_row and cache_row[0] else None
    content_length = cache_row[1] if cache_row else 0

    return jsonify({
        "guid": guid,
        "url": url,
        "summary": row[0] if row else None,
        "summary_type": summary_type,
        "screenshot": screenshot_b64,
        "content_length": content_length,
    })


@app.route("/api/rate", methods=["POST"])
def rate():
    data = request.get_json()
    guid = data["guid"]
    summary_type = data["summary_type"]
    rating = int(data["rating"])

    content_length = data.get("content_length", 0)

    conn = get_db()
    conn.execute(
        "INSERT INTO ab_ratings (guid, summary_type, rating, content_length) VALUES (?, ?, ?, ?)",
        (guid, summary_type, rating, content_length),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/results")
def results():
    conn = get_db()
    rows = conn.execute(
        "SELECT summary_type, rating, content_length FROM ab_ratings"
    ).fetchall()
    conn.close()

    by_type = {"html": [], "screenshot": []}
    rated_rows = []
    all_lengths = []
    for stype, rating, clen in rows:
        if stype in by_type:
            by_type[stype].append(rating)
            rated_rows.append((stype, rating, clen or 0))
            all_lengths.append(clen or 0)

    def prop_stats(ratings):
        n = len(ratings)
        if n == 0:
            return {"n": 0, "passes": 0, "pass_rate": None, "ci_low": None, "ci_high": None}
        passes = sum(ratings)
        p = passes / n
        se = math.sqrt(p * (1 - p) / n) if 0 < p < 1 else 0
        return {"n": n, "passes": passes, "pass_rate": round(p, 3),
                "ci_low": round(max(0, p - 1.96 * se), 3),
                "ci_high": round(min(1, p + 1.96 * se), 3)}

    stats = {stype: prop_stats(ratings) for stype, ratings in by_type.items()}

    # Two-proportion z-test
    z_test = None
    html_r = by_type["html"]
    ss_r = by_type["screenshot"]
    if len(html_r) >= 2 and len(ss_r) >= 2:
        n1, n2 = len(html_r), len(ss_r)
        p1, p2 = sum(html_r) / n1, sum(ss_r) / n2
        p_pool = (sum(html_r) + sum(ss_r)) / (n1 + n2)
        se_diff = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2)) if 0 < p_pool < 1 else 0
        z_stat = (p1 - p2) / se_diff if se_diff > 0 else 0
        p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z_stat) / math.sqrt(2))))
        z_test = {"z_stat": round(z_stat, 4), "p_value": round(p_value, 4)}

    # Content length breakdown: median split into short/long
    length_breakdown = None
    if len(all_lengths) >= 4:
        sorted_lens = sorted(all_lengths)
        median_len = sorted_lens[len(sorted_lens) // 2]
        buckets = {}
        for stype, rating, clen in rated_rows:
            bucket = "short" if clen <= median_len else "long"
            buckets.setdefault((stype, bucket), []).append(rating)
        length_breakdown = {"median_length": median_len, "cells": {}}
        for stype in ["html", "screenshot"]:
            for bucket in ["short", "long"]:
                length_breakdown["cells"][f"{stype}_{bucket}"] = prop_stats(buckets.get((stype, bucket), []))

    sufficient = len(html_r) >= 30 and len(ss_r) >= 30
    return jsonify({"stats": stats, "z_test": z_test, "sufficient_power": sufficient,
                    "length_breakdown": length_breakdown})


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Summary A/B Test</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
  .container { max-width: 1400px; margin: 0 auto; padding: 2rem 1rem; }
  h1 { text-align: center; margin-bottom: 1.5rem; color: #f8fafc; font-size: 1.5rem; }
  .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; justify-content: center; }
  .tab { padding: 0.5rem 1.5rem; border: 1px solid #334155; border-radius: 0.5rem; cursor: pointer;
         background: transparent; color: #94a3b8; font-size: 0.9rem; transition: all 0.15s; }
  .tab.active { background: #3b82f6; border-color: #3b82f6; color: white; }
  .tab:hover:not(.active) { border-color: #64748b; color: #e2e8f0; }

  /* Trial */
  .trial { display: flex; flex-direction: row; align-items: flex-start; gap: 2rem; }
  .trial-left { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
  .trial-right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1rem; }
  .screenshot { max-width: 100%; max-height: 600px; border-radius: 0.5rem; border: 1px solid #334155; object-fit: contain; }
  .url { color: #64748b; font-size: 0.8rem; word-break: break-all; text-align: center; }
  .summary-box { background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 1.25rem;
                  width: 100%; line-height: 1.6; font-size: 0.95rem; }
  .vote-btns { display: flex; gap: 1rem; justify-content: center; }
  .vote-btn { padding: 0.6rem 2rem; border: 2px solid #334155; border-radius: 0.5rem; cursor: pointer;
              font-size: 1rem; font-weight: 600; transition: all 0.15s; background: transparent; }
  .vote-btn.pass { color: #4ade80; border-color: #166534; }
  .vote-btn.pass:hover { background: #14532d; }
  .vote-btn.fail { color: #f87171; border-color: #7f1d1d; }
  .vote-btn.fail:hover { background: #450a0a; }
  .vote-btn.chosen { opacity: 1; transform: scale(1.05); }
  .vote-btn.pass.chosen { background: #14532d; }
  .vote-btn.fail.chosen { background: #450a0a; }
  .vote-btn.dimmed { opacity: 0.3; pointer-events: none; }
  .reveal { text-align: center; padding: 0.75rem 1.5rem; border-radius: 0.5rem; font-weight: 600; }
  .reveal.html { background: #1e3a5f; color: #60a5fa; }
  .reveal.screenshot { background: #3b1f2b; color: #f472b6; }
  #next-btn { padding: 0.5rem 2rem; border: none; border-radius: 0.5rem; background: #3b82f6;
              color: white; font-size: 1rem; cursor: pointer; display: none; }
  #next-btn:hover { background: #2563eb; }
  .progress { color: #64748b; font-size: 0.8rem; text-align: center; width: 100%; }

  /* Results */
  .results-section { display: none; }
  table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
  th, td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #334155; }
  th { color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
  td { font-size: 0.95rem; }
  .sig { padding: 0.75rem; border-radius: 0.5rem; text-align: center; margin-top: 1rem; font-weight: 600; }
  .sig.yes { background: #14532d; color: #4ade80; }
  .sig.no { background: #1e293b; color: #94a3b8; }
  .warn { background: #422006; color: #fbbf24; padding: 0.75rem; border-radius: 0.5rem; text-align: center; margin-bottom: 1rem; }
</style>
</head>
<body>
<div class="container">
  <h1>Summary Quality A/B Test</h1>
  <div class="tabs">
    <button class="tab active" onclick="showTab('trial')">Rate</button>
    <button class="tab" onclick="showTab('results')">Results</button>
  </div>

  <div id="trial-section" class="trial">
    <div class="trial-left">
      <img class="screenshot" id="screenshot" alt="Website screenshot" />
      <div class="url" id="url"></div>
    </div>
    <div class="trial-right">
      <div class="progress" id="progress"></div>
      <div class="summary-box" id="summary"></div>
      <div class="vote-btns" id="vote-btns">
        <button class="vote-btn pass" onclick="submitRating(1)">Pass</button>
        <button class="vote-btn fail" onclick="submitRating(0)">Fail</button>
      </div>
      <div class="reveal" id="reveal" style="display:none"></div>
      <button id="next-btn" onclick="loadTrial()">Next</button>
    </div>
  </div>

  <div id="results-section" class="results-section"></div>
</div>

<script>
let current = null;
let counts = {html: 0, screenshot: 0};

function showTab(name) {
  document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', i === (name === 'trial' ? 0 : 1)));
  document.getElementById('trial-section').style.display = name === 'trial' ? 'flex' : 'none';
  document.getElementById('results-section').style.display = name === 'results' ? 'block' : 'none';
  if (name === 'results') loadResults();
}

async function loadTrial() {
  document.getElementById('reveal').style.display = 'none';
  document.getElementById('next-btn').style.display = 'none';
  document.querySelectorAll('.vote-btn').forEach(b => { b.classList.remove('chosen', 'dimmed'); b.disabled = false; });

  const res = await fetch('/api/trial');
  if (!res.ok) { document.getElementById('summary').textContent = 'No eligible bookmarks.'; return; }
  current = await res.json();

  document.getElementById('screenshot').src = 'data:image/png;base64,' + current.screenshot;
  document.getElementById('url').textContent = current.url;
  document.getElementById('summary').textContent = current.summary;
  document.getElementById('progress').textContent =
    'Rated: ' + counts.html + ' html, ' + counts.screenshot + ' screenshot (' + (counts.html + counts.screenshot) + ' total)';
}

async function submitRating(rating) {
  if (!current) return;
  const btns = document.querySelectorAll('.vote-btn');
  btns.forEach(b => {
    b.disabled = true;
    if ((rating === 1 && b.classList.contains('pass')) || (rating === 0 && b.classList.contains('fail'))) {
      b.classList.add('chosen');
    } else {
      b.classList.add('dimmed');
    }
  });

  await fetch('/api/rate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({guid: current.guid, summary_type: current.summary_type, rating, content_length: current.content_length})
  });

  counts[current.summary_type]++;
  const rev = document.getElementById('reveal');
  rev.style.display = 'block';
  rev.className = 'reveal ' + current.summary_type;
  rev.textContent = 'Source: ' + (current.summary_type === 'html' ? 'HTML-based summary' : 'Screenshot-based summary');
  document.getElementById('next-btn').style.display = 'inline-block';
}

async function loadResults() {
  const res = await fetch('/api/results');
  const data = await res.json();
  const s = data.stats;
  let html = '';

  if (!data.sufficient_power) {
    const need = Math.max(30 - (s.html?.n || 0), 30 - (s.screenshot?.n || 0), 0);
    html += '<div class="warn">Need at least 30 ratings per type for statistical power. ~' + need + ' more ratings needed.</div>';
  }

  html += '<table><thead><tr><th>Type</th><th>N</th><th>Passes</th><th>Pass Rate</th><th>95% CI</th></tr></thead><tbody>';
  for (const type of ['html', 'screenshot']) {
    const d = s[type];
    const label = type === 'html' ? 'HTML-based' : 'Screenshot-based';
    if (d && d.n > 0) {
      html += '<tr><td>' + label + '</td><td>' + d.n + '</td><td>' + d.passes +
              '</td><td>' + (d.pass_rate * 100).toFixed(1) + '%</td><td>[' +
              (d.ci_low * 100).toFixed(1) + '%, ' + (d.ci_high * 100).toFixed(1) + '%]</td></tr>';
    } else {
      html += '<tr><td>' + label + '</td><td>0</td><td>-</td><td>-</td><td>-</td></tr>';
    }
  }
  html += '</tbody></table>';

  if (data.z_test) {
    const t = data.z_test;
    html += '<table><thead><tr><th>z-statistic</th><th>p-value</th></tr></thead><tbody>';
    html += '<tr><td>' + t.z_stat + '</td><td>' + t.p_value + '</td></tr></tbody></table>';
    const sig = t.p_value < 0.05;
    html += '<div class="sig ' + (sig ? 'yes' : 'no') + '">' +
            (sig ? 'Statistically significant difference (p < 0.05)' : 'No significant difference (p >= 0.05)') + '</div>';
  }

  // Content length breakdown
  if (data.length_breakdown && data.sufficient_power) {
    const lb = data.length_breakdown;
    const median = lb.median_length;
    html += '<h3 style="margin-top:2rem;margin-bottom:0.5rem;color:#f8fafc;font-size:1.1rem;">Pass Rate by Content Length</h3>';
    html += '<p style="color:#64748b;font-size:0.8rem;margin-bottom:0.5rem;">Median split at ' + median.toLocaleString() + ' chars</p>';
    html += '<table><thead><tr><th>Type</th><th>Content</th><th>N</th><th>Pass Rate</th><th>95% CI</th></tr></thead><tbody>';
    for (const stype of ['html', 'screenshot']) {
      const label = stype === 'html' ? 'HTML-based' : 'Screenshot-based';
      for (const bucket of ['short', 'long']) {
        const d = lb.cells[stype + '_' + bucket];
        if (d && d.n > 0) {
          html += '<tr><td>' + label + '</td><td>' + bucket + '</td><td>' + d.n +
                  '</td><td>' + (d.pass_rate * 100).toFixed(1) + '%</td><td>[' +
                  (d.ci_low * 100).toFixed(1) + '%, ' + (d.ci_high * 100).toFixed(1) + '%]</td></tr>';
        } else {
          html += '<tr><td>' + label + '</td><td>' + bucket + '</td><td>0</td><td>-</td><td>-</td></tr>';
        }
      }
    }
    html += '</tbody></table>';
  }

  // Update counts from server
  counts.html = s.html?.n || 0;
  counts.screenshot = s.screenshot?.n || 0;

  document.getElementById('results-section').innerHTML = html;
}

// Init
loadTrial();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True, port=5000)
