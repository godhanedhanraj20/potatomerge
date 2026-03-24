import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import asyncio
from config import SKYMOVIES_CHANNEL_ID

logger = logging.getLogger(__name__)

def scrape_skymovies(html_content, skip_already_sent=True):
    """
    Parses the main listing page HTML content and scrapes movie listings.
    For each movie detail URL, fetches detail page and extracts info and links.
    Skips already sent movies if skip_already_sent=True.

    If given a detail page HTML (no listing blocks), returns a single movie_info entry.
    """
    from modules.db import already_sent, mark_as_sent

    movies = []
    soup = BeautifulSoup(html_content, "html.parser")

    # If this is a detail page (no listing blocks), build directly
    movie_divs = soup.find_all("div", class_="Fmvideo", align="left")
    if not movie_divs:
        info = scrape_skymovies_detail(html_content)
        if info:
            movies.append(info)
        return movies

    for div in movie_divs:
        b_tag = div.find("b")
        if not b_tag:
            continue
        a_tag = b_tag.find("a", href=True)
        if not a_tag:
            continue

        href = a_tag['href']
        listing_title = a_tag.get_text(strip=True)
        clean_href = href.strip("[]")
        if clean_href.startswith("http"):
            detail_url = clean_href
        else:
            detail_url = f"https://skymovieshd.credit/{clean_href.lstrip('/')}"

        if skip_already_sent and already_sent(detail_url):
            logger.info(f"Already sent, skipping: {detail_url}")
            continue

        try:
            resp = requests.get(detail_url, timeout=15)
            resp.raise_for_status()
            detail_html = resp.text
            movie_title, size = extract_movie_info(detail_html)
            google_drive_links = extract_google_drive_direct_links_from_html(detail_html)
            all_server_links = extract_all_howblogs_links(detail_html)
        except Exception as e:
            logger.error(f"Fetch/detail extract error {detail_url}: {e}", exc_info=True)
            movie_title = ""
            size = "Unknown"
            google_drive_links = []
            all_server_links = []

        movie_info = {
            "listing_title": listing_title,
            "detail_url": detail_url,
            "movie_title": movie_title,
            "size": size,
            "google_drive_links": google_drive_links,
            "all_server_links": all_server_links
        }

        if skip_already_sent:
            mark_as_sent(
                detail_url,
                movie_title,
                size=size,
                sent_time=time.time(),
                google_drive_links=google_drive_links,
                all_server_links=all_server_links,
                listing_title=listing_title
            )

        movies.append(movie_info)

    return movies

def scrape_skymovies_detail(detail_html):
    """
    Build a single movie_info entry from a Skymovies detail page HTML.
    """
    movie_title, size = extract_movie_info(detail_html)
    google_drive_links = extract_google_drive_direct_links_from_html(detail_html)
    all_server_links = extract_all_howblogs_links(detail_html)

    return {
        "listing_title": movie_title,
        "detail_url": "",
        "movie_title": movie_title,
        "size": size,
        "google_drive_links": google_drive_links,
        "all_server_links": all_server_links
    }


def extract_movie_info(html_content):
    """
    Extracts movie title and size from a movie detail page HTML.

    Returns:
        (title, size) tuple (both strings)
    """
    soup = BeautifulSoup(html_content, "html.parser")
    title_tag = soup.find("title")
    title_text = ""
    if title_tag:
        title_text = title_tag.text.strip()
        # Remove trailing "Full Movie Download" if present
        title_text = re.sub(r'\s+Full Movie Download$', '', title_text, flags=re.I).strip()

    size = "Unknown"
    size_divs = soup.find_all("div", class_="Let")
    for div in size_divs:
        b_tag = div.find("b")
        if b_tag and "Size" in b_tag.text:
            size_text = div.text.replace(b_tag.text, "").strip()
            if size_text:
                size = size_text
            break

    if size == "Unknown":
        bracket_search = re.search(r'\[(\d+\.?\d*\s*[GMK]B)\]', title_text, re.I)
        if bracket_search:
            size = bracket_search.group(1)

    return title_text, size


