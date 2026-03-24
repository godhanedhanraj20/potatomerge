import re, requests, cloudscraper, base64, time, random

from re import sub, match
from urllib.parse import urlparse, quote, parse_qs
from bs4 import BeautifulSoup, NavigableString, Tag
from cloudscraper import create_scraper
from zenrows import ZenRowsClient

from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.mirror_utils.download_utils.direct_link_generator import *

def convert_time(seconds):
    mseconds = seconds * 1000
    periods = [("d", 86400000), ("h", 3600000), ("m", 60000), ("s", 1000), ("ms", 1)]
    result = ""
    for name, secs in periods:
        if mseconds >= secs:
            val, mseconds = divmod(mseconds, secs)
            result += f"{int(val)}{name}"
    return result or "0ms"

def is_excep_link(url):
    return bool(
        match(
            r"https?:\/\/.+\.(1tamilmv|tamilblasters|5movierulz|gdtot|filepress|pressbee|gdflix|sharespark)\.\S+|https?:\/\/(sharer|hdhub4u|filmyfly|onlystream|hubdrive|katdrive|drivefire|skymovieshd|toonworld4all|kayoanime|cinevood|gdflix|filepress|pressbee|filebee|appdrive)\.\S+",
            url,
        )
    )
    
olamovies_cookies = {
    '_ga': 'GA1.1.418851993.1748631702',
    'G_ENABLED_IDPS': 'google',
    '_ga_CKLGQZ7M2L': 'GS2.1.s1748631702$o1$g1$t1748631704$j58$l0$h0'
}

drive_ola_cookies_raw = [
    {
        "domain": "drive.olamovies.download",
        "hostOnly": True,
        "httpOnly": True,
        "name": "__Host-next-auth.csrf-token",
        "path": "/",
        "sameSite": "lax",
        "secure": True,
        "session": True,
        "storeId": None,
        "value": "af123fd026ba1ea680080fc96398262b87dc53631751fa718db33aacb398d715%7C36f2fd30bb05818e5cb58cb9467cb0239af78632c60e3d27996ca0e42c291350"
    },
    {
        "domain": "drive.olamovies.download",
        "hostOnly": True,
        "httpOnly": True,
        "name": "__Secure-next-auth.callback-url",
        "path": "/",
        "sameSite": "lax",
        "secure": True,
        "session": True,
        "storeId": None,
        "value": "https%3A%2F%2Fdrive.olamovies.download"
    },
    {
        "domain": "drive.olamovies.download",
        "expirationDate": 1748772804.860235,
        "hostOnly": True,
        "httpOnly": True,
        "name": "__Secure-next-auth.session-token",
        "path": "/",
        "sameSite": "lax",
        "secure": True,
        "session": False,
        "storeId": None,
        "value": "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..9kN0-OPsWpD4QGxe.M7xBx3UDEJND_KVXIQGqe7UXBlUdGpvQ_RhaLBdvfSqkXBOJmErJY6E2Vuj3rNmNmVp7F3XaLLRH6N5IuTvcZ6kGTdnK0ApcsHSUZ9SO-bZkYLmKlVWekzTiS_6Wjr_mIDrMemC6YHTGYK76RoEvzbrKHgHMmdGdzy7M01lLX-WSn_nO3Phx0_dee1NbwzI-eHqYk0ayoIvfx0Dar257WUqv7q6QEIoRF6bOsAynjL3gSUiTsRAzYHhVepp8f4T_YYeOd1p29YrU7NXcVv6feAEBHoKqLXZyBA4Es7qqdO_jzpaiddnHiWV6dp15uVj3WLC5XURr1gvwDHT11Rltyd8XIEgRVI6SzX5tbX3v5RD2wB7QRvfHl-EbLdvYkHlA9K62uq6DUL6ywcAxucRo4cfhn20ppGh-LaW-VKedXWnUzPXSTDkcOU-7ra_vnOzZQ1SBRNaHq7ekoWfJ4HzDqvVQatLvofgKuXhW7tqVAbz_3Nh9oo8Ry-O79pGwpgpkEVHCDn4aKFMImT3Ix9RW-9aaHYzp8xX8IhRbd668hi7-ir0MqQ_2HePPfzCU-WZFFW4.0m5SOarKpDRz3d0_86BrZg"
    }
]

drive_ola_cookies = {i['name']: i['value'] for i in drive_ola_cookies_raw}

