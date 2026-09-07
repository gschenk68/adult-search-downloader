#!/usr/bin/env python3
"""
Adult Site Search & Download Service
Searches adult sites by keyword and downloads videos via gallery-dl/yt-dlp
"""
import os
import json
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from curl_cffi import requests

app = Flask(__name__)

# Configuration
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/downloads")
DB_PATH = os.getenv("DB_PATH", "/config/searches.db")
GALLERY_DL_ARCHIVE = os.getenv("GALLERY_DL_ARCHIVE", "/config/archive.sqlite3")

# Supported sites with search patterns
SEARCH_SITES = {
    "spankbang": {
        "name": "SpankBang",
        "search_url": "https://spankbang.com/s/{query}/",
        "enabled": True,
        "needs_impersonate": True
    },
    # Florida IP blocks these:
    # "pornhub": {"name": "PornHub", "search_url": "https://www.pornhub.com/video/search?search={query}", "enabled": False},
    # "xvideos": {"name": "XVideos", "search_url": "https://www.xvideos.com/?k={query}", "enabled": False},
    # "xhamster": {"name": "XHamster", "search_url": "https://xhamster.com/search/{query}", "enabled": False},
}

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS searches
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  query TEXT NOT NULL,
                  site TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  status TEXT DEFAULT 'pending',
                  results_count INTEGER DEFAULT 0,
                  downloaded_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS downloads
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  search_id INTEGER,
                  url TEXT NOT NULL UNIQUE,
                  title TEXT,
                  status TEXT DEFAULT 'pending',
                  downloaded_at TIMESTAMP,
                  error TEXT,
                  FOREIGN KEY (search_id) REFERENCES searches(id))''')
    conn.commit()
    conn.close()

init_db()

def search_spankbang(query, limit=10):
    """Search SpankBang and return video URLs"""
    try:
        url = f"https://spankbang.com/s/{query.replace(' ', '+')}/trending/"
        r = requests.get(url, impersonate="chrome", timeout=30)
        
        # Extract video IDs and slugs
        import re
        matches = re.findall(r"/([a-z0-9]{4,8})/video/([a-z0-9_+-]+)", r.text)
        
        videos = []
        seen = set()
        for vid_id, slug in matches:
            full_url = f"https://spankbang.com/{vid_id}/video/{slug}"
            if full_url not in seen:
                seen.add(full_url)
                videos.append({
                    "url": full_url,
                    "title": slug.replace("-", " ").replace("_", " ").title()
                })
                if len(videos) >= limit:
                    break
        
        return videos
    except Exception as e:
        print(f"SpankBang search error: {e}")
        return []

def download_video(url, site):
    """Download video using yt-dlp with proper settings"""
    try:
        output_template = f"{DOWNLOAD_DIR}/{site}/%(title)s [%(id)s].%(ext)s"
        
        cmd = [
            "yt-dlp",
            "--impersonate", "chrome",
            "-f", "bv+ba/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--no-playlist",
            "--write-info-json",
            url
        ]
        
        # Use archive if available
        if os.path.exists(GALLERY_DL_ARCHIVE):
            cmd.extend(["--download-archive", GALLERY_DL_ARCHIVE])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            return {"success": True, "message": "Downloaded successfully"}
        else:
            return {"success": False, "error": result.stderr}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Download timeout (10 minutes)"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Web UI HTML
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Adult Site Search Downloader</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #1a1a1a; color: #fff; }
        h1 { color: #ff6b6b; }
        .search-box { margin: 20px 0; padding: 20px; background: #2a2a2a; border-radius: 8px; }
        input, select, button { padding: 10px; margin: 5px; font-size: 16px; }
        input[type="text"] { width: 400px; }
        button { background: #ff6b6b; color: white; border: none; cursor: pointer; border-radius: 4px; }
        button:hover { background: #ff5252; }
        .results { margin: 20px 0; }
        .video-card { background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .video-title { flex-grow: 1; }
        .video-url { color: #888; font-size: 12px; }
        .status { padding: 5px 10px; border-radius: 4px; font-size: 12px; }
        .status.pending { background: #666; }
        .status.downloading { background: #ffa500; }
        .status.completed { background: #4caf50; }
        .status.failed { background: #f44336; }
        .history { margin-top: 40px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; }
        a { color: #ff6b6b; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>🔍 Adult Site Search Downloader</h1>
    
    <div class="search-box">
        <h2>Search & Download</h2>
        <form id="searchForm">
            <input type="text" id="query" placeholder="Enter search keywords..." required>
            <select id="site">
                {% for site_id, site_info in sites.items() %}
                {% if site_info.enabled %}
                <option value="{{ site_id }}">{{ site_info.name }}</option>
                {% endif %}
                {% endfor %}
            </select>
            <input type="number" id="limit" value="10" min="1" max="50" style="width:60px;">
            <button type="submit">Search</button>
        </form>
    </div>
    
    <div class="results" id="results"></div>
    
    <div class="history">
        <h2>Recent Searches</h2>
        <div id="historyList">Loading...</div>
    </div>
    
    <script>
        async function search(e) {
            e.preventDefault();
            const query = document.getElementById('query').value;
            const site = document.getElementById('site').value;
            const limit = document.getElementById('limit').value;
            
            document.getElementById('results').innerHTML = '<p>Searching...</p>';
            
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query, site, limit: parseInt(limit)})
            });
            
            const data = await response.json();
            displayResults(data);
            loadHistory();
        }
        
        function displayResults(data) {
            if (!data.results || data.results.length === 0) {
                document.getElementById('results').innerHTML = '<p>No results found.</p>';
                return;
            }
            
            let html = '<h2>Search Results</h2>';
            html += `<p>Found ${data.results.length} videos. <button onclick="downloadAll(${data.search_id})">Download All</button></p>`;
            
            data.results.forEach(video => {
                html += `
                    <div class="video-card">
                        <div class="video-title">
                            <strong>${video.title}</strong><br>
                            <span class="video-url">${video.url}</span>
                        </div>
                        <button onclick="downloadOne('${video.url}', '${data.site}')">Download</button>
                    </div>
                `;
            });
            
            document.getElementById('results').innerHTML = html;
        }
        
        async function downloadOne(url, site) {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url, site})
            });
            
            const data = await response.json();
            alert(data.message || data.error);
        }
        
        async function downloadAll(searchId) {
            const response = await fetch(`/api/download-all/${searchId}`, {method: 'POST'});
            const data = await response.json();
            alert(data.message);
        }
        
        async function loadHistory() {
            const response = await fetch('/api/history');
            const data = await response.json();
            
            if (!data.searches || data.searches.length === 0) {
                document.getElementById('historyList').innerHTML = '<p>No search history.</p>';
                return;
            }
            
            let html = '<table><tr><th>Date</th><th>Query</th><th>Site</th><th>Results</th><th>Downloaded</th><th>Status</th></tr>';
            
            data.searches.forEach(search => {
                html += `
                    <tr>
                        <td>${new Date(search.created_at).toLocaleString()}</td>
                        <td><strong>${search.query}</strong></td>
                        <td>${search.site}</td>
                        <td>${search.results_count}</td>
                        <td>${search.downloaded_count}</td>
                        <td><span class="status ${search.status}">${search.status}</span></td>
                    </tr>
                `;
            });
            
            html += '</table>';
            document.getElementById('historyList').innerHTML = html;
        }
        
        document.getElementById('searchForm').addEventListener('submit', search);
        loadHistory();
        
        // Auto-refresh history every 30 seconds
        setInterval(loadHistory, 30000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, sites=SEARCH_SITES)

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    query = data.get('query', '').strip()
    site = data.get('site', 'spankbang')
    limit = data.get('limit', 10)
    
    if not query:
        return jsonify({"error": "Query required"}), 400
    
    # Store search in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO searches (query, site, status) VALUES (?, ?, ?)",
              (query, site, 'searching'))
    search_id = c.lastrowid
    conn.commit()
    
    # Perform search
    if site == "spankbang":
        results = search_spankbang(query, limit)
    else:
        results = []
    
    # Update search with results
    c.execute("UPDATE searches SET status=?, results_count=? WHERE id=?",
              ('completed', len(results), search_id))
    
    # Store result URLs
    for video in results:
        c.execute("INSERT OR IGNORE INTO downloads (search_id, url, title) VALUES (?, ?, ?)",
                  (search_id, video['url'], video['title']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "success": True,
        "search_id": search_id,
        "site": site,
        "query": query,
        "results": results
    })

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.json
    url = data.get('url')
    site = data.get('site', 'unknown')
    
    if not url:
        return jsonify({"error": "URL required"}), 400
    
    # Update status
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE downloads SET status='downloading' WHERE url=?", (url,))
    conn.commit()
    conn.close()
    
    # Download
    result = download_video(url, site)
    
    # Update final status
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if result['success']:
        c.execute("UPDATE downloads SET status='completed', downloaded_at=? WHERE url=?",
                  (datetime.now(), url))
        c.execute("""UPDATE searches SET downloaded_count = downloaded_count + 1 
                     WHERE id IN (SELECT search_id FROM downloads WHERE url=?)""", (url,))
    else:
        c.execute("UPDATE downloads SET status='failed', error=? WHERE url=?",
                  (result.get('error', 'Unknown error'), url))
    conn.commit()
    conn.close()
    
    return jsonify(result)

@app.route('/api/download-all/<int:search_id>', methods=['POST'])
def api_download_all(search_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT url FROM downloads WHERE search_id=? AND status='pending'", (search_id,))
    urls = [row[0] for row in c.fetchall()]
    
    c.execute("SELECT site FROM searches WHERE id=?", (search_id,))
    site = c.fetchone()[0]
    conn.close()
    
    if not urls:
        return jsonify({"message": "No pending downloads for this search"})
    
    # Queue downloads (in production, use background task queue)
    for url in urls:
        # For now, just mark as queued
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE downloads SET status='queued' WHERE url=?", (url,))
        conn.commit()
        conn.close()
    
    return jsonify({"message": f"Queued {len(urls)} downloads. Check back soon."})

@app.route('/api/history')
def api_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM searches ORDER BY created_at DESC LIMIT 50")
    searches = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify({"searches": searches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
