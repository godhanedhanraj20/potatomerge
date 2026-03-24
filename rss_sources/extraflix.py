import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import asyncio
from urllib.parse import urlparse
from config import EXTRAFLIX_CHANNEL_ID, PROXIES, HEADER

logger = logging.getLogger(__name__)


def clean_movie_title(title):
    """
    Remove trailing '- Extraflix' (with optional spaces/dashes), case-insensitive.
    """
    return re.sub(r"\s*[-–—]\s*Extraflix\s*$", "", (title or ""), flags=re.IGNORECASE).strip()


def scrape_extraflix(html_content, skip_already_sent=True):
    """
    Parses extraflix.blog listing HTML and scrapes entries. For each entry, fetch its detail page,
    extract the movie title and versions with resolved API links.
    """
    from modules.db import already_sent, mark_as_sent  # runtime import to avoid cycles

    movies = []
    soup = BeautifulSoup(html_content, "html.parser")

    # If this is a detail page (no listing cards), build directly
    articles = soup.find_all("article", class_="entry-card")
    if not articles:
        info = scrape_extraflix_detail(html_content)
        if info:
            movies.append(info)
        return movies

    for article in articles:
        h2 = article.find("h2", class_="entry-title")
        if not h2:
            continue
        a_tag = h2.find("a", href=True)
        if not a_tag:
            continue

        detail_url = a_tag["href"].strip()
        listing_title = a_tag.get_text(strip=True)
        img_tag = article.find("img")
        image_url = img_tag["src"].strip() if img_tag and img_tag.has_attr("src") else ""
        time_tag = article.find("time", class_="ct-meta-element-date")
        post_date = time_tag.get_text(strip=True) if time_tag else ""

        if skip_already_sent and already_sent(detail_url):
            logger.info(f"Already sent, skipping: {detail_url}")
            continue

        try:
            # use proxy + browser-like headers if configured for extraflix
            detail_resp = requests.get(
                detail_url,
                timeout=15,
                headers=HEADER,
                proxies=PROXIES,
            )
            detail_resp.raise_for_status()
            detail_html = detail_resp.text

            info = scrape_extraflix_detail(detail_html)
            movie_title = info.get("movie_title", "") if info else ""
            versions = info.get("versions", []) if info else []
        except Exception as e:
            logger.error(f"Failed to fetch details from {detail_url}: {e}", exc_info=True)
            movie_title = ""
            versions = []

        if not versions:
            continue

        movie_info = {
            "listing_title": listing_title,
            "detail_url": detail_url,
            "movie_title": movie_title,
            "post_date": post_date,
            "image_url": image_url,
            "versions": versions,
        }

        if skip_already_sent:
            mark_as_sent(
                detail_url,
                movie_title,
                sent_time=time.time(),
                listing_title=listing_title,
                post_date=post_date,
            )

        movies.append(movie_info)

    return movies

def scrape_extraflix_detail(detail_html):
    """
    Build a single movie_info entry from an Extraflix detail page HTML.
    """
    movie_title = extract_extraflix_movie_title(detail_html)
    download_links = extract_extraflix_download_links(detail_html)

    versions = []
    for dl in download_links:
        raw_url = (dl.get("url") or "").strip()

        # Only attempt API conversion for valid http(s) URLs
        if not re.match(r"^https?://", raw_url):
            logger.debug(f"Skipping non-http download URL for API conversion: {raw_url}")
            continue

        # Convert known extralink share URLs to API endpoints
        if "/api/s/" in raw_url:
            api_url = raw_url
        elif re.search(r"extralink\.ink/s/", raw_url):
            api_url = re.sub(r"/s/", "/api/s/", raw_url, count=1)
        else:
            # Unknown pattern; skip API call
            logger.debug(f"Unrecognized extralink pattern, skipping API call: {raw_url}")
            continue

        api_links = extract_links_from_api(api_url)
        if not api_links:
            continue

        version_entry = {
            "title": f"{dl.get('quality', '').strip()} ({dl.get('size', '').strip()})",
            "urls": api_links,
        }
        versions.append(version_entry)

    if not versions:
        return None

    return {
        "listing_title": movie_title,
        "detail_url": "",
        "movie_title": movie_title,
        "post_date": "",
        "image_url": "",
        "versions": versions,
    }


