import requests
import logging
import re
import urllib.parse
from bs4 import BeautifulSoup
from config import HEADER

logger = logging.getLogger(__name__)

def extract_magnet_title_size(detail_url):
    try:
        r = requests.get(detail_url, headers=HEADER, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        title = None
        h1 = soup.find("h1")
        if h1 and h1.text.strip():
            title = h1.text.strip()
        else:
            dbox = soup.find(id="downloadbox")
            if dbox:
                p = dbox.find("p")
                if p and p.text.strip():
                    title = p.text.strip()
        
        magnet = None
        box = soup.find("div", id="downloadbox")
        if box:
            a_tag = box.find("a", href=lambda h: h and h.startswith("magnet:"))
            if a_tag:
                magnet = re.sub(r"\s+", "", a_tag['href'])
        
        size = "Unknown"
        size_strong = soup.find("strong", string=re.compile(r"Total size:"))
        if size_strong:
            next_sib = size_strong.next_sibling
            if next_sib:
                size = next_sib.strip()
        
        if not title and magnet:
            regexp = re.search(r"dn=([^&]+)", magnet)
            if regexp:
                title = urllib.parse.unquote(regexp.group(1))
            else:
                title = "Torrent"
        elif not title:
            title = "Torrent"
        
        return magnet, title, size
    except requests.RequestException as e:
        logger.error(f"Request failed for {detail_url}: {e}")
    except Exception as e:
        logger.error(f"Extracting magnet/title/size failed for {detail_url}: {e}", exc_info=True)
    return None, "Torrent", "Unknown"

def get_new_details(search_url, last_tid):
    try:
        r = requests.get(search_url, headers=HEADER, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        a_tags = soup.find_all("a", href=lambda h: h and "details.php?id=" in h)
        new_items = []
        for a_tag in a_tags:
            match = re.search(r"id=(\d+)", a_tag['href'])
            if match:
                tid = match.group(1)
                if tid == last_tid:
                    break  # Stop at the last known tid (assuming newest first)
                detail_url = f"https://uindex.org/details.php?id={tid}"
                new_items.append((tid, detail_url))
        # If last_tid not found, return all items as new
        if not new_items and a_tags:
            for a_tag in a_tags:
                match = re.search(r"id=(\d+)", a_tag['href'])
                if match:
                    tid = match.group(1)
                    detail_url = f"https://uindex.org/details.php?id={tid}"
                    new_items.append((tid, detail_url))
        return new_items
    except requests.RequestException as e:
        logger.error(f"Request failed for {search_url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Scraping failed on {search_url}: {e}")
        return []

def get_first_detail(search_url):
    try:
        r = requests.get(search_url, headers=HEADER, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        a_tag = soup.find("a", href=lambda h: h and "details.php?id=" in h)
        if a_tag:
            match = re.search(r"id=(\d+)", a_tag['href'])
            if match:
                tid = match.group(1)
                detail_url = f"https://uindex.org/details.php?id={tid}"
                return tid, detail_url
        return None, None
    except requests.RequestException as e:
        logger.error(f"Request failed for {search_url}: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Scraping failed on {search_url}: {e}")
        return None, None