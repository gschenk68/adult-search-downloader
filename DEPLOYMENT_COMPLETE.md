# 🎉 Adult Search Downloader - Deployment Complete!

## ✅ What Was Set Up

I've successfully deployed a **keyword-based adult site search and download service** on ss4 following your Deployrr workflow.

### Deployed Components:

1. **Flask Web Application** (`searcher.py`)
   - Search adult sites by keywords/description
   - Interactive web UI for browsing results
   - One-click or bulk downloads
   - SQLite database for tracking searches and downloads

2. **Docker Container** (`adult-search-downloader:latest`)
   - Python 3.11 with Flask, curl-cffi, yt-dlp
   - FFmpeg for video processing
   - Browser impersonation for Cloudflare bypass

3. **Deployrr Integration**
   - Compose file: `~/docker/compose/schenkserver4/adult-search-downloader.yml`
   - Included in master compose with `--profile adult`
   - Port 5555 (ADULT_SEARCH_PORT in .env)
   - Connected to docker_default network

4. **Traefik Routing**
   - Rule: `~/docker/appdata/traefik3/rules/schenkserver4/app-adult-search.yml`
   - URL: https://adult-search.gjsandstar.com
   - Protected by Authelia 2FA
   - SSL via Cloudflare DNS challenge

5. **Stash Integration**
   - Downloads go to: `${MEDIADIR3}/gallery-dl/` = `/home/gschenk68/mnt/media/videos/gallery-dl/`
   - Visible to Stash at: `/data/gallery-dl/`
   - Shared archive DB prevents re-downloading

---

## 🚀 How to Use

### Web Interface

1. **Access**: https://adult-search.gjsandstar.com
2. **Login**: Use Authelia (push notification preferred)
3. **Search**:
   - Enter keywords (e.g., "outdoor amateur", "college party", "milf blonde")
   - Select site: **SpankBang** (only working site from Florida IP)
   - Set limit: 1-50 results
   - Click **Search**

4. **Download**:
   - Review video cards with titles and URLs
   - Click **Download** on individual videos
   - Or click **Download All** to queue entire search

5. **Monitor**:
   - Check **Recent Searches** table for status
   - Downloads save to `gallery-dl/spankbang/` automatically

### API Usage

```bash
# Search
curl -X POST https://adult-search.gjsandstar.com/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "keyword here", "site": "spankbang", "limit": 10}'

# Download single video
curl -X POST https://adult-search.gjsandstar.com/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://spankbang.com/xxxxx/video/title", "site": "spankbang"}'

# Download all from search ID
curl -X POST https://adult-search.gjsandstar.com/api/download-all/1

# View history
curl https://adult-search.gjsandstar.com/api/history
```

---

## 📁 File Locations

```
ss4 Structure:
├── ~/docker/compose/schenkserver4/
│   ├── adult-search-downloader.yml         # Service definition
│   └── build-contexts/
│       └── adult-search-downloader/
│           ├── searcher.py                  # Python app
│           └── Dockerfile                   # Container build
├── ~/docker/appdata/
│   ├── adult-search-downloader/            # Config & database
│   │   ├── searches.db                     # SQLite tracking DB
│   │   └── archive.sqlite3                 # Shared dedup archive
│   └── traefik3/rules/schenkserver4/
│       └── app-adult-search.yml            # Traefik routing
└── ~/mnt/media/videos/gallery-dl/          # Downloads (MEDIADIR3)
    └── spankbang/                          # Site-organized folders
        └── [Video Title] [ID].mp4

Master Compose:
- ~/docker/docker-compose-schenkserver4.yml includes adult-search-downloader.yml
- ~/docker/.env contains ADULT_SEARCH_PORT=5555
```

---

## ⚠️ Important Notes

### Site Compatibility

**✅ WORKS:**
- **SpankBang** - Full search and download support with browser impersonation

**❌ BLOCKED (Florida IP age verification):**
- PornHub - State law blocks access
- XVideos - "No video formats found" error
- XHamster - KeyError videoModel
- Eporner - "Unable to extract hash"