def olam_generate(url):
    cook = '; '.join([f"{key}={value}" for key, value in olamovies_cookies.items()])
    headers = {"Cookie": cook}
    params = {"js_render": "true"}
    zen_cli = ZenRowsClient("6c0607809e2b6b8de97bb3f5f1f2b5d08b6a644a")
    res = zen_cli.get(url, headers=headers, params=params)
    if "Login is Required" in res.text:
        raise Exception('ERROR: Cookies Expired !')
    soup = BeautifulSoup(res.text, 'html.parser')
    button = soup.find('button')
    script = button.find_next('script')
    decoded = script.text
    encoded_url = re.search(r'\"(aHR0[^\"]+)\"', decoded).group(1)
    link = base64.b64decode(encoded_url).decode('utf-8')
    link = direct_link_generator(link)
    client = cloudscraper.create_scraper(allow_brotli=False)
    cget = client.request
    verify_link = link

    def bypass_verify(link):
        cd_ = link.split('/')[-1]
        cget('GET', "https://drive.olamovies.download/api/auth/session")
        headers = {
            'origin': 'https://drive.olamovies.download',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'sec-fetch-site': 'same-origin',
        }
        respxxx = cget('POST', "https://drive.olamovies.download/api/verify", json={'id': cd_}, headers=headers)
        cd_ = respxxx.json()['id']
        link = f"https://drive.olamovies.download/file/{cd_}"
        return link

    link = bypass_verify(link)
    res_ = client.get(link, cookies=drive_ola_cookies)
    match = re.search(r',\\\"driveId\\\":\\\"([^\\"]+)\\\"', res_.text)
    if not match:
        return bypass_verify(verify_link)
    drive_id = match.group(1)
    res = client.get(f"{DIRECT_URL}info.aspx?id={drive_id}").json()
    if res.get('error'):
        return bypass_verify(verify_link)
    link = f"{DIRECT_URL}direct.aspx?id={drive_id}"
    d_link = f"https://drive.google.com/uc?id={drive_id}"
    return d_link

def tamilblasters(url):
    try:
        resp = cloudscraper.create_scraper().get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = [(a.text.strip(), a["href"]) for a in soup.find_all("a", href=True) if a["href"].startswith("magnet:?xt=urn:btih:")]
        out = f"<b><u>{soup.title.string.strip()}</u></b>"
        for i, (title, link) in enumerate(links, 1):
            title = sub(r"www\S+|\- |\.torrent", "", title)
            title = sub(r"\s+", " ", title).strip()
            if "&dn" in link:
                link = link.split("&dn")[0] + "&dn"
            out += f"\n\n<b>{i}. {title}</b>\n<b>🌐 Torrent Link :</b> <code>{link}</code>"
        return out.strip()
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in tamilblasters: {str(e)}")

def movierulz(url):
    try:
        resp = cloudscraper.create_scraper().get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = [(a.text.strip(), a["href"]) for a in soup.find_all("a", href=True) if a["href"].startswith("magnet:?xt=urn:btih:")]
        out = f"<b><u>{soup.title.string.strip()}</u></b>"
        for i, (title, link) in enumerate(links, 1):
            title = sub(r"www\S+|\- |\.torrent", "", title)
            title = sub(r"\s+", " ", title).strip()
            if "&dn" in link:
                link = link.split("&dn")[0] + "&dn"
            out += f"\n\n<b>{i}. {title}</b>\n<b>🌐 Torrent Link :</b> <code>{link}</code>"
        return out.strip()
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in movierulz: {str(e)}")

def tamilmv(url):
    try:
        resp = create_scraper().get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        tor = soup.select('a[data-fileext="torrent"]')
        mag = soup.select('a[href^="magnet:?xt=urn:btih:"]')
        out = f"<b><u>{soup.title.string}</u></b>"
        for i, (t, _) in enumerate(zip(tor, mag), 1):
            name = sub(r"www\S+|\- |\.torrent", "", t.string)
            out += f"\n\n<b>{i}. {name}</b>\n<b>🌐 Torrent Link :</b> <code>{t['href']}</code>"
        return out
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in tamilmv: {str(e)}")

