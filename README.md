# Adult Site Search & Downloader

Multi-site adult video search and download tool with real-time progress tracking.

## 🚀 Features

- **Multi-Site Search**: Search across 6+ adult sites simultaneously
- **Real-Time Progress**: Live download progress with percentage and speed
- **VPN Ready**: Designed to run through Tailscale/Mullvad VPN
- **Smart Deduplication**: Archive tracking to avoid re-downloads
- **Modern UI**: Dark-themed responsive web interface
- **Download Queue**: Track multiple downloads with status monitoring

## 🌐 Supported Sites

✅ **Currently Enabled** (6 sites):
- SpankBang
- XNXX
- EPorner
- TXXX
- HClips
- Upornia

❌ **Geo-Blocked** (Florida/Aylo sites):
- PornHub
- XVideos
- XHamster
- Brazzers
- Reality Kings

## 📦 Quick Start

### Option 1: Standalone (No VPN)

```bash
cd adult-search-downloader
docker compose -f docker-compose-standalone.yml up -d
```

Access at: http://localhost:5556

### Option 2: Through VPN (Recommended)

**Requirements:**
- qBittorrent VPN container running (qbt-vpn)
- Tailscale → Mullvad setup

```bash
# Deploy to ss4 with VPN routing
cd adult-search-downloader
./deploy.sh
```

Access at: http://172.17.0.1:5556 (or through qbt-vpn's network)

### Option 3: Traefik + Authelia

1. Copy Traefik route:
```bash
scp app-adult-search.yml gschenk68@192.168.10.162:~/docker/appdata/traefik3/rules/schenkserver4/
```

2. Update the route to match your qbt-vpn setup

3. Access at: https://adult-search.gjsandstar.com

## 🎯 Usage

1. **Search**: Enter keywords, select site (or "All Sites"), set result limit
2. **Download**: Click "Download" on any video - progress shows in real-time
3. **Monitor**: Active Downloads section shows all in-progress downloads
4. **History**: Recent searches tracked with success rates

## 📊 Progress Tracking

The UI now shows:
- **Real-time percentage** (0-100%)
- **Download speed** and ETA
- **Visual progress bars** for each download
- **Active downloads panel** with all concurrent downloads
- **Auto-refresh** every 5 seconds

No more "click and wonder" - you'll see exactly what's happening!

## 🔧 Configuration

### Environment Variables

- `DOWNLOAD_DIR`: Where videos are saved (default: `/downloads`)
- `DB_PATH`: SQLite database location (default: `/config/searches.db`)
- `GALLERY_DL_ARCHIVE`: Deduplication archive (default: `/config/archive.sqlite3`)

### Volume Mounts

- `/config`: Database and settings
- `/downloads`: Video downloads organized by site

### Network Modes

**VPN Mode** (recommended for privacy):
```yaml
network_mode: "container:qbt-vpn"
```

**Bridge Mode** (direct internet):
```yaml
ports:
  - "5556:5000"
```

## 🏗️ Architecture

```
User → Traefik → adult-search-downloader → Tailscale → Mullvad VPN → Adult Sites
                        ↓
                   qbt-vpn netns
```

- **Flask** web server with SSE for progress
- **yt-dlp** for downloads with `--impersonate chrome`
- **curl-cffi** for CF-protected sites
- **SQLite** for search/download history
- **Threading** for background downloads

## 📝 API Endpoints

- `POST /api/search` - Search sites
- `POST /api/download` - Start download
- `GET /api/progress/<id>` - Get download progress
- `GET /api/active-downloads` - List active downloads
- `GET /api/history` - Search history

## 🔒 Security Notes

- Use Authelia for authentication
- Run through VPN for privacy
- Geo-blocking bypass via VPN
- No logs of search queries (local only)

## 🐛 Troubleshooting

### Downloads stuck at 0%
- Check VPN connection: `docker logs qbt-vpn`
- Test site access: `curl --impersonate chrome https://spankbang.com`

### "Container not found" error
- Ensure qbt-vpn is running: `docker ps | grep qbt-vpn`
- Use standalone mode if VPN not available

### Site search returns empty
- Some sites may change their HTML structure
- Check logs: `docker logs adult-search-downloader`
- Site may be temporarily down

## 📜 License

MIT License - See LICENSE file

## 🤝 Contributing

Pull requests welcome! Please test with:
```bash
# Build and test locally
docker build -t adult-search-test .
docker run -p 5556:5000 adult-search-test
```

## 🎉 Recent Updates

**v2.0** - Real-Time Progress Tracking
- ✨ Live download progress with percentages
- ✨ Active downloads monitoring panel
- ✨ Multi-site "All Sites" search option
- ✨ 5 new adult sites added
- ✨ Better error handling and status updates
- ✨ VPN network mode support

**v1.0** - Initial Release
- Basic search and download
- SpankBang support only
- Simple progress tracking
