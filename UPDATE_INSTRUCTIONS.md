# Fix Deployment: Directory Creation Bug

## Issue
Downloads were failing with error:
```
ERROR: Unable to rename file: [Errno 2] No such file or directory: 
'/downloads/spankbang/a55m7 [a55m7].mp4.part-Frag12.part' -> 
'/downloads/spankbang/a55m7 [a55m7].mp4.part-Frag12'
```

**Root Cause**: The `download_video()` function didn't create the site-specific subdirectory (`/downloads/spankbang/`) before attempting downloads.

## Fix Applied
Added directory creation in `searcher.py` line 93-95:
```python
# Ensure site-specific directory exists
site_dir = os.path.join(DOWNLOAD_DIR, site)
os.makedirs(site_dir, exist_ok=True)
```

---

## Deploy Updated Container

### Option 1: Pull from GitHub (Recommended)
```bash
# SSH to ss4
ssh -p 1237 gschenk68@192.168.10.162

# Navigate to build context
cd ~/docker/compose/schenkserver4/build-contexts/adult-search-downloader/

# Pull latest changes
git pull origin master

# Rebuild and restart container
cd ~/docker
sudo docker compose -f docker-compose-schenkserver4.yml up adult-search-downloader --build -d

# Verify fix
docker logs adult-search-downloader --tail 20
```

### Option 2: Manual File Update
```bash
# SSH to ss4
ssh -p 1237 gschenk68@192.168.10.162

# Edit searcher.py
nano ~/docker/compose/schenkserver4/build-contexts/adult-search-downloader/searcher.py

# Add these lines after line 92 (inside download_video function):
        # Ensure site-specific directory exists
        site_dir = os.path.join(DOWNLOAD_DIR, site)
        os.makedirs(site_dir, exist_ok=True)

# Save and rebuild
cd ~/docker
sudo docker compose -f docker-compose-schenkserver4.yml up adult-search-downloader --build -d
```

---

## Verification Steps

1. **Check container is running**:
   ```bash
   docker ps | grep adult-search
   ```

2. **Test a download**:
   - Open https://adult-search.gjsandstar.com
   - Search for any term (e.g., "verified amateur")
   - Click **Download** on any result
   - Should succeed without directory errors

3. **Check downloads directory**:
   ```bash
   docker exec adult-search-downloader ls -la /downloads/
   docker exec adult-search-downloader ls -la /downloads/spankbang/
   ```

4. **Verify on host**:
   ```bash
   ls -la /stash-data/adult-videos/
   ls -la /stash-data/adult-videos/spankbang/
   ```

---

## Git Commit & Push

```bash
# From local workspace
cd /data/workspace/adult-search-downloader

# Stage changes
git add searcher.py

# Commit
git commit -m "fix: create site subdirectory before download

Fixes directory creation issue that caused yt-dlp downloads to fail
with 'No such file or directory' error when renaming temp files.

Added os.makedirs() call to ensure /downloads/{site}/ exists before
yt-dlp attempts to save files there."

# Push to GitHub
git push origin master
```

---

## Related Files
- **Source**: `searcher.py` (line 90-96)
- **Container**: `/app/searcher.py` inside `adult-search-downloader`
- **Build Context**: `~/docker/compose/schenkserver4/build-contexts/adult-search-downloader/`
- **Compose File**: `~/docker/compose/schenkserver4/services/adult-search-downloader.yml`

---

**Status**: ⚠️ Fix ready to deploy  
**Deployment Time**: ~2-3 minutes (rebuild + restart)  
**Downtime**: ~30 seconds during restart