def sharespark(link):
    try:
        gd_txt = ""
        cget = create_scraper().request
        res = cget("GET", "?action=printpage;".join(link.split('?')))
        soup = BeautifulSoup(res.text, 'html.parser')
        gd_txt += f"☰ <i>{soup.title.text.replace('Print Page - ','')}</i>\n\n"
        for br in soup.findAll('br'): 
            next_s = br.nextSibling
            if not (next_s and isinstance(next_s, NavigableString)): 
                continue
            if (next2_s := next_s.nextSibling) and isinstance(next2_s, Tag) and next2_s.name == 'br' and str(next_s).strip():
                if re.match(r'^(480p|720p|1080p)(.+)? Links:\Z', next_s):
                    gd_txt += f'» <i>{next_s}</i>\n\n' 
                for s in next_s.split(): 
                    ns = re.sub(r'\(|\)', '', s)
                    if re.match(r'https?://(.+\.)?gdtot\.\S+', ns):
                        soup2 = BeautifulSoup(cget("GET", ns).text, "html.parser")
                        parse_data = (soup2.select('meta[property^="og:description"]')[0]['content']).replace('Download ' , '').rsplit('-', maxsplit=1)
                        gd_txt += f"┎ Name : <code>{parse_data[0]}</code>\n┠ Size : <code>{parse_data[-1]}<code>\n┖ GDTot : {ns}\n\n"
                    elif re.match(r'https?://pastetot\.\S+', ns):
                        nxt = re.sub(r'\(|\)|(https?://pastetot\.\S+)', '', next_s) 
                        gd_txt += f"\n» <i>{nxt}</i>\n┖ {ns}\n"
        if gd_txt != "": 
            return gd_txt.strip()
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in sharespark: {str(e)}")

def teluguflix(link):
    try:
        txt = ""
        soup = BeautifulSoup(requests.get(link).text, "html.parser")
        for a in soup.find_all("a"):
            u = a.get("href")
            if u and "gdtot" in u:
                soup2 = BeautifulSoup(requests.get(u).text, "html.parser")
                txt += f"<code>{soup2.title.text.replace('GDToT | ', '')}</code>\n{u}\n\n"
        return txt or "No links found."
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in teluguflix: {str(e)}")

def cinevood(link):
    try:
        out = ""
        soup = BeautifulSoup(requests.get(link).text, 'html.parser')
        for a in soup.select('a[href^="https://filepress"]'):
            u = a['href']
            soup2 = BeautifulSoup(requests.get(u).text, "html.parser")
            title = sub(r'Kolop \| ', '', soup2.title.text)
            out += f'{title}\n{u}\n\n'
        return out or "No links found."
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in cinevood: {str(e)}")

