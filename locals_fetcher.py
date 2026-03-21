"""
Fetch playlist video list and video metadata from Locals.com using saved cookies.
Playlist and video pages are JS-rendered, so we use Playwright with cookies to get links and metadata.
"""
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import config


def _extract_title_and_description(html: str) -> tuple[str, str]:
    """Best-effort extraction of Locals post title and description from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    desc = ""

    # Locals post block: div[communityid] contains h3 (title) and a <p> (description)
    post_block = soup.find("div", attrs={"communityid": True})
    if post_block:
        h3 = post_block.find("h3")
        if h3:
            title = h3.get_text(strip=True)
        p_el = post_block.find("p")
        if p_el:
            desc = p_el.get_text(strip=True)

    # Fallback: social meta tags
    if not title:
        for key in ("og:title", "twitter:title"):
            tag = soup.find("meta", attrs={"property": key}) or soup.find(
                "meta", attrs={"name": key}
            )
            if tag and tag.get("content"):
                title = tag["content"].strip()
                break
    if not desc:
        for key in ("og:description", "twitter:description"):
            tag = soup.find("meta", attrs={"property": key}) or soup.find(
                "meta", attrs={"name": key}
            )
            if tag and tag.get("content"):
                desc = tag["content"].strip()
                break

    # Fallback: classic <title> and <meta name="description">
    if not title and soup.title:
        title = (soup.title.string or "").strip()
    if not desc:
        for meta in soup.find_all("meta", attrs={"name": "description"}):
            if meta.get("content"):
                desc = meta["content"].strip()
                break

    # Last resort: any heading
    if not title:
        h = soup.find(["h1", "h2", "h3"])
        if h:
            title = h.get_text(strip=True)

    return title, desc


def _load_netscape_cookies(cookies_path: str | Path) -> list[dict]:
    """Parse a Netscape-format cookie file into a list of dicts for Playwright."""
    path = Path(cookies_path)
    if not path.exists():
        return []
    cookies = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _include_sub, path_str, secure, expires, name, value = parts[:7]
        cookie = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path_str,
            "secure": secure.upper() == "TRUE",
            "httpOnly": False,
            "sameSite": "Lax",
        }
        try:
            cookie["expires"] = int(float(expires)) if expires != "0" else -1
        except ValueError:
            cookie["expires"] = -1
        cookies.append(cookie)
    return cookies


def get_playlist_video_urls(
    playlist_url: str,
    cookies_path: str | Path,
    *,
    timeout_ms: int = 60_000,
) -> list[str]:
    """
    Load the Locals playlist page with Playwright (with saved cookies), extract video page URLs.
    Returns a list of absolute URLs in playlist order.
    """
    from playwright.sync_api import sync_playwright

    cookies_path = Path(cookies_path)
    cookie_list = _load_netscape_cookies(cookies_path)
    if not cookie_list:
        return []

    def _extract_post_urls(html: str, base: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        out = []
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or href.startswith("#"):
                continue
            full = urljoin(base, href) if href.startswith("/") else href
            if full in seen or "locals.com" not in full:
                continue
            if "feed?playlist=" in full and "post=" not in full:
                continue
            if "post=" in full:
                seen.add(full)
                out.append(full)
            else:
                lower = full.lower()
                if "video" in lower or "content" in lower or "/post/" in lower:
                    seen.add(full)
                    out.append(full)
        return out

    base = f"{urlparse(playlist_url).scheme}://{urlparse(playlist_url).netloc}"
    with sync_playwright() as p:
        headless = os.environ.get("LOCALS_HEADLESS", "1") != "0"
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_cookies(cookie_list)
        page = context.new_page()
        try:
            page.goto(playlist_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_load_state("domcontentloaded")
            # Scroll to load all items (infinite scroll; ~260 videos)
            prev_count = 0
            no_new_count = 0
            max_scrolls = 80
            for _ in range(max_scrolls):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2500)
                html = page.content()
                urls_so_far = _extract_post_urls(html, base)
                current = len(urls_so_far)
                if current == prev_count:
                    no_new_count += 1
                    if no_new_count >= 2:
                        break
                else:
                    no_new_count = 0
                prev_count = current
            html = page.content()
            if os.environ.get("LOCALS_DEBUG_HTML"):
                Path("playlist_page_debug.html").write_text(html, encoding="utf-8")
                print(f"  [debug] Saved playlist HTML to playlist_page_debug.html")
        finally:
            browser.close()

    # Dedupe preserving order
    urls = list(dict.fromkeys(_extract_post_urls(html, base)))
    return urls


def _fetch_page_with_cookies(url: str, cookies_path: str | Path) -> str:
    """Fetch URL with Netscape cookies; return response text or empty string."""
    import http.cookiejar
    import requests

    path = Path(cookies_path)
    if not path.exists():
        return ""
    jar = http.cookiejar.MozillaCookieJar(str(path))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception:
        return ""
    try:
        r = requests.get(
            url,
            cookies=jar,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"},
            timeout=30,
        )
        r.raise_for_status()
        return r.text
    except Exception:
        return ""


def get_video_info_and_stream_url(
    video_page_url: str,
    cookies_path: str | Path,
    *,
    timeout_ms: int = 30_000,
) -> tuple[str, str, str | None]:
    """
    Load the Locals video page with Playwright, extract title, description, and video stream URL.
    Returns (title, description, stream_url). stream_url may be m3u8, mp4, or None if not found.
    """
    from playwright.sync_api import sync_playwright

    cookie_list = _load_netscape_cookies(cookies_path)
    if not cookie_list:
        return "", "", None

    stream_url: str | None = None

    # Extract post ID from URL (e.g. feed?post=5924409 -> 5924409)
    post_id = None
    if "post=" in video_page_url:
        match = re.search(r"post=(\d+)", video_page_url)
        if match:
            post_id = match.group(1)

    # Optional: probe Locals API for post details (may return video stream URL or UUID).
    # Disabled by default because Cloudflare blocks direct access to webapi.locals.com.
    if post_id and not stream_url and os.environ.get("LOCALS_ENABLE_API_PROBE") == "1":
        import json as _json
        import requests as req
        import http.cookiejar as cj
        jar = cj.MozillaCookieJar(str(Path(cookies_path)))
        debug_api = os.environ.get("LOCALS_DEBUG_HTML") or os.environ.get("LOCALS_DEBUG_API")
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
            for api_url in (
                f"https://webapi.locals.com/api/v1/posts/{post_id}",
                f"https://webapi.locals.com/api/v1/feed/post/{post_id}",
            ):
                try:
                    r = req.get(
                        api_url,
                        cookies=jar,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"},
                        timeout=15,
                    )
                    if debug_api:
                        print(f"  [debug] API {api_url} -> {r.status_code} (len={len(r.text)})")
                    if r.status_code != 200 and r.text and debug_api:
                        Path("post_api_403_debug.json").write_text(r.text[:20000], encoding="utf-8")
                        print(f"  [debug] Saved non-200 response to post_api_403_debug.json")
                    if r.status_code == 200 and r.text:
                        text = r.text
                        if debug_api:
                            out = Path("post_api_debug.json")
                            out.write_text(text[:50000], encoding="utf-8")
                            print(f"  [debug] Saved API response to {out}")
                        # Search for m3u8 URL in JSON response (raw string)
                        m = re.search(
                            r'https://webapi\.locals\.com/api/v1/posts/content/hls/[^"\'<>\s]+\.m3u8\?vt=[^"\'<>\s]+',
                            text,
                        )
                        if m:
                            stream_url = m.group(0)
                            break
                        # Or look for video UUID + token (vt may be in different keys)
                        if not stream_url and "content/hls" in text:
                            uuid_m = re.search(r'(v_[a-f0-9\-]+)', text)
                            vt_m = re.search(r'"vt"\s*:\s*"([^"]+)"', text) or re.search(r'"vt"\s*:\s*([^,}\s]+)', text)
                            if uuid_m and vt_m:
                                vt_val = vt_m.group(1).strip('"')
                                stream_url = f"https://webapi.locals.com/api/v1/posts/content/hls/{uuid_m.group(1)}/source.m3u8?vt={vt_val}"
                                break
                        # Parse JSON and walk for video/hls url or nested object with uuid + vt
                        if not stream_url:
                            try:
                                data = _json.loads(text)
                                def find_hls(obj, depth=0):
                                    if depth > 20:
                                        return None
                                    if isinstance(obj, dict):
                                        if "hls" in str(obj).lower() and isinstance(obj.get("url"), str) and ".m3u8" in obj.get("url", ""):
                                            return obj["url"]
                                        for k, v in obj.items():
                                            u = find_hls(v, depth + 1)
                                            if u:
                                                return u
                                    elif isinstance(obj, list):
                                        for item in obj:
                                            u = find_hls(item, depth + 1)
                                            if u:
                                                return u
                                    return None
                                u = find_hls(data)
                                if u:
                                    stream_url = u
                                    break
                                # Look for video_uuid / vt or source_url in nested structure
                                def find_video_parts(obj, depth=0):
                                    if depth > 20:
                                        return None, None
                                    if isinstance(obj, dict):
                                        uuid, vt = obj.get("video_uuid"), obj.get("vt") or obj.get("token")
                                        if uuid and vt:
                                            return str(uuid), str(vt)
                                        for k, v in obj.items():
                                            a, b = find_video_parts(v, depth + 1)
                                            if a and b:
                                                return a, b
                                    elif isinstance(obj, list):
                                        for item in obj:
                                            a, b = find_video_parts(item, depth + 1)
                                            if a and b:
                                                return a, b
                                    return None, None
                                uuid_part, vt_part = find_video_parts(data)
                                if uuid_part and vt_part:
                                    stream_url = f"https://webapi.locals.com/api/v1/posts/content/hls/{uuid_part}/source.m3u8?vt={vt_part}"
                                    break
                            except _json.JSONDecodeError:
                                pass
                except Exception as e:
                    if debug_api:
                        print(f"  [debug] API request error: {e}")
                    continue
        except Exception as e:
            if debug_api:
                print(f"  [debug] API init error: {e}")
            pass

    if stream_url and post_id:
        # We got stream from API; get title/description from the page
        page_text = _fetch_page_with_cookies(video_page_url, cookies_path)
        if page_text:
            soup = BeautifulSoup(page_text, "html.parser")
            title = (soup.title.string or "").strip() if soup.title else ""
            desc = ""
            for meta in soup.find_all("meta", attrs={"name": "description"}):
                if meta.get("content"):
                    desc = meta["content"].strip()
                    break
            if not title:
                h1 = soup.find("h1")
                if h1:
                    title = h1.get_text(strip=True)
            return title, desc, stream_url

    # Fetch post page and search for m3u8 URL in HTML/JSON (often embedded)
    page_text = _fetch_page_with_cookies(video_page_url, cookies_path)
    if page_text and not stream_url:
        # Match: webapi.locals.com/.../hls/.../source.m3u8?vt=... or .../playlist/.../720.m3u8?vt=...
        for pattern in (
            r'https://webapi\.locals\.com/api/v1/posts/content/hls/[^"\'<>\s]+\.m3u8\?vt=[^"\'<>\s]+',
            r'https://webapi\.locals\.com/api/v1/posts/content/hls/[^"\'<>\s]+\.m3u8[^"\'<>\s]*',
        ):
            match = re.search(pattern, page_text)
            if match:
                u = match.group(0)
                for a, b in (
                    ("\\u0026", "&"),
                    ("\\u002f", "/"),
                    ("\\/", "/"),
                    ("&amp;", "&"),
                    ("\\?", "?"),
                ):
                    u = u.replace(a, b)
                if "webapi.locals.com" in u and ".m3u8" in u:
                    stream_url = u
                    break
        if stream_url:
            # Get title/description from the same page text
            title, desc = _extract_title_and_description(page_text)
            return title, desc, stream_url

    # Playwright: load video page, capture stream URL from network responses
    captured_streams: list[str] = []

    def on_response(response):
        url = response.url
        if response.status != 200:
            return
        # Capture HLS manifests and direct MP4 URLs from ANY host.
        # Older Locals posts often fetch playlists from media*.locals.com (not webapi.locals.com).
        if ".m3u8" in url or ".mp4" in url:
            captured_streams.append(url)

    with sync_playwright() as p:
        headless = os.environ.get("LOCALS_HEADLESS", "1") != "0"
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_cookies(cookie_list)
        page = context.new_page()
        page.on("response", on_response)
        try:
            page.goto(video_page_url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(2000)
            # Try to get post title/description from initial post page (they may be here before thumbnail click).
            meta_title, meta_desc = "", ""
            try:
                result = page.evaluate(
                    """() => {
                      const generic = (document.title || '').trim();
                      let div = document.querySelector('div[communityid]') || document.querySelector('[communityid]');
                      if (div) {
                        const h3 = div.querySelector('h3');
                        const p = div.querySelector('p');
                        if (h3) return { title: h3.innerText.trim(), desc: (p && p.innerText.trim()) || '' };
                      }
                      const h3s = document.querySelectorAll('h3');
                      for (const h3 of h3s) {
                        const t = h3.innerText.trim();
                        if (t && t.length > 4 && t !== generic && !generic.startsWith(t)) {
                          const container = h3.closest('div');
                          const p = container ? container.querySelector('p') : document.querySelector('p');
                          return { title: t, desc: (p && p.innerText.trim()) || '' };
                        }
                      }
                      return { title: '', desc: '' };
                    }"""
                )
                if isinstance(result, dict):
                    meta_title = (result.get("title") or "").strip()
                    meta_desc = (result.get("desc") or "").strip()
            except Exception:
                pass
            # Some post pages show a clickable thumbnail card that navigates to the real video page.
            # Do NOT click generic `a:has(img)` (often goes to the creator profile / avatar).
            try:
                # Prefer Locals video thumbnails (as background-image): https://media*.locals.com/video/files/...
                thumb_card = page.locator('div[style*="locals.com/video/files/"]').first
                if thumb_card.count():
                    thumb_card.click(timeout=5000)
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    page.wait_for_timeout(2000)
                # If we got dumped to the profile feed, undo and try a safer click.
                if "mode=profile" in page.url:
                    page.go_back()
                    page.wait_for_timeout(1000)
                    # Click the nearest clickable ancestor of the thumbnail card (if any)
                    page.evaluate(
                        """() => {
                          const el = document.querySelector('div[style*="locals.com/video/files/"]');
                          if (!el) return;
                          const clickable = el.closest('a,button,[role="button"]') || el;
                          (clickable).click();
                        }"""
                    )
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    page.wait_for_timeout(2000)
            except Exception:
                pass
            # If we still don't have title/description, try again on this page (after thumbnail) before opening player.
            if not meta_title or not meta_desc:
                try:
                    page.wait_for_timeout(1500)
                    result = page.evaluate(
                        """() => {
                          const generic = (document.title || '').trim();
                          let div = document.querySelector('div[communityid]') || document.querySelector('[communityid]');
                          if (div) {
                            const h3 = div.querySelector('h3');
                            const p = div.querySelector('p');
                            if (h3) return { title: h3.innerText.trim(), desc: (p && p.innerText.trim()) || '' };
                          }
                          const h3s = document.querySelectorAll('h3');
                          for (const h3 of h3s) {
                            const t = h3.innerText.trim();
                            if (t && t.length > 4 && t !== generic && !generic.startsWith(t)) {
                              const container = h3.closest('div');
                              const p = container ? container.querySelector('p') : document.querySelector('p');
                              return { title: t, desc: (p && p.innerText.trim()) || '' };
                            }
                          }
                          return { title: '', desc: '' };
                        }"""
                    )
                    if isinstance(result, dict):
                        t = (result.get("title") or "").strip()
                        d = (result.get("desc") or "").strip()
                        if t:
                            meta_title = t
                        if d:
                            meta_desc = d
                except Exception:
                    pass
            # On the video page you then click a big play overlay (bg-r_no-repeat + SVG play icon).
            # Click that container to open the actual player page where the movie starts.
            try:
                play_overlay = page.locator("div.bg-r_no-repeat:has(svg.w_50px)").first
                if play_overlay.count():
                    play_overlay.click(timeout=5000)
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    page.wait_for_timeout(2000)
            except Exception:
                pass
            # Trigger video load so the site requests the m3u8 (only appears in network when player loads)
            try:
                page.wait_for_selector("video", state="attached", timeout=10_000)
            except Exception:
                pass
            # Click big play button if present
            try:
                btn = page.locator(".vjs-big-play-button").first
                if btn.count():
                    btn.click(force=True, timeout=3000)
                    page.wait_for_timeout(3000)
            except Exception:
                pass
            # Start playback to force m3u8 request
            page.evaluate("""() => {
                const v = document.querySelector('video');
                if (v) v.play().catch(() => {});
            }""")
            page.wait_for_timeout(5000)
            # Click video container as fallback (some UIs load stream on first click)
            try:
                page.locator("video").first.click(force=True, timeout=2000)
                page.wait_for_timeout(4000)
            except Exception:
                pass
            if not captured_streams:
                page.evaluate("() => { const v = document.querySelector('video'); if (v) v.play().catch(() => {}); }")
                page.wait_for_timeout(5000)
            # Prefer HLS master, then any m3u8, then mp4
            if captured_streams:
                stream_url = next(
                    (u for u in captured_streams if "source.m3u8" in u),
                    next((u for u in captured_streams if ".m3u8" in u), captured_streams[0]),
                )
            html = page.content()
            if os.environ.get("LOCALS_DEBUG_HTML") or os.environ.get("LOCALS_DEBUG_API"):
                Path("post_page_debug.html").write_text(html, encoding="utf-8")
                print("  [debug] Saved video/post page HTML to post_page_debug.html")
            if not stream_url and (os.environ.get("LOCALS_DEBUG_HTML") or os.environ.get("LOCALS_DEBUG_API")):
                safe_post = post_id or "unknown"
                Path(f"post_page_failed_{safe_post}.html").write_text(html, encoding="utf-8")
                print(f"  [debug] Saved failed page HTML to post_page_failed_{safe_post}.html")
            if not stream_url:
                # Fallback 1: scan page HTML for webapi.locals.com ... .m3u8 (often in script/config)
                match = re.search(
                    r'https://webapi\.locals\.com[^"\'<>\\s]+\.m3u8[^"\'<>\\s]*',
                    html,
                )
                if match:
                    u = match.group(0)
                    for a, b in (("\\u0026", "&"), ("\\/", "/"), ("&amp;", "&")):
                        u = u.replace(a, b)
                    stream_url = u
            if not stream_url:
                # Fallback 2: get stream from video element
                try:
                    stream_url = page.evaluate(
                        """() => {
                            const v = document.querySelector('video');
                            if (!v) return null;
                            return v.src || (v.querySelector('source') && v.querySelector('source').src) || null;
                        }"""
                    )
                except Exception:
                    pass
            if not stream_url:
                soup = BeautifulSoup(html, "html.parser")
                video = soup.find("video")
                if video and video.get("src"):
                    stream_url = video["src"]
                if not stream_url and video:
                    src = video.find("source", src=True)
                    if src:
                        stream_url = src.get("src")
            # Use title/description captured from post block (before player); fallback to final page
            title, desc = meta_title, meta_desc
            if not title or not desc:
                t, d = _extract_title_and_description(html)
                if not title:
                    title = t
                if not desc:
                    desc = d
            return title, desc, stream_url
        finally:
            browser.close()


def download_locals_video_with_ytdlp(
    video_url: str,
    output_dir: str,
    cookies_path: str | Path,
    outtmpl: str,
) -> tuple[str, str] | None:
    """
    Try to download a Locals video page with yt-dlp using the cookie file.
    Returns (title, description) on success, None on failure.
    """
    import os

    import yt_dlp

    path = Path(cookies_path)
    if not path.exists():
        return None
    opts = {
        "outtmpl": os.path.join(output_dir, outtmpl),
        "cookiefile": str(path),
        "quiet": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        if info:
            return (info.get("title") or "", info.get("description") or "")
    except Exception:
        pass
    return None


def download_locals_hls_with_ffmpeg(
    stream_url: str,
    output_path: str,
    cookies_path: str | Path,
) -> bool:
    """Download HLS stream (e.g. webapi.locals.com .../playlist/...m3u8?vt=JWT) using ffmpeg -c copy."""
    import shutil
    import subprocess

    path = Path(cookies_path)
    if not path.exists():
        return False
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    # Build Cookie header from Netscape file for auth
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        parts = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) >= 7:
                parts.append(f"{cols[5]}={cols[6]}")
        cookie_header = ("Cookie: " + "; ".join(parts) + "\r\n") if parts else None
    except Exception:
        cookie_header = None
    if cookie_header:
        cmd = [ffmpeg, "-y", "-headers", cookie_header, "-i", stream_url, "-c", "copy", str(output_path)]
    else:
        cmd = [ffmpeg, "-y", "-i", stream_url, "-c", "copy", str(output_path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        return Path(output_path).exists()
    except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError):
        return False


def download_locals_stream_with_requests(
    stream_url: str,
    output_path: str,
    cookies_path: str | Path,
) -> bool:
    """Download a direct stream URL (e.g. m3u8 or mp4) using requests and Netscape cookies."""
    import http.cookiejar
    import os

    import requests

    path = Path(cookies_path)
    if not path.exists():
        return False
    jar = http.cookiejar.MozillaCookieJar(str(path))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception:
        return False
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    try:
        with requests.Session() as s:
            s.cookies = jar
            s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
            r = s.get(stream_url, stream=True, timeout=60)
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception:
        return False


def ensure_locals_cookies() -> bool:
    """If Locals credentials are set and cookie file is missing or invalid, run login and save cookies."""
    if not config.LOCALS_EMAIL or not config.LOCALS_PASSWORD:
        return False
    from locals_auth import login_and_save_cookies

    path = Path(config.LOCALS_COOKIES_PATH)
    if path.exists() and path.stat().st_size > 200:
        # Assume cookies might still be valid
        return True
    # Need to log in (cookie file missing or too small)
    ok = login_and_save_cookies(
        config.LOCALS_EMAIL,
        config.LOCALS_PASSWORD,
        path,
        headless=True,
    )
    return ok
