---
name: fetch-media
description: Scrape akun X/TikTok, count media, sort by likes, download, upload ke Mega, kirim ke user via Telegram
metadata:
  hermes:
    tags: [x, twitter, tiktok, media-download, mega, social-media, telegram-delivery]
    category: productivity
---

# Fetch Media

Scrape foto & video dari akun X/TikTok, download, upload ke Mega, kirim ke Telegram. Satu workflow dari cek → ambil → simpan → kirim.

## Platform Decision Table — read first

| Input URL | Platform | Count method | Download method | Local path | Upload path |
|-----------|----------|-------------|----------------|------------|-------------|
| `x.com/<handle>` / `twitter.com/<handle>` | **X/Twitter** | fxtwitter → `x_user_top_media.py` (GraphQL) | `x_user_top_media.py --type {photo,video} --count 0 --output-dir` | `~/Downloads/x/<handle>/` | `upload_mega.sh <handle>` (auto) |
| `tiktok.com/@<handle>` / `vt.tiktok.com/...` | **TikTok** | Camofox → JSON stats | `yt-dlp --batch-file` | `~/Downloads/tiktok/<handle>/` | **MUST MOVE** ke `~/Downloads/x/<handle>/videos/` dulu |
| `instagram.com/<handle>` | **Instagram** | via media-download skill | gallery-dl | `~/Downloads/instagram/<handle>/` | manual |

**Gunakan tabel ini untuk langsung tau langkah yang benar.** Jangan coba pake langkah X buat TikTok — script `x_count_media.py` dan `dl_media.py` CUMA buat X.

## When to Use
- User kasih link akun X → mau liat jumlah foto/video
- User kasih link akun TikTok → mau liat jumlah video
- User mau download semua media akun X atau TikTok
- User mau upload hasil download ke Mega
- User mau media dikirim langsung ke Telegram chat

## Prerequisites
- Cookies X.com: `~/.config/social-dl/cookies/x.com.txt`
- Mega credentials: `~/.megarc`
- Python venv Hermes: `~/.hermes/hermes-agent/venv/bin/python`

## How to Run

1. **Cek jumlah media** (cepat, 1 detik)
   ```bash
   curl -sL "https://api.fxtwitter.com/<screen>" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('user',{}); print(f'Media: {u.get(\"media_count\",\"?\")}')"
   ```

2. **Hitung split foto vs video** (~1-2 menit, GraphQL). ⚠️ Pakai script `x_user_top_media.py` versi terbaru — X udah ganti endpoint `UserMedia` → `UserVideoTimeline` / `UserPhotoTimeline`:
   ```bash
   ~/.hermes/hermes-agent/venv/bin/python ~/.hermes/skills/productivity/scrapebook/scripts/x_user_top_media.py <screen> --type video --count 0
   ~/.hermes/hermes-agent/venv/bin/python ~/.hermes/skills/productivity/scrapebook/scripts/x_user_top_media.py <screen> --type photo --count 0
   ```
   Angka `Found X total` = jumlah post berisi media tiap tipe.

3. **Download photos/videos** (`--count 0` = semua, `--type` harus `photo`/`video`):
   ```bash
   ~/.hermes/hermes-agent/venv/bin/python ~/.hermes/skills/productivity/scrapebook/scripts/x_user_top_media.py <screen> --type photo --count 0 --output-dir ~/Downloads/x/<screen>/photos
   ~/.hermes/hermes-agent/venv/bin/python ~/.hermes/skills/productivity/scrapebook/scripts/x_user_top_media.py <screen> --type video --count 0 --output-dir ~/Downloads/x/<screen>/videos
   ```

   ⚠️ **Khusus TikTok:** download pake metode di bawah. Hasilnya di `~/Downloads/tiktok/<handle>/`, BUKAN `~/Downloads/x/<handle>/`. Wajib mindahin file sebelum upload:
   ```bash
   mkdir -p ~/Downloads/x/<handle>/videos
   mv ~/Downloads/tiktok/<handle>/*.mp4 ~/Downloads/x/<handle>/videos/
   ```