def skymovieshd(link):
    try:
        gd_txt = ""
        res = requests.get(link, allow_redirects=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        a = soup.select('a[href^="https://howblogs.xyz"]')
        a1 = soup.find_all("a", href=re.compile(r"^https://new\d{0,2}\.gdflix"))
        a11 = soup.select('a[href^="https://gdlink"]')
        a2 = soup.select('a[href^="https://hubcloud"]')
        t = soup.select('div[class^="Robiul"]')
        if not t:
            return "Title not found"
        gd_txt += f"☰ <i>{t[-1].text.replace('Download ', '')}</i>\n\n"
        if not a:
            if a1 + a11 + a2:
                pack, no = None, 1
                for link in a1 + a11 + a2:
                    if '/pack/' in link['href']:
                        pack = link
                        continue
                    gd_txt += f"{no}. <a href='{link['href']}'>{link.text}</a>\n"
                    no += 1
                if pack:
                    gd_txt += f"{no}. <a href='{pack['href']}'>{pack.text}</a>\n"
                return gd_txt.strip()
            else:
                return "Cant Find Links Here"
        nres = requests.get(a[0]['href'], allow_redirects=False)
        nsoup = BeautifulSoup(nres.text, 'html.parser')
        atag = nsoup.select('div[class="cotent-box"] > a[href]')
        for no, link in enumerate(atag, start=1):
            gd_txt += f"{no}. {link['href']}\n"
        return gd_txt.strip()
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in skymovieshd: {str(e)}")

def atishmkv(link):
    try:
        out = ""
        soup = BeautifulSoup(requests.get(link).text, 'html.parser')
        for a in soup.select('a[href^="https://gdflix.top/file"]'):
            out += a['href'] + '\n\n'
        return out or "No links found."
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in atishmkv: {str(e)}")

def toonworld4all(url):
    cookies , headers  = get_cf_clearance('https://links.toonworld4all.me/redirect')
    client = cloudscraper.create_scraper(allow_brotli = False)
    for i in range(10):
        cookies['redirect_index'] = str(i)
        response = client.post(
            f"{cf_cdn}headerloc" , data = {'url' : url , "cookies" : str(cookies) , "headers" : str(headers)}
        )
        link = response.text.strip()
        if any(x in link for x in ['link.pocolinks.com', 'm.easysky.in', 'gplinks.co']):
            return direct_link_generator(link)

def toonworld4allphp(url):
     client = cloudscraper.create_scraper(allow_brotli = False)
     response = client.get(f"{AWS_API}location?url={url}").json()
     links = response['links']
     for link in links:
         if any(x in link for x in ['link.pocolinks.com', 'm.easysky.in', 'gplinks.co']):
            return direct_link_generator(link)
             
def sextb(link , retry=0):
    client = create_scraper()
    rndm = random.randint(1, 100)
    proxies = {
        'http': f'http://iuhottnp-in-{rndm}:agybxhs8o5t8@p.webshare.io:80',
        'https' : f'http://iuhottnp-in-{rndm}:agybxhs8o5t8@p.webshare.io:80'
    }
    res = client.get(link , proxies = proxies)
    soup = BeautifulSoup(res.text, 'html.parser')
    if "Attention" in soup.title.text or "Just a moment" in soup.title.text:
        if retry >= 3:
            raise DirectDownloadLinkException('Too Many Retries, Please Try Again Later !')
        return sextb(link , retry = retry + 1)
    buttons = soup.find_all('button', class_=['btn-player' ,'episode' ])
    string = {}
    string['THUMB'] = soup.find('meta', property='og:image')['content'].split('?')[0] if soup.find('meta', property='og:image') else None
    for i in buttons:
        if i.text.strip() == 'ST':
            episode_id = i['data-id']
            film_id = i['data-source']
            resp = client.post("https://sextb.net/ajax/player" , data = {'episode' : episode_id , 'filmId' : film_id} , proxies = proxies).json()
            new_soup = BeautifulSoup(resp['player'], 'html.parser')
            video_link = new_soup.find('iframe')['src']
            string[i.text] = video_link.split('?thumb')[0]
        if i.text.strip() == 'SW':
            episode_id = i['data-id']
            film_id = i['data-source']
            resp = client.post("https://sextb.net/ajax/player" , data = {'episode' : episode_id , 'filmId' : film_id} , proxies = proxies).json()
            new_soup = BeautifulSoup(resp['player'], 'html.parser')
            video_link = new_soup.find('iframe')['src']
            string[i.text] = video_link.split('?poster')[0]
    if not string:
        raise DirectDownloadLinkException('No Links Found !')
    # return "\n".join([v for k, v in string.items() if v])
    return "\n".join([f"{i+1}. {v}" for i, (k, v) in enumerate(string.items()) if v])

def hdhub4u(url):
    try:
        scraper = cloudscraper.create_scraper(browser={'custom': 'HDHub4u-Bot/1.0'}, delay=2)       
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }       
        response = scraper.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = None
        title_selectors = [
            'h1.entry-title', 'h1.post-title', 'h1', 
            '.entry-header h1', '.post-header h1'
        ]       
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                raw_title = title_element.get_text().strip()
                title = re.sub(r'[^\x00-\x7F]+', ' ', raw_title)
                title = re.sub(r'\s+', ' ', title).strip()
                break
        if not title:
            title = url.split('/')[-2].replace('-', ' ').title()
        out = f"<b><u>{title}</u></b>"
        all_links = soup.find_all('a')
        download_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            if not href or 'how-to-download' in href.lower() or href.startswith('/'):
                continue
            indicators = [
                'hubdrive', 'hubcdn', 'techyboy4u', 'gdtot', 'gtlinks',
                'sharespark', 'drivebot', 'filepress', 'filecrypt',
                'download', 'link', 'mirror'
            ]           
            if any(indicator in href.lower() or indicator in text.lower() for indicator in indicators):
                quality_match = re.search(r'(480p|720p|1080p|2160p|4K)', text, re.IGNORECASE)
                size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:MB|GB))', text, re.IGNORECASE)
                codec_match = re.search(r'(HEVC|x264|x265|H\.264|H\.265)', text, re.IGNORECASE)
                link_info = f"{quality_match.group(1).upper() if quality_match else 'Link'}"
                if codec_match:
                    link_info += f" {codec_match.group(1).upper()}"
                if size_match:
                    link_info += f" [{size_match.group(1).upper()}]"  
                download_links.append((link_info, href))
        for i, (info, link) in enumerate(download_links, 1):
            out += f"\n\n<b>{i}. {info}</b>\n<b>🌐 Download Link:</b> <code>{link}</code>"
        return out.strip()
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in hdhub4u: {str(e)}")

