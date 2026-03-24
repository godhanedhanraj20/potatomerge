import requests
import logging
from bs4 import BeautifulSoup

from modules.skymovies import (
    scrape_skymovies,
    skymovies_message_template,
    extract_movie_info,
    extract_google_drive_direct_links_from_html,
    extract_all_howblogs_links,
    extract_host_links_from_howblogs,
)
from modules.extraflix import scrape_extraflix, create_telegram_message
from modules.uindex import extract_magnet_title_size

logger = logging.getLogger(__name__)

def dispatch_link_by_domain(url: str) -> str:
    """
    Determines which scraper module to use based on the URL's domain.

    Returns:
        str: Handler name ('skymovies', 'uindex', 'extraflix', or 'unknown').
    """
    url_lower = url.lower()
    if "skymovieshd" in url_lower or "skymovies" in url_lower or "skymovies.mba" in url_lower or "skymovieshd.mba" in url_lower:
        return "skymovies"
    elif "uindex.org" in url_lower:
        return "uindex"
    elif "extraflix" in url_lower:
        return "extraflix"
    else:
        return "unknown"

def process_link(url: str, telegram_client=None, channel_id=None, skip_already_sent=True, max_versions=3):
    """
    Process a single URL by dispatching to the correct handler/module.
    If telegram_client and channel_id are provided, sends the processed data to channel.
    """
    handler = dispatch_link_by_domain(url)

    if handler == "skymovies":
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            html = resp.text

            # Detect listing vs detail page
            soup = BeautifulSoup(html, "html.parser")
            listing_nodes = soup.find_all("div", class_="Fmvideo", align="left")

            if listing_nodes:
                movies = scrape_skymovies(html, skip_already_sent=skip_already_sent)
                for movie in movies:
                    if telegram_client and channel_id:
                        msg = skymovies_message_template(movie)
                        telegram_client.send_message(
                            chat_id=channel_id,
                            text=msg,
                            parse_mode="html"
                        )
                    else:
                        return movie
                return None
            else:
                # Detail page handling
                title, size = extract_movie_info(html)
                google_drive_links = extract_google_drive_direct_links_from_html(html) or []
                all_server_links = extract_all_howblogs_links(html) or []

                movie_info = {
                    "listing_title": title,
                    "detail_url": url,
                    "movie_title": title,
                    "size": size,
                    "google_drive_links": google_drive_links,
                    "all_server_links": all_server_links
                }

                # Aggregate host links from howblogs pages
                host_links_aggregate = {
                    "gofile": [],
                    "vikingfile": [],
                    "streamtape": [],
                    "gdflix": [],
                    "hubcloud": []
                }
                for how_url in all_server_links:
                    host_links = extract_host_links_from_howblogs(how_url)
                    for key in host_links_aggregate.keys():
                        host_links_aggregate[key].extend(host_links.get(key, []))
                # Deduplicate while preserving order
                for key in host_links_aggregate:
                    seen = set()
                    deduped = []
                    for link in host_links_aggregate[key]:
                        if link not in seen:
                            deduped.append(link)
                            seen.add(link)
                    host_links_aggregate[key] = deduped

                msg = skymovies_message_template(movie_info, host_links_dict=host_links_aggregate)

                if telegram_client and channel_id:
                    telegram_client.send_message(
                        chat_id=channel_id,
                        text=msg,
                        parse_mode="html"
                    )
                    return None
                else:
                    return movie_info

        except Exception as e:
            logger.error(f"Error processing skymovies link: {e}", exc_info=True)
            return None

    elif handler == "uindex":
        try:
            magnet, title, size = extract_magnet_title_size(url)
            info = {"magnet": magnet, "title": title, "size": size}
            if telegram_client and channel_id:
                msg_text = (
                    f"📀 <b>{title}</b>\n"
                    f"<b>Size:</b> <code>{size}</code>\n\n"
                    f"🧲 <b>Magnet:</b>\n"
                    f"<code>{magnet}</code>"
                )
                telegram_client.send_message(
                    chat_id=channel_id,
                    text=msg_text,
                    parse_mode="html"
                )
            else:
                return info
            return None
        except Exception as e:
            logger.error(f"Error processing uindex link: {e}", exc_info=True)
            return None

    elif handler == "extraflix":
        try:
            from config import HEADER
            resp = requests.get(url, timeout=20, headers=HEADER)
            resp.raise_for_status()
            html = resp.text
            movies = scrape_extraflix(html, skip_already_sent=skip_already_sent)
            for movie in movies:
                # Only send movies that have versions (links))
                msg = create_telegram_message(
                    movie.get("movie_title", "N/A"), 
                    movie.get("versions", []),
                    max_versions=max_versions
                )
                if not msg:
                    continue
                if telegram_client and channel_id:
                    telegram_client.send_message(
                        chat_id=channel_id,
                        text=msg,
                        parse_mode="html",
                        disable_web_page_preview=True,
                    )
                else:
                    return movie
            return None
        except Exception as e:
            logger.error(f"Error processing extraflix link: {e}", exc_info=True)
            return None

    else:
        logger.warning(f"No handler found for: {url}")
        return None

def process_links(links, telegram_client=None, channel_id=None, skip_already_sent=True, max_versions=3):
    """
    Process a list of URLs, dispatching each to the appropriate handler.
    """
    for link in links:
        process_link(link, telegram_client=telegram_client, channel_id=channel_id, skip_already_sent=skip_already_sent, max_versions=max_versions)