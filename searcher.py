#!/usr/bin/env python3
"""
Adult Site Search & Download Service
Searches adult sites by keyword and downloads videos via gallery-dl/yt-dlp
"""
import os
import json
import subprocess
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, Response
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
        "search_url": "https://spankbang.com/s/{query}/trending/",
        "enabled": True,
        "needs_impersonate": True,
        "url_pattern": r"/([a-z0-9]{4,8})/video/([a-z0-9_+-]+)"
    },
    "xnxx": {
        "name": "XNXX",
        "search_url": "https://www.xnxx.com/?k={query}",
        "enabled": True,
        "needs_impersonate": False,
        "url_pattern": r'video-([a-z0-9]+)/([^"]+)'
    },
    "eporner": {
        "name": "EPorner",
        "search_url": "https://www.eporner.com/search/{query}/",
        "enabled": True,
        "needs_impersonate": False,
        "url_pattern": r'href="(/video-[^"]+)"'
    },
    "txxx": {
        "name": "TXXX",
        "search_url": "https://txxx.com/search/{query}/",
        "enabled": True,
        "needs_impersonate": False,
        "url_pattern": r'href="(/videos/[0-9]+-[^"]+)"'
    },
    "hclips": {
        "name": "HClips",
        "search_url": "https://hclips.com/search/{query}/",
        "enabled": True,
        "needs_impersonate": False,
        "url_pattern": r'href="(/videos/[0-9]+-[^"]+)"'
    },
    "upornia": {
        "name": "Upornia",
        "search_url": "https://www.upornia.com/search/?q={query}",
        "enabled": True,
        "needs_impersonate": False,
        "url_pattern": r'href="(/video/[^"]+)"'
    },
    # Florida IP blocks these (Aylo sites):
    # "pornhub": {"name": "PornHub", "search_url": "https://www.pornhub.com/video/search?search={query}", "enabled": False},
    # "brazzers": {"name": "Brazzers", "search_url": "https://www.brazzers.com/search?query={query}", "enabled": False},
    # "reality_kings": {"name": "Reality Kings", "search_url": "https://www.realitykings.com/search?query={query}", "enabled": False},
}