def filmyfly(url):
    try:
        scraper = cloudscraper.create_scraper(browser={'custom': 'ScraperBot/1.0'})
        response = scraper.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        url_path = urlparse(url).path
        if "/page-download/" in url_path:
            movie_title_raw = url_path.split('/')[-1].replace('.html', '')
            movie_title = ' '.join(movie_title_raw.split('-'))
            movie_title = re.sub(r'\b\d{3,4}p\b', '', movie_title)
            movie_title = re.sub(r'ESub$', '', movie_title).strip()
        else:
            title_tag = soup.find('h1') or soup.find('h2') or soup.find('h3')
            movie_title = title_tag.text.strip() if title_tag else "Unknown Title"
        
        linkmake_url = None
        for a in soup.find_all('a', href=True):
            if 'linkmake' in a['href']:
                linkmake_url = a['href']
                break
                
        if not linkmake_url:
            raise DirectDownloadLinkException(f"No download link found for {url}")
            
        if not linkmake_url.startswith('http'):
            linkmake_url = urljoin(url, linkmake_url)
            
        response = scraper.get(linkmake_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        quality_links = []
        for a in soup.find_all('a', href=True):
            if 'filesdl' in a['href']:
                quality_links.append((a.text.strip(), a['href']))
                
        if not quality_links:
            raise DirectDownloadLinkException(f"No quality links in {linkmake_url}")
            
        result = []
        
        for i, (quality, cloud_url) in enumerate(quality_links, 1):
            if not cloud_url.startswith('http'):
                cloud_url = urljoin(linkmake_url, cloud_url)
                
            response = scraper.get(cloud_url)
            cloud_soup = BeautifulSoup(response.text, 'html.parser')
            text = cloud_soup.get_text("\n", strip=True)
            
            if cloud_soup.find('h1'):
                file_name = cloud_soup.find('h1').text.strip()
            else:
                m_name = re.search(r"([^\n]+\.(?:mkv|mp4|avi|mov))", text, re.I)
                file_name = m_name.group(1).strip() if m_name else movie_title
                
            if quality and quality.lower() not in file_name.lower():
                file_name = f"{file_name} [{quality}]"
                
            links_found = False
            result.append(f"<b>{i}. {file_name}</b>")
            
            for a in cloud_soup.find_all('a', href=True):
                href = a['href']
                if 'gofile.io' in href.lower():
                    result.append(href)
                    links_found = True
                elif 'gdflix' in href.lower():
                    result.append(href)
                    links_found = True
            
            if not links_found:
                result.append("No GoFile or GDFLIX links for this quality")
            
            result.append("")
        
        return "\n".join(result).strip()
    except Exception as e:
        raise DirectDownloadLinkException(f"Error in filmyfly: {str(e)}")

def direct_link_checker(link, onlylink=False):
    domain = urlparse(link).hostname
    if "1tamilmv" in domain:
        return tamilmv(link)
    elif "tamilblasters" in domain:
        return tamilblasters(link)
    elif "movierulz" in domain:
        return movierulz(link)
    elif "sharespark" in domain:
        return sharespark(link)
    elif "teluguflix" in domain:
        return teluguflix(link)
    elif "cinevood" in domain:
        return cinevood(link)
    elif "skymovieshd" in domain:
        return skymovieshd(link)
    elif "atishmkv" in domain:
        return atishmkv(link)
    elif "links.toonworld4all.me/redirect?data=" in link:
        return toonworld4all(link)
    elif "toonworld4all.me/redirect/main.php?url=" in link:
         return toonworld4allphp(link)
    elif 'sextb.net' in domain:
        return sextb(link)
    elif "filmyfly" in domain:
        return filmyfly(link)
    elif "https://olamovies.help/generate/?id=" in link or "https://gen2.ol-am.top/generate/?id=" in link:
        domain = urlparse(link).netloc
        link = link.replace(domain , "olamovies.help")
        return olam_generate(link)
    elif "hdhub4u" in domain:
        return hdhub4u(link)
    else:
        raise DirectDownloadLinkException(f"No Direct link function found for {domain}")
    if onlylink:
        return link
    chain = [link]
    while True:
        try:
            next_link = direct_link_checker(chain[-1], onlylink=True)
            if is_excep_link(chain[-1]):
                chain.append("\n\n" + next_link)
                break
            chain.append(next_link)
        except Exception:
            break
    return chain