4. **Upload ke Mega** (~3-5 detik per file)
   ```bash
   bash ~/.hermes/skills/productivity/cloud-storage-sync/scripts/upload_mega.sh <screen> photos
   bash ~/.hermes/skills/productivity/cloud-storage-sync/scripts/upload_mega.sh <screen> videos
   ```

   ⚠️ **Kalo megaput error "File already exists"** — itu bug megatools kalo foldernya udah ada. Fallback pake rclone:
   ```bash
   rclone copy ~/Downloads/x/<screen>/photos mega:<screen>/foto/ --transfers 1 --checkers 1
   rclone copy ~/Downloads/x/<screen>/videos mega:<screen>/video/ --transfers 1 --checkers 1
   ```

## Telegram Delivery — batch MEDIA: lines

Kirim semua file dalam SATU response via MEDIA: path. Jangan kirim satu-satu — user bakal frustrasi.

**A. User minta semua video/foto dikirim** — tulis semua MEDIA: path dalam 1 response:

```bash
# Dapatkan daftar file — pastikan path benar dulu!
ls ~/Downloads/x/<screen>/videos/*.mp4 | sort | while read f; do echo "MEDIA:$f"; done
```

Contoh response:
```
MEDIA:/home/ubuntu/Downloads/x/<screen>/videos/1234.mp4
MEDIA:/home/ubuntu/Downloads/x/<screen>/videos/5678.mp4
... (hingga 40+ file works dalam 1 response)
```

**⚠️ VERIFY path SEBELUM nulis MEDIA: line.** Path-format `0.mp4`, `1.mp4` itu SALAH — file aslinya punya nama Tweet ID (`1234567890.mp4`). Selalu jalanin `ls ~/Downloads/x/<screen>/videos/` dulu buat mastiin nama file bener. Kalo salah, user bakal nanya "Mana?" 3× dan itu bikin frustrasi.

**B. File terlalu besar untuk Telegram** (>50MB per file) — compress atau split:
```bash
tar czf /tmp/<screen>_videos.tar.gz -C ~/Downloads/x/<screen>/videos .
ls -lh /tmp/<screen>_videos.tar.gz
# Kalo >50MB, split:
split -b 50M /tmp/<screen>_videos.tar.gz /tmp/<screen>_videos_part_
# Kirim setiap part via MEDIA:
```

**C. Foto** — biasanya <5MB/file, batch semua MEDIA: path tanpa compress.

**D. User minta jumlah spesifik** (misal "40 video", "50 video", "100 video") — kirim tepat N file pake sed -n:

```bash
# Kirim 40 video pertama
ls ~/Downloads/x/<screen>/videos/*.mp4 | sort | sed -n '1,40p'
# Hasil → tempelkan MEDIA: prefix di response line

# Kalo user minta lagi, kirim batch berikutnya (41-80)
ls ~/Downloads/x/<screen>/videos/*.mp4 | sort | sed -n '41,80p'
```

**Jangan tanya "mau berapa lagi"** — langsung kirim batch berikutnya berdasarkan batch sebelumnya. Kalo udah kirim 1-40, berikutnya 41-80, dst. User yg reply "Mana lagi" atau "?" berarti minta LANJUTAN, bukan tanya jumlah.

**E. Kalo user bilang "kirim semua"** = SEMUA. Jangan tanya konfirmasi.

**F. User minta "top N" — tapi TikTok VS X beda approach:**

| Platform | Punya ranking? | Action |
|----------|---------------|--------|
| **X/Twitter** | ✅ Ada like/sort di `x_count_media.py` | Bisa kasih "top 40 by likes" |
| **TikTok** | ❌ `yt-dlp --flat-playlist` gak return like count | Kirim N pertama dari hasil sort file. Bilang aja gak ada data like — yang dikirim N video terbaru / teracak. |

## TikTok — Cepat (5 detik, via Camofox)

Gunakan ketika user kasih link TikTok (vt.tiktok.com/... atau tiktok.com/@user) dan mau tau jumlah video/followers/likes.