def extract_google_drive_direct_links_from_html(html_content):
    """
    Extracts Google Drive Direct Links URLs from the movie detail page HTML.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        if "google drive direct links" in text:
            href = a['href']
            match = re.search(r"\((https?://[^\)]+)\)", href)
            url = match.group(1) if match else href.strip("[]")
            if url and url.startswith("http") and url not in links:
                links.append(url)
    return links 
    
def extract_all_howblogs_links(html_content):
    """
    Extract all howblogs.xyz URLs except those with anchor text
    'WATCH ONLINE' or '1080p WEB-DL LINK' (case insensitive).

    Args:
        html_content (str): HTML string of movie detail page.

    Returns:
        list of str: Filtered howblogs.xyz URLs.
    """
    excluded_texts = {"watch online", "1080p web-dl link"}
    soup = BeautifulSoup(html_content, "html.parser")
    filtered_links = []

    for a_tag in soup.find_all("a", href=True):
        link_text = a_tag.get_text(strip=True).lower()
        href = a_tag['href']
        # Get direct link within possible markdown-like wrapping
        match = re.search(r"\((https?://[^\)]+)\)", href)
        url = match.group(1).strip() if match else href.strip("[]").strip()
        if url.startswith("https://howblogs.xyz/"):
            if link_text not in excluded_texts and url not in filtered_links:
                filtered_links.append(url)
    return filtered_links

def extract_host_links_from_howblogs(howblogs_url):
    """
    Fetches the Howblogs.xyz page and extracts links grouped by host:
    - gofile (gofile.io)
    - vikingfile
    - streamtape
    - gdflix (gdflix, gdlink)
    - hubcloud

    Returns:
        dict of host keys -> list of URLs
    """
    hosts = {
        "gofile": "gofile.io",
        "vikingfile": "vikingfile",
        "streamtape": "streamtape",
        "gdflix": ["gdflix", "gdlink"],
        "hubcloud": "hubcloud"
    }
    extracted = {key: [] for key in hosts.keys()}

    try:
        resp = requests.get(howblogs_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            href_low = a_tag['href'].strip().lower()
            href_orig = a_tag['href'].strip()
            for key, domain in hosts.items():
                if isinstance(domain, list):
                    if any(d in href_low for d in domain):
                        if href_orig not in extracted[key]:
                            extracted[key].append(href_orig)
                else:
                    if domain in href_low:
                        if href_orig not in extracted[key]:
                            extracted[key].append(href_orig)

    except Exception as e:
        logger.error(f"Failed to extract host links from {howblogs_url}: {e}", exc_info=True)

    return extracted


def skymovies_message_template(movie_info, host_links_dict=None):
    """
    Generates a Telegram message formatted like the example UI:
    Title, followed by groups like GoFile Link, Stream Tape Link, and All Cloud Links.

    Args:
        movie_info (dict): Movie info with keys like 'movie_title', 'size', 'detail_url'
        host_links_dict (dict): Dict with host keys mapped to list of URLs.

    Returns:
        str: Formatted message string with HTML tags
    """
    # Header with title and size
    msg = f"<b>🎬 New Post Just Dropped! ✅</b>\n\n"
    msg += f"📌 <b>{movie_info.get('movie_title','N/A')}</b>\n\n"
    
    # GoFile Link section
    gofile_links = host_links_dict.get("gofile", []) if host_links_dict else []
    if gofile_links:
        msg += "<blockquote><b>🔰GoFile Link🔰</b></blockquote>\n"
        for link in gofile_links:
            msg += f"• <a href=\"{link}\">{link}</a>\n"
        msg += "\n"
    
    # Stream Tape Link section
    streamtape_links = host_links_dict.get("streamtape", []) if host_links_dict else []
    if streamtape_links:
        msg += "<blockquote><b>🐬Stream Tape Link🐬</b></blockquote>\n"
        for link in streamtape_links:
            msg += f"• <a href=\"{link}\">{link}</a>\n"
        msg += "\n"
    
    # All Cloud Links section — grouping rest of hosts except gofile and streamtape
    if host_links_dict:
        # Collect all other hosts except gofile and streamtape
        other_hosts = {k: v for k, v in host_links_dict.items() if k not in ("gofile", "streamtape")}
        if any(other_hosts.values()):  # at least one non-empty list
            msg += "<blockquote><b>♻️All Cloud Links♻️</b></blockquote>\n"
            for host, links in other_hosts.items():
                if links:
                    for link in links:
                        msg += f"• <a href=\"{link}\">{link}</a>\n"
            msg += "\n"
    
    # Add footer or branding if you want
    msg += '<blockquote>Powered By <a href="https://t.me/+_sbKyI81UI1hODhh">Downloader Zone</a></blockquote>'
    
    return msg


async def send_movie_with_expanded_hosts(client, movie_info):
    """
    Asynchronously fetch host links for each Howblogs link in movie_info,
    aggregate and deduplicate them, then send a formatted message.
    """
    loop = asyncio.get_event_loop()
    host_links_aggregate = {
        "gofile": [],
        "vikingfile": [],
        "streamtape": [],
        "gdflix": [],
        "hubcloud": []
    }

    for howblogs_link in movie_info.get("all_server_links", []):
        host_links = await loop.run_in_executor(None, extract_host_links_from_howblogs, howblogs_link)
        for host_key in host_links_aggregate.keys():
            host_links_aggregate[host_key].extend(host_links.get(host_key, []))

    # Deduplicate links per host group while preserving order
    for host_key in host_links_aggregate:
        seen = set()
        filtered = []
        for link in host_links_aggregate[host_key]:
            if link not in seen:
                filtered.append(link)
                seen.add(link)
        host_links_aggregate[host_key] = filtered

    msg = skymovies_message_template(movie_info, host_links_dict=host_links_aggregate)

    await client.send_message(
        chat_id=SKYMOVIES_CHANNEL_ID,
        text=msg,
        parse_mode="html",
        disable_web_page_preview=True
    )