These sites are blocked at the ISP level due to Florida's age verification laws. **You would need VPN egress** (like your existing Mullvad setup) to bypass.

### Technical Details

- **Impersonation**: curl-cffi with `impersonate="chrome"` bypasses Cloudflare
- **Deduplication**: Shared `archive.sqlite3` prevents re-downloading same videos
- **Format**: Videos download as MP4 with best quality (bv+ba/best)
- **Timeout**: 10 minutes per video download
- **Metadata**: Saves .info.json files alongside videos

---

## 🔧 Management Commands

```bash
# SSH to ss4
ssh gschenk68@192.168.10.162

# View logs
cd ~/docker
docker compose -f docker-compose-schenkserver4.yml logs -f adult-search-downloader

# Restart service
docker compose -f docker-compose-schenkserver4.yml restart adult-search-downloader

# Stop service
docker compose -f docker-compose-schenkserver4.yml --profile adult down

# Rebuild after code changes
docker compose -f docker-compose-schenkserver4.yml build adult-search-downloader
docker compose -f docker-compose-schenkserver4.yml --profile adult up -d
```

### Trigger Stash Scan After Downloads

```bash
# Get Stash API key
APIKEY=$(docker exec stash grep -m1 "^api_key" /root/.stash/config.yml | cut -d" " -f2)

# Trigger scan of download directory
curl -s http://localhost:9999/graphql \
  -H "ApiKey: $APIKEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { metadataScan(input: { paths: [\"/data/gallery-dl\"] }) }"}'
```

---

## 🎯 Next Steps (Optional Enhancements)

1. **Add More Sites** (when accessible via VPN):
   - Modify `SEARCH_SITES` dict in `searcher.py`
   - Add search patterns and parsers

2. **Background Task Queue**:
   - Integrate Celery + Redis for async downloads
   - Prevents web UI timeout on large batches

3. **Scheduled Searches**:
   - Cron job to auto-search saved keywords
   - Email/Telegram notifications for new content

4. **Auto-Stash Tagging**:
   - GraphQL mutation to tag downloaded scenes
   - Auto-add to "gallery-dl-imported" tag

5. **Quality Preferences**:
   - UI dropdown for resolution (480p/720p/1080p/4K)
   - Format preference (MP4/MKV/WEBM)

---

## 📊 Example Workflow

1. Open https://adult-search.gjsandstar.com
2. Search: "amateur outdoor threesome" → SpankBang → Limit 10
3. Review 10 results
4. Click "Download All" or select individual videos
5. Videos save to `~/mnt/media/videos/gallery-dl/spankbang/`
6. Trigger Stash scan (manual or automated)
7. Videos appear in Stash for tagging/organizing
8. Check History tab to monitor download status

---

## 🐛 Troubleshooting

**"NoExtractorError / Exit code 32"**
- URL is a search page or aggregator, not a direct video link
- Always ensure URLs are direct video pages (e.g., `/video/` in path)

**"403 Forbidden" or "Unable to extract"**
- Site may be blocked by Florida age verification law
- Try with VPN egress or different site

**"Download timeout"**
- Video file is very large or slow server
- Increase timeout in `download_video()` function

**Stash doesn't see new files**
- Check mount: `docker exec stash ls /data/gallery-dl`
- Trigger manual scan via GraphQL
- Wait ~5min for auto-scan interval

---

## 📝 Summary

You now have a **fully functional adult site search and download service** that:
- ✅ Searches by keywords/descriptions
- ✅ Downloads videos automatically
- ✅ Integrates with your existing Stash library
- ✅ Follows Deployrr conventions
- ✅ Protected by Authelia 2FA
- ✅ Accessible at https://adult-search.gjsandstar.com

**Status**: 🟢 **DEPLOYED & RUNNING**

Container: `adult-search-downloader` on port 5555  
Profile: `adult`, `media`, `all`  
Network: `docker_default`  
Downloads: `/home/gschenk68/mnt/media/videos/gallery-dl/`