```bash
# 1. Buka profile via Camofox
~/.local/bin/camofox open "https://www.tiktok.com/@<handle>" --user ubuntu
# → stdout: tabId: <uuid>

# 2. Tunggu render
sleep 5

# 3. Extract stats dari embedded JSON
~/.local/bin/camofox eval \
  "document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__').textContent" \
  "<tabId>" --user ubuntu > /tmp/<handle>_tiktok.json

# 4. Parse
python3 -c "
import json
d = json.load(open('/tmp/<handle>_tiktok.json'))
u = d['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']
print(f\"@{u['user']['uniqueId']} — {u['user']['nickname']}\")
print(f\"Followers: {u['stats']['followerCount']:,}\")
print(f\"Videos:    {u['stats']['videoCount']:,}\")
print(f\"Likes:     {u['stats']['heartCount']:,}\")
print(f\"Bio:       {u['user'].get('signature','')}\")
"
```

Catatan: TikTok count semua post sebagai "video" — gak ada split foto vs video. Kalau user tanya "ada berapa foto?", bilang aja jumlah total post.

## TikTok — Batch Download Semua Video

Untuk kasus "gas download semua" dengan ratusan video:

```bash
# 1. Enumerate semua video IDs
yt-dlp --flat-playlist --print "%(id)s" "https://www.tiktok.com/@<handle>" > /tmp/<handle>_ids.txt

# 2. Convert ke URL list
sed 's|^|https://www.tiktok.com/@<handle>/video/|' /tmp/<handle>_ids.txt > /tmp/<handle>_urls.txt

# 3. Download via batch-file (sequential, tapi simpel)
mkdir -p ~/Downloads/tiktok/<handle>
yt-dlp -o "%(id)s.%(ext)s" -f "best[ext=mp4]/best" --no-warnings \
  --batch-file /tmp/<handle>_urls.txt --limit-rate 5M

# 4. ⚠️ WAJIB — bersihin audio-only & file sampah SEBELUM kirim ke user / upload
#    yt-dlp sering download file region-locked sebagai MP3 (audio doang)
#    tanpa error/warning. Script verify_batch.sh ngurusin 2 jenis sampah:
#    - File .mp3 (100% audio, hapus aja)
#    - File .mp4 yg isinya MP3 doang (ketauan via ffprobe)
bash ~/.hermes/skills/productivity/media-download/scripts/verify_batch.sh \
  ~/Downloads/tiktok/<handle>
```

Untuk jumlah >500 video, lebih baik pake chunked parallel di skill `media-download`.

## Pitfalls
- **⚠️ X ganti endpoint GraphQL media (Agt 2026):** `UserMedia` sudah TIDAK dipakai lagi. Sekarang:
  - Video → `UserVideoTimeline`
  - Foto → `UserPhotoTimeline`
  - Tab media X sekarang punya dropdown **Video/Foto**. Klik link `/media` dulu buat buka dropdown, baru klik `Foto` — kalau tidak, query foto (`UserPhotoTimeline`) tidak pernah ke-load dan hasil foto 0.
  - Struktur tweet di response timeline sekarang di `content.itemContent.tweet_results.result`, bukan langsung punya `legacy`. Script `walk()` harus handle dua-duanya.
  - Ini bikin download foto awalnya gagal balik 0 — sudah fixed di `x_user_top_media.py` versi terbaru.
- **Akun baru (March 2026+) gak bisa via X API v1.1** — error 34 ("page not exist") di `users/show.json` dan `statuses/user_timeline.json`. Tapi fxtwitter API masih works buat total media count. Fallback: fxtwitter dulu, baru GraphQL kalo perlu.
- **fxtwitter `media_count` hanya total gabungan foto+video** — gak bisa dipisah per tipe dari API-nya aja. Split foto/video perlu GraphQL scrape.
- **Scroll rounds menentukan kelengkapan.** `--scroll 60` ≈ ~60% total, `--scroll 140` dapet ~99%. Untuk akun gede (600+ media) selalu pakai `--scroll 140`.
- fxtwitter rate limit → fallback ke GraphQL scrape
- GraphQL cursor cuma dapet ~85% total media
- `megamkdir` gak recursive: bikin parent dulu baru child
- Kalo mau liat hasil dulu sebelum upload, call `x_user_top_media.py --list`
- **Telegram Bot limit 50MB per file** — kalo kirim archive >50MB, wajib split dulu pake `split -b 50M`. Suruh user join balik pake `cat parts* > archive.tar.gz`.
- **`zip` mungkin gak terinstall** — pake `tar czf` instead. Ubuntu minimal image sering gak include zip.
- **TikTok shortlink `vt.tiktok.com/Z...` harus di-resolve dulu** — redirect ke profile URL:
  ```bash
  curl -sL -o /dev/null -w "%{url_effective}" "https://vt.tiktok.com/Z.../"
  ```
  Hasilnya: `https://www.tiktok.com/@<handle>?_r=1&_t=...`. Ambil handle dari URL itu, jangan langsung buka shortlink-nya.