def extract_extraflix_movie_title(html_content):
    """
    Extract movie/show title from detail page HTML by first checking
    <h1 class="entry-title"> tag, fallback to <title> tag with 'Full Movie Download' suffix removed.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    h1 = soup.find("h1", class_="entry-title")
    if h1:
        return h1.get_text(strip=True)
    title_tag = soup.find("title")
    if title_tag:
        return re.sub(r"\s+Full Movie Download$", "", title_tag.get_text(strip=True), flags=re.I)
    return ""


def extract_extraflix_download_links(detail_html):
    """
    Parse detail page HTML to extract download qualities, sizes, and direct URLs.
    Returns list of dicts: [{"quality":..., "size":..., "url":...}, ...]
    """
    soup = BeautifulSoup(detail_html, "html.parser")
    downloads = []
    paragraphs = soup.find_all("p")
    for p in paragraphs:
        text = p.get_text(separator=" ", strip=True)
        m = re.match(r"^(.*?)\s*[–-]\s*\[(.*?)\]", text)
        if not m:
            continue
        quality = m.group(1).strip()
        size = m.group(2).strip()
        a = p.find_next("a", href=True, string=re.compile(r"download link", re.I))
        if a:
            url = a["href"].strip()
            # unwrap [http://...] or (http://...) patterns into plain URL
            url = re.sub(r"^\[?(https?://[^\]\s]+)\]?$", r"\1", url)
            url = re.sub(r"^\((https?://[^)]+)\)$", r"\1", url)
            downloads.append({"quality": quality, "size": size, "url": url})
    return downloads


def extract_links_from_api(api_url):
    """
    Fetch API JSON and extract relevant streaming/download links.
    Returns dict mapping host keys to URLs.

    Supports both:
    - Old schema with `driveLinks` list and *Link fields.
    - New extralink endpoint that exposes Google Drive via
      POST https://new2.extralink.ink/api/s/<code>/download
      with payload {"driveIndex": "0"} returning `driveLink.webViewLink`.
    """
    api_url_str = str(api_url or "").strip()
    parsed = urlparse(api_url_str)
    if parsed.scheme not in {"http", "https"}:
        logger.debug(f"Skipping API fetch due to invalid/missing URL scheme: {api_url_str}")
        return {}

    common_kwargs = {
        "timeout": 15,
        "headers": HEADER,
        "proxies": PROXIES,
    }

    links = {}

    try:
        # 1) Always try to GET the original API URL first.
        #    This is where non-drive hosts (hubcloud/gofile/etc) usually live.
        try:
            resp_main = requests.get(api_url_str, **common_kwargs)
            resp_main.raise_for_status()
            data_main = resp_main.json()
        except Exception as e:
            logger.debug(f"Primary API GET failed for {api_url_str}: {e}")
            data_main = {}

        # Extract non-drive hosts and old-style driveLinks from main response
        if isinstance(data_main, dict):
            drive_links = data_main.get("driveLinks", [])
            if isinstance(drive_links, list) and drive_links:
                links.setdefault("google_drive", [])
                for d in drive_links:
                    web_view = (d or {}).get("webViewLink")
                    if web_view:
                        links["google_drive"].append(web_view)

            keys_of_interest = [
                "gdtotLink",
                "filepressLink",
                "gofileLink",
                "vikingLink",
                "photoLink",
                "r2Link",
                "abyssPlayerLink",
                "hubcloudLink",
                "pixeldrainLink",
            ]
            for key in keys_of_interest:
                url = data_main.get(key)
                if url:
                    simple_key = key.replace("Link", "").lower()
                    links[simple_key] = url

        # 2) For extralink.ink, additionally POST the /download endpoint
        #    to expose driveLink.webViewLink.
        if "extralink.ink" in (parsed.netloc or "").lower():
            m = re.search(r"/api/s/([^/]+)", parsed.path)
            if m:
                code = m.group(1)
                download_url = f"{parsed.scheme}://{parsed.netloc}/api/s/{code}/download"
            else:
                # If the given URL is already a /download endpoint, use it directly.
                download_url = api_url_str if parsed.path.endswith("/download") else None

            if download_url:
                try:
                    resp_dl = requests.post(
                        download_url,
                        json={"driveIndex": "0"},
                        **common_kwargs,
                    )
                    resp_dl.raise_for_status()
                    data_dl = resp_dl.json()
                except Exception as e:
                    logger.debug(f"Download API POST failed for {download_url}: {e}")
                    data_dl = {}
                if isinstance(data_dl, dict):
                    drive_link_obj = data_dl.get("driveLink")
                    if isinstance(drive_link_obj, dict):
                        web_view = drive_link_obj.get("webViewLink")
                        if web_view:
                            links.setdefault("google_drive", [])
                            links["google_drive"].append(web_view)

        # Deduplicate google_drive links if multiple sources filled them
        if "google_drive" in links and isinstance(links["google_drive"], list):
            seen = set()
            deduped = []
            for u in links["google_drive"]:
                if u and u not in seen:
                    deduped.append(u)
                    seen.add(u)
            links["google_drive"] = deduped

        return links
    except requests.exceptions.MissingSchema:
        logger.debug(f"Skipping API fetch due to MissingSchema: {api_url_str}")
        return {}
    except requests.exceptions.InvalidURL:
        logger.debug(f"Skipping API fetch due to InvalidURL: {api_url_str}")
        return {}
    except Exception as e:
        logger.error(f"Failed to fetch/parse API data from {api_url_str}: {e}", exc_info=True)
        return {}


def create_telegram_message(movie_main_title, versions, max_versions=None):
    """
    Create Telegram HTML message with the movie title and up to max_versions versions.
    If a movie has no versions, it should not be sent.
    """
    if not versions or len(versions) == 0:
        return None

    # Clean "- Extraflix" or similar from title
    clean_title = clean_movie_title(movie_main_title)

    msg = "🎬 New Post Just Dropped! ✅\n\n"
    msg += f"📌 <b>{clean_title}</b>\n\n"

    num_versions = len(versions) if max_versions is None else min(len(versions), max_versions)

    for idx, version in enumerate(versions[:num_versions], start=1):
        version_title = version.get("title", "No Title")
        urls = version.get("urls", {})
        if not urls:
            continue

        msg += f"{idx}. <b>{version_title}</b>\n"
        for host_key, host_name in [
            ("hubcloud", "HubCloud"),
            ("viking", "Viking File"),
            ("gdtot", "GDTot"),
            ("filepress", "FilePress"),
            ("google_drive", "Google Drive"),
            ("gofile", "GoFile"),
            ("photo", "DotFlix"),
            ("r2", "R2"),
            ("abyssplayer", "Abyss Player"),
            ("pixeldrain", "PixelDrain"),
        ]:
            url = urls.get(host_key)
            if host_key == "google_drive" and isinstance(url, list):
                if url:
                    gdlink = url[0]
                    msg += f"• <b>{host_name}:</b> <a href=\"{gdlink}\">Click Here</a>\n"
            elif url:
                msg += f"• <b>{host_name}:</b> <a href=\"{url}\">Click Here</a>\n"
        msg += "\n"

    msg += '<blockquote>Powered By <a href="https://t.me/+2Z8xk1s1C944MmI1">Downloader Zone</a></blockquote>'
    return msg


async def send_extraflix_messages(client, movies):
    """
    Async function to send telegram messages for new movies with extracted info.
    Only sends movies that have versions (links).
    """
    for movie_info in movies:
        msg = create_telegram_message(movie_info.get("movie_title", "N/A"), movie_info.get("versions", []))
        if not msg:
            continue  # Skip if no valid versions

        await client.send_message(
            chat_id=EXTRAFLIX_CHANNEL_ID,
            text=msg,
            parse_mode="html",
            disable_web_page_preview=True
        )
        await asyncio.sleep(10)