# Active downloads tracking
active_downloads = {}
download_lock = threading.Lock()

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
                  progress INTEGER DEFAULT 0,
                  downloaded_at TIMESTAMP,
                  error TEXT,
                  FOREIGN KEY (search_id) REFERENCES searches(id))''')
    conn.commit()
    conn.close()

init_db()

def search_site(site_id, query, limit=10):
    """Generic search function for adult sites"""
    try:
        site_info = SEARCH_SITES[site_id]
        url = site_info["search_url"].format(query=query.replace(' ', '+'))
        
        if site_info["needs_impersonate"]:
            r = requests.get(url, impersonate="chrome", timeout=30)
        else:
            r = requests.get(url, timeout=30)
        
        # Extract video URLs based on pattern
        import re
        pattern = site_info["url_pattern"]
        matches = re.findall(pattern, r.text)
        
        videos = []
        seen = set()
        
        for match in matches:
            if site_id == "spankbang":
                vid_id, slug = match
                full_url = f"https://spankbang.com/{vid_id}/video/{slug}"
                title = slug.replace("-", " ").replace("_", " ").title()
            elif site_id == "xnxx":
                vid_id, slug = match
                full_url = f"https://www.xnxx.com/video-{vid_id}/{slug}"
                title = slug.replace("-", " ").replace("_", " ").title()
            elif site_id == "eporner":
                path = match
                full_url = f"https://www.eporner.com{path}"
                title = path.split('/')[-1].replace("-", " ").title()
            elif site_id in ["txxx", "hclips"]:
                path = match
                full_url = f"https://{site_id}.com{path}"
                title = path.split('/')[-1].replace("-", " ").title()
            elif site_id == "upornia":
                path = match
                full_url = f"https://www.upornia.com{path}"
                title = path.split('/')[-1].replace("-", " ").title()
            else:
                continue
            
            if full_url not in seen:
                seen.add(full_url)
                videos.append({
                    "url": full_url,
                    "title": title[:100]  # Limit title length
                })
                if len(videos) >= limit:
                    break
        
        return videos
    except Exception as e:
        print(f"{site_id} search error: {e}")
        return []

def download_video_with_progress(url, site, download_id):
    """Download video using yt-dlp with progress tracking"""
    try:
        # Ensure site-specific directory exists
        site_dir = os.path.join(DOWNLOAD_DIR, site)
        os.makedirs(site_dir, exist_ok=True)
        
        output_template = f"{DOWNLOAD_DIR}/{site}/%(title)s [%(id)s].%(ext)s"
        
        cmd = [
            "yt-dlp",
            "--impersonate", "chrome",
            "-f", "bv+ba/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--no-playlist",
            "--write-info-json",
            "--newline",  # Progress on new lines for parsing
            url
        ]
        
        # Use archive if available
        if os.path.exists(GALLERY_DL_ARCHIVE):
            cmd.extend(["--download-archive", GALLERY_DL_ARCHIVE])
        
        # Start download process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Track progress
        with download_lock:
            active_downloads[download_id] = {
                "url": url,
                "site": site,
                "progress": 0,
                "status": "downloading",
                "message": "Starting download..."
            }
        
        # Parse output for progress
        for line in process.stdout:
            line = line.strip()
            if "[download]" in line and "%" in line:
                try:
                    # Extract percentage
                    percent_str = line.split("%")[0].split()[-1]
                    percent = float(percent_str)
                    
                    with download_lock:
                        if download_id in active_downloads:
                            active_downloads[download_id]["progress"] = int(percent)
                            active_downloads[download_id]["message"] = line
                    
                    # Update database
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("UPDATE downloads SET progress=? WHERE id=?", (int(percent), download_id))
                    conn.commit()
                    conn.close()
                except:
                    pass
            
            print(f"[{download_id}] {line}")
        
        process.wait()
        
        if process.returncode == 0:
            with download_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["progress"] = 100
                    active_downloads[download_id]["status"] = "completed"
                    active_downloads[download_id]["message"] = "Download complete"
            
            return {"success": True, "message": "Downloaded successfully"}
        else:
            with download_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["status"] = "failed"
                    active_downloads[download_id]["message"] = "Download failed"
            
            return {"success": False, "error": "Download failed"}
            
    except Exception as e:
        with download_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "failed"
                active_downloads[download_id]["message"] = str(e)
        
        return {"success": False, "error": str(e)}
    finally:
        # Clean up after 60 seconds
        threading.Timer(60, lambda: active_downloads.pop(download_id, None)).start()

# Web UI HTML with progress tracking
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Adult Site Search Downloader</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #1a1a1a; color: #fff; }
        h1 { color: #ff6b6b; }
        .search-box { margin: 20px 0; padding: 20px; background: #2a2a2a; border-radius: 8px; }
        input, select, button { padding: 10px; margin: 5px; font-size: 16px; }
        input[type="text"] { width: 400px; }
        button { background: #ff6b6b; color: white; border: none; cursor: pointer; border-radius: 4px; }
        button:hover { background: #ff5252; }
        button:disabled { background: #666; cursor: not-allowed; }
        .results { margin: 20px 0; }
        .video-card { background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .video-title { flex-grow: 1; }
        .video-url { color: #888; font-size: 12px; word-break: break-all; }
        .status { padding: 5px 10px; border-radius: 4px; font-size: 12px; }
        .status.pending { background: #666; }
        .status.downloading { background: #ffa500; }
        .status.completed { background: #4caf50; }
        .status.failed { background: #f44336; }
        .progress-bar { width: 100%; height: 20px; background: #444; border-radius: 4px; overflow: hidden; margin: 10px 0; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #4caf50, #8bc34a); transition: width 0.3s; text-align: center; line-height: 20px; font-size: 12px; }
        .download-status { margin-top: 10px; font-size: 12px; color: #aaa; }
        .active-downloads { margin: 20px 0; padding: 20px; background: #2a2a2a; border-radius: 8px; }
        .download-item { background: #333; padding: 10px; margin: 10px 0; border-radius: 4px; }
        .history { margin-top: 40px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; }
        a { color: #ff6b6b; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .site-count { color: #4caf50; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🔍 Adult Site Search Downloader</h1>
    <p>Supports <span class="site-count">{{ enabled_count }}</span> adult sites | Running through VPN 🔒</p>
    
    <div class="search-box">
        <h2>Search & Download</h2>
        <form id="searchForm">
            <input type="text" id="query" placeholder="Enter search keywords..." required>
            <select id="site">
                <option value="all">All Sites</option>
                {% for site_id, site_info in sites.items() %}
                {% if site_info.enabled %}
                <option value="{{ site_id }}">{{ site_info.name }}</option>
                {% endif %}
                {% endfor %}
            </select>
            <input type="number" id="limit" value="10" min="1" max="50" style="width:60px;" title="Results per site">
            <button type="submit">Search</button>
        </form>
    </div>
    
    <div class="active-downloads" id="activeDownloads" style="display:none;">
        <h2>Active Downloads</h2>
        <div id="activeDownloadsList"></div>
    </div>
    
    <div class="results" id="results"></div>
    
    <div class="history">
        <h2>Recent Searches</h2>
        <div id="historyList">Loading...</div>
    </div>
    
    <script>
        let downloadCheckInterval = null;
        
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
            html += `<p>Found ${data.results.length} videos from ${data.sites_searched || 1} site(s).</p>`;
            
            data.results.forEach(video => {
                const btnId = `btn-${video.url.replace(/[^a-z0-9]/gi, '')}`;
                html += `
                    <div class="video-card">
                        <div class="video-title">
                            <strong>${video.title}</strong><br>
                            <span class="video-url">${video.url}</span>
                            <div class="download-status" id="status-${btnId}"></div>
                        </div>
                        <button id="${btnId}" onclick="downloadOne('${encodeURIComponent(video.url)}', '${video.site || data.site}', '${btnId}')">Download</button>
                    </div>
                `;
            });
            
            document.getElementById('results').innerHTML = html;
        }
        
        async function downloadOne(encodedUrl, site, btnId) {
            const url = decodeURIComponent(encodedUrl);
            const button = document.getElementById(btnId);
            const statusDiv = document.getElementById(`status-${btnId}`);
            
            button.disabled = true;
            button.textContent = 'Starting...';
            statusDiv.innerHTML = '<div class="progress-bar"><div class="progress-fill" style="width:0%">0%</div></div>';
            
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url, site})
            });
            
            const data = await response.json();
            
            if (data.download_id) {
                // Start monitoring progress
                monitorDownload(data.download_id, btnId);
            } else {
                button.textContent = 'Failed';
                statusDiv.textContent = data.error || 'Download failed';
            }
        }
        
        function monitorDownload(downloadId, btnId) {
            const button = document.getElementById(btnId);
            const statusDiv = document.getElementById(`status-${btnId}`);
            
            const checkProgress = async () => {
                try {
                    const response = await fetch(`/api/progress/${downloadId}`);
                    const data = await response.json();
                    
                    if (data.status === 'downloading') {
                        const progress = data.progress || 0;
                        statusDiv.innerHTML = `
                            <div class="progress-bar">
                                <div class="progress-fill" style="width:${progress}%">${progress}%</div>
                            </div>
                            <div>${data.message || 'Downloading...'}</div>
                        `;
                        button.textContent = `${progress}%`;
                        
                        // Continue checking
                        setTimeout(checkProgress, 1000);
                    } else if (data.status === 'completed') {
                        statusDiv.innerHTML = '<span class="status completed">✓ Complete</span>';
                        button.textContent = 'Done';
                        button.disabled = false;
                    } else if (data.status === 'failed') {
                        statusDiv.innerHTML = `<span class="status failed">✗ Failed: ${data.message}</span>`;
                        button.textContent = 'Failed';
                        button.disabled = false;
                    }
                    
                    updateActiveDownloads();
                } catch (error) {
                    console.error('Progress check failed:', error);
                }
            };
            
            checkProgress();
        }
        
        async function updateActiveDownloads() {
            const response = await fetch('/api/active-downloads');
            const data = await response.json();
            
            if (data.downloads && data.downloads.length > 0) {
                document.getElementById('activeDownloads').style.display = 'block';
                
                let html = '';
                data.downloads.forEach(dl => {
                    html += `
                        <div class="download-item">
                            <strong>${dl.url}</strong><br>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width:${dl.progress}%">${dl.progress}%</div>
                            </div>
                            <div style="font-size:12px; color:#aaa;">${dl.message}</div>
                        </div>
                    `;
                });
                
                document.getElementById('activeDownloadsList').innerHTML = html;
            } else {
                document.getElementById('activeDownloads').style.display = 'none';
            }
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
        
        // Auto-refresh active downloads and history
        setInterval(() => {
            updateActiveDownloads();
            loadHistory();
        }, 5000);
        
        // Initial active downloads check
        updateActiveDownloads();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    enabled_count = sum(1 for s in SEARCH_SITES.values() if s["enabled"])
    return render_template_string(HTML_TEMPLATE, sites=SEARCH_SITES, enabled_count=enabled_count)

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    query = data.get('query', '').strip()
    site = data.get('site', 'all')
    limit = data.get('limit', 10)
    
    if not query:
        return jsonify({"error": "Query required"}), 400
    
    all_results = []
    sites_searched = []
    
    # Search all sites or specific site
    if site == "all":
        for site_id, site_info in SEARCH_SITES.items():
            if site_info["enabled"]:
                results = search_site(site_id, query, limit)
                for video in results:
                    video["site"] = site_id
                all_results.extend(results)
                if results:
                    sites_searched.append(site_id)
    else:
        if site in SEARCH_SITES and SEARCH_SITES[site]["enabled"]:
            all_results = search_site(site, query, limit)
            for video in all_results:
                video["site"] = site
            sites_searched.append(site)
    
    # Store search in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO searches (query, site, status, results_count) VALUES (?, ?, ?, ?)",
              (query, site, 'completed', len(all_results)))
    search_id = c.lastrowid
    
    # Store result URLs
    for video in all_results:
        c.execute("INSERT OR IGNORE INTO downloads (search_id, url, title) VALUES (?, ?, ?)",
                  (search_id, video['url'], video['title']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "success": True,
        "search_id": search_id,
        "site": site,
        "sites_searched": len(sites_searched),
        "query": query,
        "results": all_results
    })

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.json
    url = data.get('url')
    site = data.get('site', 'unknown')
    
    if not url:
        return jsonify({"error": "URL required"}), 400
    
    # Get or create download entry
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM downloads WHERE url=?", (url,))
    row = c.fetchone()
    
    if row:
        download_id = row[0]
    else:
        c.execute("INSERT INTO downloads (url, title, status) VALUES (?, ?, ?)",
                  (url, url.split('/')[-1], 'downloading'))
        download_id = c.lastrowid
    
    c.execute("UPDATE downloads SET status='downloading', progress=0 WHERE id=?", (download_id,))
    conn.commit()
    conn.close()
    
    # Start download in background thread
    thread = threading.Thread(
        target=download_worker,
        args=(url, site, download_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Download started",
        "download_id": download_id
    })

def download_worker(url, site, download_id):
    """Background worker for downloads"""
    result = download_video_with_progress(url, site, download_id)
    
    # Update final status in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if result['success']:
        c.execute("UPDATE downloads SET status='completed', progress=100, downloaded_at=? WHERE id=?",
                  (datetime.now(), download_id))
        c.execute("""UPDATE searches SET downloaded_count = downloaded_count + 1 
                     WHERE id IN (SELECT search_id FROM downloads WHERE id=?)""", (download_id,))
    else:
        c.execute("UPDATE downloads SET status='failed', error=? WHERE id=?",
                  (result.get('error', 'Unknown error'), download_id))
    conn.commit()
    conn.close()

@app.route('/api/progress/<int:download_id>')
def api_progress(download_id):
    """Get download progress"""
    with download_lock:
        if download_id in active_downloads:
            return jsonify(active_downloads[download_id])
    
    # Check database for final status
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status, progress, error FROM downloads WHERE id=?", (download_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        status, progress, error = row
        return jsonify({
            "status": status,
            "progress": progress or 0,
            "message": error or "Complete"
        })
    
    return jsonify({"status": "not_found"}), 404

@app.route('/api/active-downloads')
def api_active_downloads():
    """Get all active downloads"""
    with download_lock:
        downloads = list(active_downloads.values())
    return jsonify({"downloads": downloads})

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