- **Batch continuation: kalo user minta lagi setelah batch pertama, jangan tanya "mau berapa lagi"** — hitung dari batch yg udah dikirim. Misal udah kirim 1-40, berikutnya langsung 41-80. User yg minta "Mana lagi" atau "?" berarti minta lanjutan, bukan tanya jumlah.
- **Background download paralel** — foto (small, <1MB) dan video (bisa 100MB+) jalan bareng gapapa, tapi kalo RAM terbatas (<2GB), run sequential aja biar gak swap thrash.
- **Kirim file individual: batch ALL in one response, jangan satu-satu** — User yang minta file dikirim langsung akan frustrasi kalo dikirim satu per satu secara bergantian ("Mana lagi 😭"). Selalu kumpulkan semua MEDIA: path dalam SATU response. Telegram handle puluhan file attachments sekaligus dengan baik. Tested: 40+ MEDIA: path dalam 1 response works di Telegram tanpa masalah.
- **Jangan tanya jumlah dulu kalo user minta kirim semua** — Langsung kirim semua file. User yang bilang "kirim semua video" berarti SEMUA, bukan "mau berapa?". Kecuali mereka spesifik minta jumlah tertentu ("40 video").
- **VERIFY path file SEBELUM nulis MEDIA:** line — jalan `ls ~/Downloads/x/<screen>/videos/` dulu. Path yang salah atau typo bakal silent drop di Telegram — user cuma liat teks "MEDIA:/path/..." doang, gak ada attachment. Verified Jul 2026: 5 foto dari cache akun lain path-nya beda, user nanya "Mana?" 3x.
- **TikTok `videoCount` includes semua post**, bukan cuma video — TikTok gak bedain photo mode vs video. Kalo user tanya "ada berapa foto?", bilang jumlah total post aja.
- **CEK available disk SEBELUM download batch besar** — TikTok 1000+ video bisa makan 1-2 GB. Jalanin `df -h /` dulu. Kalo free <5GB, peringatin user.
- **Unbroker / data broker privacy tool — hanya buat warga US.** Skill `unbroker` di Hermes repo optional-skills/ hanya berguna buat warga negara US (punya SSN, alamat US, nomor US). Data broker yang di-scan (Spokeo, Whitepages, BeenVerified, TruePeopleSearch, dll) adalah situs aggregator data publik US — voter registration, property records, court records US. Warga Indonesia gak akan ditemukan di situs-situs itu. Kalo user Indonesia minta di-scan, cukup bilang "data broker US gak punya data orang Indo" dan skip. Jangan buang waktu scan 51 situs.
- **TikTok batch download yield** — dari 1609 video dari VPS Singapore, biasanya cuma ~808 (50%) yang genuine video. Sisanya:
  - ~538 (33%) jadi audio-only **MP3** (region-locked, skip aja)
  - ~180 (11%) jadi **MP4 berisi MP3 doang** (region-locked, ketauan via ffprobe)
  - ~83 (5%) gagal total (error/deleted)
  **Total unusable ≈ 45%.** Jadi kalo user minta "download semua" TikTok dari SG VPS, bilang estimasi yield ~50-60% biar gak kaget. Step 4 (verify_batch.sh) otomatis hapus file sampah.
  Catatan: yield rate bisa beda tergantung region VPS dan region creator TikTok.
