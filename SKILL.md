---
name: scraper-x-media
description: Scrape & download semua foto/video dari akun X via GraphQL endpoint baru. Hitung split, download, sort by likes.
metadata:
  hermes:
    tags: [x, twitter, media, scrape, download, graphql, photos, videos]
    category: productivity
---

# Scraper X Media

Download semua foto & video dari akun X/Twitter. Satu workflow: cek total → hitung split → download → simpan per folder.

## Kapan pakai
- User kasih link akun X (`x.com/<handle>`) dan mau tau jumlah foto/video
- User mau download semua media akun X
- User mau media dikirim ke Telegram / upload ke cloud

## Prasyarat
- Cookies X (Netscape): `~/.config/social-dl/cookies/x.com.txt`
- Python + playwright (chromium)
- VPS/US region (X gak di-block)

## ⚠️ Baca dulu: X ganti endpoint (Agt 2026)
Endpoint lama `UserMedia` **sudah tidak dipakai** — balik kosong. Pakai:
- Video → **`UserVideoTimeline`**
- Foto → **`UserPhotoTimeline`**
- Tab media X punya **dropdown Video/Foto** — klik `/media` lalu `Foto` biar query foto ke-load, kalau tidak foto = 0.
- Struktur tweet baru di `content.itemContent.tweet_results.result`. Script `walk()` handle dua-duanya.

## Cara pakai

**1. Cek total media (cepat, 1 detik)**
```bash
curl -sL "https://api.fxtwitter.com/<handle>" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('user',{}); print(f'Media total: {u.get(\"media_count\",\"?\")}')"
```
> fxtwitter cuma kasih total gabungan, gak bisa split per tipe.

**2. Hitung split foto vs video (~2 menit)**
```bash
python scripts/x_media_dl.py <handle> --type video --count 0
python scripts/x_media_dl.py <handle> --type photo --count 0
```
Output `Found X total` = jumlah post berisi media tiap tipe.

**3. Download semua**
```bash
python scripts/x_media_dl.py <handle> --type video --count 0 --output-dir ~/Downloads/x/<handle>/videos
python scripts/x_media_dl.py <handle> --type photo --count 0 --output-dir ~/Downloads/x/<handle>/photos
```
File disimpan `TweetID.jpg` / `TweetID.mp4`, di-sort by likes.

## Opsi script
| Flag | Fungsi |
|------|--------|
| `--type {video,photo}` | Jenis media (wajib) |
| `--count N` | Ambil N teratas by likes. `0` = semua |
| `--scroll N` | Jumlah scroll. `140` ≈ 99% coverage (default) |
| `--output-dir` | Folder tujuan |
| `--cookies` | Path cookies (default sudah otomatis) |

## Kirim ke Telegram
Batch semua file dalam SATU response, jangan satu-satu:
```bash
ls ~/Downloads/x/<handle>/photos/*.jpg | sort | sed -n '1,50p'
```
Tempel hasilnya sebagai `MEDIA:/full/path/...` per baris. Verifikasi path dulu — path salah = silent drop (user tanya "Mana?").

## Pitfalls
- **Rate limit 429:** X ketat kalau request keburu. Pakai `--scroll` wajar + jeda. Kalau kena 429, tunggu 2-3 menit, ulangi (script skip file yang sudah ada otomatis).
- **Akun baru (Mar 2026+)** gak bisa via X API v1.1 (error 34) — fxtwitter masih jalan buat total count.
- **Multi-foto** dihitung 1 post → angka post bisa lebih kecil dari total item (foto dobel dalam 1 post).
- **Akun gede (600+ media)** wajib `--scroll 140`, kalau `60` cuma dapet ~60%.
- **Cek disk dulu** (`df -h /`) sebelum download besar — ratusan video bisa makan GB.
- **File existing (>100KB) otomatis di-skip** — aman di re-run.
- **Telegram limit 50MB/file** — video gede compress/split dulu.
