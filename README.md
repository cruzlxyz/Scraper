# Scraper

Scrape & download semua media (foto & video) dari akun X/Twitter lewat GraphQL.
Dibangun dari workflow AI agent yang sudah terverifikasi download nyata (440 & 510 file).

## Kenapa repo ini ada

X baru-baru ini ganti struktur GraphQL media. Endpoint lama `UserMedia` sudah tidak dipakai lagi dan
balik hasil kosong. Repo ini pakai endpoint baru yang terbukti jalan:

- **Video** → `UserVideoTimeline`
- **Foto** → `UserPhotoTimeline`
- Tab media X sekarang punya **dropdown Video/Foto** — harus diklik dulu biar query foto ke-load,
  kalau tidak hasil foto = 0.
- Struktur tweet di response sekarang di `content.itemContent.tweet_results.result`, bukan langsung punya `legacy`.

## Prasyarat

- Cookies X.com (format Netscape): `~/.config/social-dl/cookies/x.com.txt`
- Python 3 + `playwright` (chromium)
- VPS/US region yang gak di-block X

## Cara pakai

Hitung split foto vs video:

```bash
python scripts/x_media_dl.py <screen_name> --type video --count 0
python scripts/x_media_dl.py <screen_name> --type photo --count 0
```

Download semua (`--count 0` = semua, `--scroll 140` ≈ ~99% coverage):

```bash
python scripts/x_media_dl.py <screen_name> --type video --count 0 --output-dir ~/Downloads/x/<screen>/videos
python scripts/x_media_dl.py <screen_name> --type photo --count 0 --output-dir ~/Downloads/x/<screen>/photos
```

File disimpan dengan nama `TweetID.jpg` / `TweetID.mp4`, di-sort by likes (paling populer duluan).

## Opsi

| Flag | Deskripsi |
|------|-----------|
| `--type {video,photo}` | Jenis media |
| `--count N` | Ambil N teratas; `0` = semua |
| `--scroll N` | Jumlah scroll (default 140). `60` ≈ 60%, `140` ≈ 99% |
| `--output-dir` | Folder tujuan download |
| `--cookies` | Path file cookies (default `~/.config/social-dl/cookies/x.com.txt`) |

## Pitfalls

- **Rate limit (HTTP 429):** X ketat kalau request keburu. Pakai `--scroll` sedang + jeda antar scroll.
  Kalau kena 429, tunggu 2-3 menit dulu lalu ulangi — script skip file yang sudah ada otomatis.
- **Akun baru (Mar 2026+)** gak bisa via X API v1.1 (error 34) — tapi fxtwitter API masih bisa buat total media count.
- **fxtwitter `media_count`** hanya total gabungan, gak bisa split per tipe. Split perlu GraphQL.
- Multi-foto dihitung 1 post → angka post bisa lebih kecil dari total item media.
- File yang sudah ada (>100KB) otomatis di-skip saat re-run.

## Struktur

```
scraper/
├── README.md
├── SKILL.md                  # manifest skill (drop ke ~/.hermes/skills/)
└── scripts/
    └── x_media_dl.py         # scraper & downloader utama
```

## Lisensi

MIT
