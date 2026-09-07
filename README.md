# Adult Search Downloader

Web-based search and download service for adult sites with gallery-dl/yt-dlp integration.

## Features

- 🔍 **Keyword Search**: Search adult sites (SpankBang, etc.) by description/keywords
- 📥 **Automated Downloads**: One-click or bulk download of search results
- 📊 **Search History**: Track all searches and download status
- 🗄️ **Deduplication**: Shared archive database prevents re-downloading
- 🎯 **Stash Integration**: Downloads go directly to media directory visible to Stash

## Supported Sites

- ✅ **SpankBang** - Full search and download support
- ❌ **PornHub, XVideos, XHamster** - Blocked by Florida age verification laws from ss4 IP

## Installation

### Deployrr-Compatible Deployment

1. Copy service compose file:
```bash
cp docker-compose.yml ~/docker/compose/schenkserver4/adult-search-downloader.yml
```

2. Add to master compose includes (before SERVICE-PLACEHOLDER):
```bash
cd ~/docker
# Edit docker-compose-schenkserver4.yml and add to includes:
#   - compose/schenkserver4/adult-search-downloader.yml
```

3. Add port to .env:
```bash
echo "ADULT_SEARCH_PORT=5555" >> .env
```

4. Build and deploy:
```bash
docker compose -f docker-compose-schenkserver4.yml build adult-search-downloader
docker compose -f docker-compose-schenkserver4.yml --profile adult up -d
```

5. Create Traefik rule:
```yaml
# ~/docker/appdata/traefik3/rules/schenkserver4/app-adult-search.yml
http:
  routers:
    adult-search-rtr:
      entryPoints:
        - websecure-external
        - websecure-internal
      rule: "Host(`adult-search.gjsandstar.com`)"
      service: adult-search-svc
      middlewares:
        - chain-authelia
      tls:
        certResolver: dns-cloudflare
        
  services:
    adult-search-svc:
      loadBalancer:
        servers:
          - url: "http://172.17.0.1:5555"
```

6. Access at: https://adult-search.gjsandstar.com

## Usage

### Web UI
1. Open the web interface
2. Enter search keywords (e.g., "outdoor amateur", "college party")
3. Select site (SpankBang recommended)
4. Click "Search"
5. Review results and click "Download" on individual videos or "Download All"

### API Endpoints

**Search:**
```bash
curl -X POST http://localhost:5555/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "keyword here", "site": "spankbang", "limit": 10}'
```

**Download Single:**
```bash
curl -X POST http://localhost:5555/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://spankbang.com/xxxxx/video/title", "site": "spankbang"}'
```

**Download All from Search:**
```bash
curl -X POST http://localhost:5555/api/download-all/1
```

**View History:**
```bash
curl http://localhost:5555/api/history
```

## Configuration

Environment variables:
- `DOWNLOAD_DIR`: Download destination (default: `/downloads`, maps to `MEDIADIR3/gallery-dl`)
- `DB_PATH`: SQLite database for search history (default: `/config/searches.db`)
- `GALLERY_DL_ARCHIVE`: Shared archive for deduplication (default: `/config/archive.sqlite3`)

## Integration with Stash

Downloads go to `${MEDIADIR3}/gallery-dl/<site>/` which is visible to Stash at `/data/gallery-dl/`.

Trigger Stash scan after downloads:
```bash
# Get API key from Stash container
APIKEY=$(docker exec stash grep -m1 "^api_key" /root/.stash/config.yml | cut -d" " -f2)

# Trigger scan
curl -s http://localhost:9999/graphql \
  -H "ApiKey: $APIKEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { metadataScan(input: { paths: [\"/data/gallery-dl\"] }) }"}'
```

## Limitations

- **Florida IP Block**: ss4's Florida IP (47.195.x.x) is blocked by Aylo sites (PornHub, XVideos, XHamster) due to age verification laws
- **SpankBang Only**: Currently only SpankBang search is fully implemented
- **No Background Queue**: Downloads run synchronously (future: add Celery/RQ)

## Architecture

```
User → Web UI (Flask) → Search Site (curl-cffi) → Parse Results
                      ↓
                Download (yt-dlp + impersonate) → MEDIADIR3/gallery-dl/
                      ↓
                Track in SQLite → History/Status
```

## Troubleshooting

**Exit code 32**: NoExtractorError - URL is an aggregator/search page, not a direct video URL

**403 Forbidden**: Site requires browser impersonation - curl-cffi with `impersonate="chrome"` is enabled

**Empty results**: Try different keywords or check if site is accessible from ss4 IP

## Future Enhancements

- [ ] Add more sites (when accessible)
- [ ] Background task queue (Celery/Redis)
- [ ] Scheduled searches (cron-like)
- [ ] Stash API integration (auto-tag downloaded scenes)
- [ ] Quality/format preferences
- [ ] Batch import from text file
