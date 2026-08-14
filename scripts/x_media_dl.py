#!/usr/bin/env python3
"""Download semua media dari akun X via GraphQL UserVideoTimeline/UserPhotoTimeline.
Simpan ke ~/Downloads/x/<screen>/photos dan ~/Downloads/x/<screen>/videos
"""
import os, sys, time, argparse
import requests
from playwright.sync_api import sync_playwright

COOKIE = os.path.expanduser("~/.config/social-dl/cookies/x.com.txt")
BASE = os.path.expanduser("~/Downloads/x")

def load_cookies(path):
    cookies = []; now = time.time()
    for line in open(path):
        if line.startswith("#") or not line.strip(): continue
        parts = line.split("\t")
        if len(parts) < 7: continue
        domain,_,path_,secure,expires,name,value = parts[:7]
        exp = int(expires) if expires.isdigit() else -1
        if exp > 0 and exp < now: continue
        cookies.append({"name":name,"value":value.strip(),
                        "domain":domain if domain.startswith(".") else "."+domain,
                        "path":path_,"secure":secure=="TRUE",
                        "expires":exp if exp>0 else -1})
    return cookies

def walk(obj, items, seen):
    """Kumpulkan media: (type, url, likes, tid). Handle struktur timeline lama & baru."""
    if isinstance(obj, dict):
        # struktur baru: content.itemContent.tweet_results.result
        if "__typename" in obj and obj.get("tweet_results"):
            tr = obj.get("tweet_results", {}).get("result")
            if tr and isinstance(tr, dict):
                walk(tr, items, seen)
        # struktur lama/umum: dict tweet dengan legacy
        if "rest_id" in obj and "legacy" in obj:
            legacy = obj.get("legacy", {})
            tid = obj.get("rest_id")
            media = (legacy.get("extended_entities",{}).get("media")
                     or legacy.get("entities",{}).get("media") or [])
            for m in media:
                if tid in seen: continue
                seen.add(tid)
                typ = m.get("type")
                url = ""
                if typ == "video":
                    mp4s = [v for v in m.get("video_info",{}).get("variants",[])
                            if v.get("content_type")=="video/mp4"]
                    if mp4s:
                        url = max(mp4s, key=lambda x:x.get("bitrate",0))["url"]
                elif typ == "photo":
                    url = m.get("media_url_https","") + "?format=jpg&name=orig"
                if url:
                    items.append({"type":typ,"url":url,"likes":legacy.get("favorite_count",0),"id":tid})
        for v in obj.values(): walk(v, items, seen)
    elif isinstance(obj, list):
        for v in obj: walk(v, items, seen)

def collect(screen, media_type, scroll_rounds=120):
    query = "UserVideoTimeline" if media_type=="video" else "UserPhotoTimeline"
    items = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width":1280,"height":900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0")
        ctx.add_cookies(load_cookies(COOKIE))
        page = ctx.new_page()
        bodies = []
        def on_resp(r):
            if query in r.url and r.status==200:
                try: bodies.append(r.json())
                except Exception: pass
        page.on("response", on_resp)
        page.goto(f"https://x.com/{screen}/media", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        if media_type=="photo":
            # klik link /media buka dropdown, lalu pilih "Foto" — retry sampai berhasil
            for attempt in range(4):
                try:
                    page.click(f'a[href="/{screen}/media"]', timeout=4000)
                    page.wait_for_timeout(1500)
                    page.click('text=Foto', timeout=4000)
                    page.wait_for_timeout(4000)
                    if "filter=photo" in page.url:
                        break
                except Exception as e:
                    print(f"  [!] attempt {attempt} switch Foto gagal: {e}", file=sys.stderr)
                    page.wait_for_timeout(1500)
            # fallback: pastikan kita di URL filter=photo
            if "filter=photo" not in page.url:
                try:
                    page.goto(f"https://x.com/{screen}/media?filter=photo",
                              wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(4000)
                except Exception:
                    pass
        for _ in range(scroll_rounds):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1500)
        b.close()
    seen = set()
    for body in bodies: walk(body, items, seen)
    return items

def download(items, outdir, media_type, screen):
    os.makedirs(outdir, exist_ok=True)
    # skip file yang udah ada (>100KB)
    existing = set(os.listdir(outdir))
    sess = requests.Session()
    sess.headers.update({"User-Agent":"Mozilla/5.0","Referer":f"https://x.com/{screen}"})
    ext = "mp4" if media_type=="video" else "jpg"
    ok=skip=err=0
    for i, it in enumerate(items, 1):
        fn = f"{it['id']}.{ext}"
        if fn in existing and os.path.getsize(os.path.join(outdir,fn)) > 100_000:
            skip += 1; continue
        try:
            r = sess.get(it["url"], timeout=180, stream=True)
            r.raise_for_status()
            tmp = os.path.join(outdir, fn + ".part")
            with open(tmp,"wb") as f:
                for chunk in r.iter_content(chunk_size=1024*256):
                    if chunk: f.write(chunk)
            os.replace(tmp, os.path.join(outdir,fn))
            ok += 1
        except Exception as e:
            err += 1
            if i<=3: print(f"  ERR {it['id']}: {e}")
        if i % 20 == 0:
            print(f"  ...{i}/{len(items)} (ok={ok} skip={skip} err={err})")
    print(f"[{media_type.upper()}] selesai: ok={ok} skip={skip} err={err} total={len(items)}")
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("screen")
    ap.add_argument("--type", choices=["video","photo","all"], default="all")
    ap.add_argument("--scroll", type=int, default=120)
    args = ap.parse_args()
    screen = args.screen
    base = os.path.join(BASE, screen)

    if args.type in ("all","video"):
        print(f"[*] Koleksi VIDEO dari @{screen}...")
        items = collect(screen, "video", args.scroll)
        print(f"  -> {len(items)} video. Download...")
        download(items, os.path.join(base,"videos"), "video", screen)

    if args.type in ("all","photo"):
        print(f"[*] Koleksi FOTO dari @{screen}...")
        items = collect(screen, "photo", args.scroll)
        print(f"  -> {len(items)} foto. Download...")
        download(items, os.path.join(base,"photos"), "photo", screen)

    print("SELESAI. Lokasi:", base)

if __name__ == "__main__":
    main()
