#!/usr/bin/env python3
import requests, re, cloudscraper, time, base64, subprocess

from requests import Session
from threading import Thread
from base64 import b64decode, b64encode
from json import loads
from os import path
from uuid import uuid4
from hashlib import sha256
from time import sleep
from re import findall, match, search

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml.etree import HTML
from requests import Session, session as req_session, post, RequestException, get
from urllib.parse import parse_qs, quote, unquote, urlparse, urljoin
from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from http.cookiejar import MozillaCookieJar

from bot import LOGGER, config_dict
from bot.helper.ext_utils.bot_utils import get_readable_time, is_share_link, is_index_link, is_magnet
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.help_messages import PASSWORD_ERROR_MESSAGE

_caches = {}
user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
)

anonfilesBaseSites = ['anonfiles.com', 'hotfile.io', 'bayfiles.com', 'megaupload.nz', 'letsupload.cc',
                      'filechan.org', 'myfile.is', 'vshare.is', 'rapidshare.nu', 'lolabits.se',
                      'openload.cc', 'share-online.is', 'upvid.cc']

debrid_sites = ['1fichier.com', '2shared.com', '4shared.com', 'alfafile.net', 'anzfile.net', 'backin.net',
                'bayfiles.com', 'bdupload.in', 'brupload.net', 'btafile.com', 'catshare.net', 'clicknupload.me',
                'clipwatching.com', 'cosmobox.org', 'dailymotion.com', 'dailyuploads.net', 'daofile.com',
                'datafilehost.com', 'ddownload.com', 'depositfiles.com', 'dl.free.fr', 'douploads.net',
                'drop.download', 'earn4files.com', 'easybytez.com', 'ex-load.com', 'extmatrix.com',
                'down.fast-down.com', 'fastclick.to', 'faststore.org', 'file.al', 'file4safe.com', 'fboom.me',
                'filefactory.com', 'filefox.cc', 'filenext.com', 'filer.net', 'filerio.in', 'filesabc.com', 'filespace.com',
                'file-up.org', 'fileupload.pw', 'filezip.cc', 'fireget.com', 'flashbit.cc', 'flashx.tv', 'florenfile.com',
                'fshare.vn', 'gigapeta.com', 'goloady.com', 'docs.google.com', 'gounlimited.to', 'heroupload.com',
                'hexupload.net', 'hitfile.net', 'hotlink.cc', 'hulkshare.com', 'icerbox.com', 'inclouddrive.com',
                'isra.cloud', 'katfile.com', 'keep2share.cc', 'letsupload.cc', 'load.to', 'down.mdiaload.com', 'mediafire.com',
                'mega.co.nz', 'mixdrop.co', 'mixloads.com', 'mp4upload.com', 'nelion.me', 'ninjastream.to', 'nitroflare.com',
                'nowvideo.club', 'oboom.com', 'prefiles.com', 'sky.fm', 'rapidgator.net', 'rapidrar.com', 'rapidu.net',
                'rarefile.net', 'real-debrid.com', 'redbunker.net', 'redtube.com', 'rockfile.eu', 'rutube.ru', 'scribd.com',
                'sendit.cloud', 'sendspace.com', 'simfileshare.net', 'solidfiles.com', 'soundcloud.com', 'speed-down.org',
                'streamon.to', 'streamtape.com', 'takefile.link', 'tezfiles.com', 'thevideo.me', 'turbobit.net', 'tusfiles.com',
                'ubiqfile.com', 'uloz.to', 'unibytes.com', 'uploadbox.io', 'uploadboy.com', 'uploadc.com', 'uploaded.net',
                'uploadev.org', 'uploadgig.com', 'uploadrar.com', 'uppit.com', 'upstore.net', 'upstream.to', 'uptobox.com',
                'userscloud.com', 'usersdrive.com', 'vidcloud.ru', 'videobin.co', 'vidlox.tv', 'vidoza.net', 'vimeo.com',
                'vivo.sx', 'vk.com', 'voe.sx', 'wdupload.com', 'wipfiles.net', 'world-files.com', 'worldbytez.com', 'wupfile.com',
                'wushare.com', 'xubster.com', 'youporn.com', 'youtube.com']

debrid_link_sites = ["1dl.net", "1fichier.com", "alterupload.com", "cjoint.net", "desfichiers.com", "dfichiers.com", "megadl.org", 
                "megadl.fr", "mesfichiers.fr", "mesfichiers.org", "piecejointe.net", "pjointe.com", "tenvoi.com", "dl4free.com", 
                "apkadmin.com", "bayfiles.com", "clicknupload.link", "clicknupload.org", "clicknupload.co", "clicknupload.cc", 
                "clicknupload.link", "clicknupload.download", "clicknupload.club", "clickndownload.org", "ddl.to", "ddownload.com", 
                "depositfiles.com", "dfile.eu", "dropapk.to", "drop.download", "dropbox.com", "easybytez.com", "easybytez.eu", 
                "easybytez.me", "elitefile.net", "elfile.net", "wdupload.com", "emload.com", "fastfile.cc", "fembed.com", 
                "feurl.com", "anime789.com", "24hd.club", "vcdn.io", "sharinglink.club", "votrefiles.club", "there.to", "femoload.xyz", 
                "dailyplanet.pw", "jplayer.net", "xstreamcdn.com", "gcloud.live", "vcdnplay.com", "vidohd.com", "vidsource.me", 
                "votrefile.xyz", "zidiplay.com", "fcdn.stream", "femax20.com", "sexhd.co", "mediashore.org", "viplayer.cc", "dutrag.com", 
                "mrdhan.com", "embedsito.com", "diasfem.com", "superplayxyz.club", "albavido.xyz", "ncdnstm.com", "fembed-hd.com", 
                "moviemaniac.org", "suzihaza.com", "fembed9hd.com", "vanfem.com", "fikper.com", "file.al", "fileaxa.com", "filecat.net", 
                "filedot.xyz", "filedot.to", "filefactory.com", "filenext.com", "filer.net", "filerice.com", "filesfly.cc", "filespace.com", 
                "filestore.me", "flashbit.cc", "dl.free.fr", "transfert.free.fr", "free.fr", "gigapeta.com", "gofile.io", "highload.to", 
                "hitfile.net", "hitf.cc", "hulkshare.com", "icerbox.com", "isra.cloud", "goloady.com", "jumploads.com", "katfile.com", 
                "k2s.cc", "keep2share.com", "keep2share.cc", "kshared.com", "load.to", "mediafile.cc", "mediafire.com", "mega.nz", 
                "mega.co.nz", "mexa.sh", "mexashare.com", "mx-sh.net", "mixdrop.co", "mixdrop.to", "mixdrop.club", "mixdrop.sx", 
                "modsbase.com", "nelion.me", "nitroflare.com", "nitro.download", "e.pcloud.link", "pixeldrain.com", "prefiles.com", "rg.to", 
                "rapidgator.net", "rapidgator.asia", "scribd.com", "sendspace.com", "sharemods.com", "soundcloud.com", "noregx.debrid.link", 
                "streamlare.com", "slmaxed.com", "sltube.org", "slwatch.co", "streamtape.com", "subyshare.com", "supervideo.tv", "terabox.com", 
                "tezfiles.com", "turbobit.net", "turbobit.cc", "turbobit.pw", "turbobit.online", "turbobit.ru", "turbobit.live", "turbo.to", 
                "turb.to", "turb.cc", "turbabit.com", "trubobit.com", "turb.pw", "turboblt.co", "turboget.net", "ubiqfile.com", "ulozto.net", 
                "uloz.to", "zachowajto.pl", "ulozto.cz", "ulozto.sk", "upload-4ever.com", "up-4ever.com", "up-4ever.net", "uptobox.com", 
                "uptostream.com", "uptobox.fr", "uptostream.fr", "uptobox.eu", "uptostream.eu", "uptobox.link", "uptostream.link", "upvid.pro", 
                "upvid.live", "upvid.host", "upvid.co", "upvid.biz", "upvid.cloud", "opvid.org", "opvid.online", "uqload.com", "uqload.co", 
                "uqload.io", "userload.co", "usersdrive.com", "vidoza.net", "voe.sx", "voe-unblock.com", "voeunblock1.com", "voeunblock2.com", 
                "voeunblock3.com", "voeunbl0ck.com", "voeunblck.com", "voeunblk.com", "voe-un-block.com", "voeun-block.net", 
                "reputationsheriffkennethsand.com", "449unceremoniousnasoseptal.com", "world-files.com", "worldbytez.com", "salefiles.com", 
                "wupfile.com", "youdbox.com", "yodbox.com", "youtube.com", "youtu.be", "4tube.com", "academicearth.org", "acast.com", 
                "add-anime.net", "air.mozilla.org", "allocine.fr", "alphaporno.com", "anysex.com", "aparat.com", "www.arte.tv", "video.arte.tv", 
                "sites.arte.tv", "creative.arte.tv", "info.arte.tv", "future.arte.tv", "ddc.arte.tv", "concert.arte.tv", "cinema.arte.tv", 
                "audi-mediacenter.com", "audioboom.com", "audiomack.com", "beeg.com", "camdemy.com", "chilloutzone.net", "clubic.com", "clyp.it", 
                "daclips.in", "dailymail.co.uk", "www.dailymail.co.uk", "dailymotion.com", "touch.dailymotion.com", "democracynow.org", 
                "discovery.com", "investigationdiscovery.com", "discoverylife.com", "animalplanet.com", "ahctv.com", "destinationamerica.com", 
                "sciencechannel.com", "tlc.com", "velocity.com", "dotsub.com", "ebaumsworld.com", "eitb.tv", "ellentv.com", "ellentube.com", 
                "flipagram.com", "footyroom.com", "formula1.com", "video.foxnews.com", "video.foxbusiness.com", "video.insider.foxnews.com", 
                "franceculture.fr", "gameinformer.com", "gamersyde.com", "gorillavid.in", "hbo.com", "hellporno.com", "hentai.animestigma.com", 
                "hornbunny.com", "imdb.com", "instagram.com", "itar-tass.com", "tass.ru", "jamendo.com", "jove.com", "keek.com", "k.to", 
                "keezmovies.com", "khanacademy.org", "kickstarter.com", "krasview.ru", "la7.it", "lci.fr", "play.lcp.fr", "libsyn.com", 
                "html5-player.libsyn.com", "liveleak.com", "livestream.com", "new.livestream.com", "m6.fr", "www.m6.fr", "metacritic.com", 
                "mgoon.com", "m.mgoon.com", "mixcloud.com", "mojvideo.com", "movieclips.com", "movpod.in", "musicplayon.com", "myspass.de", 
                "myvidster.com", "odatv.com", "onionstudios.com", "ora.tv", "unsafespeech.com", "play.fm", "plays.tv", "playvid.com", 
                "pornhd.com", "pornhub.com", "www.pornhub.com", "pyvideo.org", "redtube.com", "embed.redtube.com", "www.redtube.com", 
                "reverbnation.com", "revision3.com", "animalist.com", "seeker.com", "rts.ch", "rtve.es", "videos.sapo.pt", "videos.sapo.cv", 
                "videos.sapo.ao", "videos.sapo.mz", "videos.sapo.tl", "sbs.com.au", "www.sbs.com.au", "screencast.com", "skysports.com", 
                "slutload.com", "soundgasm.net", "store.steampowered.com", "steampowered.com", "steamcommunity.com", "stream.cz", "streamable.com", 
                "streamcloud.eu", "sunporno.com", "teachertube.com", "teamcoco.com", "ted.com", "tfo.org", "thescene.com", "thesixtyone.com", 
                "tnaflix.com", "trutv.com", "tu.tv", "turbo.fr", "tweakers.net", "ustream.tv", "vbox7.com", "veehd.com", "veoh.com", "vid.me", 
                "videodetective.com", "vimeo.com", "vimeopro.com", "player.vimeo.com", "player.vimeopro.com", "wat.tv", "wimp.com", "xtube.com", 
                "yahoo.com", "screen.yahoo.com", "news.yahoo.com", "sports.yahoo.com", "video.yahoo.com", "youporn.com"]


def direct_link_generator(link):
    auth = None
    if isinstance(link, tuple):
        link, auth = link
    if is_magnet(link):
        return real_debrid(link, True)

    domain = urlparse(link).hostname
    if not domain:
        raise DirectDownloadLinkException("ERROR: Invalid URL")
    if 'youtube.com' in domain or 'youtu.be' in domain:
        raise DirectDownloadLinkException("ERROR: Use ytdl cmds for Youtube links")
    elif config_dict['DEBRID_LINK_API'] and any(x in domain for x in debrid_link_sites):
        return debrid_link(link)
    elif config_dict['REAL_DEBRID_API'] and any(x in domain for x in debrid_sites):
        return real_debrid(link)
    elif any(x in domain for x in ['filelions.com', 'filelions.live', 'filelions.to', 'filelions.online']):
        return filelions(link)
    elif 'mediafire.com' in domain:
        return mediafire(link)
    elif 'osdn.net' in domain:
        return osdn(link)
    elif 'github.com' in domain:
        return github(link)
    elif '1drv.ms' in domain:
        return onedrive(link)
    elif 'pixeldrain.com' in domain:
        return pixeldrain(link)
    elif 'racaty' in domain:
        return racaty(link)
    elif '1fichier.com' in domain:
        return fichier(link)
    elif 'solidfiles.com' in domain:
        return solidfiles(link)
    elif 'krakenfiles.com' in domain:
        return krakenfiles(link)
    elif 'upload.ee' in domain:
        return uploadee(link)
    elif 'akmfiles' in domain:
        return akmfiles(link)
    elif 'linkbox' in domain:
        return linkbox(link)
    elif 'shrdsk' in domain:
        return shrdsk(link)
    elif 'letsupload.io' in domain:
        return letsupload(link)
    elif 'gofile.io' in domain:
        return gofile(link, auth)
    elif 'easyupload.io' in domain:
        return easyupload(link)
    elif 'streamvid.net' in domain:
        return streamvid(link)
    elif any(x in domain for x in ['dood.watch', 'doodstream.com', 'dood.to', 'dood.so', 'dood.cx', 'dood.la', 'dood.ws', 'dood.sh', 'doodstream.co', 'dood.pm', 'dood.wf', 'dood.re', 'dood.video', 'dooood.com', 'dood.yt', 'doods.yt', 'dood.stream', 'doods.pro']):
        return doods(link)
    elif any(x in domain for x in ['streamtape.com', 'streamtape.co', 'streamtape.cc', 'streamtape.to', 'streamtape.net', 'streamta.pe', 'streamtape.xyz']):
        return streamtape(link)
    elif any(x in domain for x in ['wetransfer.com', 'we.tl']):
        return wetransfer(link)
    elif any(x in domain for x in anonfilesBaseSites):
        raise DirectDownloadLinkException('ERROR: R.I.P Anon Sites!')
    #-----------------------------------MY SITES--------------------------------#
    elif "papajiurl.com" in domain:
        return cf_decrypt_transcript(link, "https://papajiurl.com" , "https://animenewsnet.com/" , 7)
    elif "lemolink.com" in domain:
        return transcript(link , 'https://lemolink.com/' , 'https://getpdf.net/' , 12)
    elif "gameszone.ink" in domain or "gameszone.im" in domain or "genzurl.com" in domain or 'gameszone.tech' in domain:
        link = link.replace('gameszone.im' , 'gameszone.tech').replace('genzurl.com' , 'gameszone.tech').replace('gameszone.ink' , 'gameszone.tech')
        client = requests.Session()
        resp = client.get(link , allow_redirects = False)
        match = re.search(r'href\s*=\s*"([^"]+)"', resp.text)
        if match:
            referer = match.group(1)
        else:
            raise DirectDownloadLinkException('Referer Not Found !')
        referer = "https://" + urlparse(referer).netloc + "/"
        return decrypt_transcript(link, "https://gameszone.tech/" , referer , 7 , True)
    elif 'publicearn' in domain:
        client = requests.Session()
        link = link.replace('publicearn.com' , 'publicearn.site')
        resp = client.get(link , allow_redirects = False)
        match = re.search(r'href\s*=\s*"([^"]+)"', resp.text)
        if match:
            referer = match.group(1)
        else:
            raise DirectDownloadLinkException('Referer Not Found !')
        referer = "https://" + urlparse(referer).netloc + "/"
        return cf_decrypt_transcript(link, "https://publicearn.site/" , referer , 7 )
    elif 'reboxlinks.xyz' in domain:
        client = requests.Session()
        link = link.replace('gameszone.im' , 'gameszone.ink')
        resp = client.get(url , allow_redirects = False)
        match = re.search(r'href\s*=\s*"([^"]+)"', resp.text)
        if match:
            referer = match.group(1)
        else:
            raise DirectDownloadLinkException('Referer Not Found !')
        referer = "https://" + urlparse(referer).netloc + "/"
        return decrypt_transcript(link, "https://reboxlinks.xyz/" , referer , 7 , True)
    elif 'kingurl.com' in domain:
        return transcript(link, "https://go.kingurl.in/", "https://earnbox.bankshiksha.in/", 7)
    elif "vplink.in" in domain:
        return local_transcript(link, "https://vplink.in/", "https://kaomojihub.com/", 7)
    elif 'seturl.in' in domain:
        return aws_transcript(link ,'https://url.seturl.in/' , 'https://earn.offerpagehub.fun/' , 7)
    elif 'shortner.in' in domain:
        return cf_transcript(link ,'https://shortner.in/' , 'https://quiz.mukhyasamachar.in/' , 7 , ref_detect = True)
    elif "jiolink.net" in domain:
        return transcript(link, "https://jiolink.net/", "https://earn.stockmarg.com/" , 7)
    elif 'bharatlinks.com' in domain:
        client = requests.Session()
        resp = client.get(link , allow_redirects = False)
        loc = resp.headers.get('location')
        if not loc:
            raise DirectDownloadLinkException('Referer Not Found !')
        else:
            referer = "https://" + urlparse(loc).netloc + "/"
        return transcript(link , "https://bharatlinks.com/", referer, 7)
    elif 'trusturl.in' in domain:
        return transcript(link , 'https://trusturl.in/' , 'https://cryptoforyou.in/' , 7)
    elif 'modijiurl.com' in domain:
        return transcript(link, "https://modijiurl.com/", "https://mazakisan.com/", 6)
    elif 'inshorturl.com' in domain:
        return cf_transcript(link, 'https://inshorturl.com/', 'https://mahitimanch.in/' , 5)
    elif 'shortxlinks.com' in domain or 'shortxlinks.in' in domain or 'shortxlinks.xyz' in domain:
        return transcript( link, "https://shortxlinks.com/", "https://mtc1.jobwalebaba.com/", 5)
    elif 'seturl.in' in domain:
        return cf_transcript(link ,'https://set.seturl.in/' , 'https://loan.creditsgoal.com/' , 7 , 'https://set.seturl.in/links/go')
    elif 'link.pocolinks.com' in link:
        return transcript(link, "https://blog.techweedy.top/", "https://links.rcccn.in/", 7)
    elif 'm.easysky.in' in link:
        return transcript(link, "https://techy.veganab.co/", "https://camdigest.com/", 8)
    elif 'droplink.co' in link:
        return droplink(link, "https://game5s.com/")
    elif 'gplinks.co' in link:
        return gplinks(link, "https://gplinks.co/")
    elif "linkcents.com" in domain:
        return linkcents(link)
    elif any(x in domain for x in ["gyanilinks.com", "gtlinks.me"]):
        return gyanilinks(link , "https://golink.bloggerishyt.in/" , "https://tech.pubghighdamage.com/")
    elif any(x in domain for x in ['terabox.com', 'nephobox.com', '4funbox.com', 'mirrobox.com', 'momerybox.com', 'teraboxapp.com', '1024tera.com', 'terabox.app', 'gibibox.com', 'goaibox.com', 'terasharelink.com', 'freeterabox.com', '1024terabox.com', 'teraboxshare.com', 'teraboxlink.com', 'terafileshare.com']):
        return terabox(link)
    elif 'hubcloud' in domain:
        return hubcloud(link)
    elif "hubdrive" in domain:
        return hubdrive(link)
    elif any(x in domain for x in ['gdflix', 'gdlink', 'ziddiflix', 'vifix']) or 'gd.vifix.site' in link:
        return gdflix(link)
    #-------------------------------------END-----------------------------------#
    elif is_index_link(link) and link.endswith('/'):
        return gd_index(link, auth)
    elif is_share_link(link):
        if 'gdtot' in domain:
            return gdtot(link)
        elif 'filepress' in domain:
            return filepress(link)
        elif 'www.jiodrive' in domain:
            return jiodrive(link)
        else:
            return sharer_scraper(link)
    elif 'zippyshare.com' in domain:
        raise DirectDownloadLinkException('ERROR: R.I.P Zippyshare')
    else:
        raise DirectDownloadLinkException(f'No Direct link function found for {link}')

# ---------------------------------------------------------------- Shorten Bypass --------------------------------------------------------#

cf_api = f'http://161.35.94.73:3000/'
cf_cdn = f'http://161.35.94.73:5544/'
AWS_API = f'http://15.207.247.213:8080/'
NORTH_API = f'https://p01--bps--p9g26wzpywjh.code.run/'
LOCAL_CF_API = 'https://27jbp5c8-3000.inc1.devtunnels.ms/'
LOCAL_API = 'https://27jbp5c8-5000.inc1.devtunnels.ms/'
DIRECT_URL = 'https://dd.bypass-bot.workers.dev/'

cookies_dict = {}

def local_transcript(url: str, DOMAIN: str, ref: str, sltime , reel2earn = False) -> str:
    proxies = {
        'http': 'http://iuhottnp-in-1:agybxhs8o5t8@p.webshare.io:80',
        'https' : 'http://iuhottnp-in-1:agybxhs8o5t8@p.webshare.io:80'
    }
    useragent = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    code = url.rstrip("/").split("/")[-1]
    cget = cloudscraper.create_scraper(allow_brotli=False).request
    resp = cget("GET", url , headers={ 'User-Agent': useragent} , proxies=proxies)
    if reel2earn:
        ref = "https://" + urlparse(resp.url).netloc + "/"
    resp = cget("GET", f"{DOMAIN}/{code}", headers={"referer": ref , 'User-Agent': useragent} , proxies=proxies)
    soup = BeautifulSoup(resp.content, "html.parser")
    data = {inp.get('name'): inp.get('value') for inp in soup.find_all('input') if inp.get('name') and inp.get('value')}
    sleep(sltime)
    resp = cget("POST", f"{DOMAIN}/links/go", data=data, headers={ "x-requested-with": "XMLHttpRequest" , 'User-Agent': useragent} , proxies=proxies)
    return resp.json()['url']

def get_cf_clearance(url):
    old = cookies_dict.get(url)
    if not old or time.time() > old['expiry']:
        client = cloudscraper.create_scraper()
        response = client.post(f"{cf_api}cf-clearance-scraper" , headers = {"Content-Type": "application/json"} , 
                json={
                        "url": url,
                        "mode": "waf-session"
                }
        )
        session = response.json()
        cookies = { cookie['name'] : cookie['value'] for cookie in session.get("cookies", []) }
        cookies_dict[url] = {'cookies' : cookies , 'headers' : session['headers'] , 'expiry' : time.time() + 600}
        return cookies , session['headers']
    else:
        return old['cookies'] , old['headers']

def cf_transcript(url , domain , referer , sleep_time , cf_base = False, ref_detect = False):
    try:
        client = cloudscraper.create_scraper()
        cookies , headers = get_cf_clearance(domain if not cf_base else cf_base)
        if ref_detect:
            tmp = f"{cf_cdn}headerloc"
            data = {
                'url' : url ,
                'cookies' : str(cookies) ,
                'headers' : str(headers)
            }
            response = client.post(tmp , data = data)
            ref_text = response.text
            if ref_text and ref_text.startswith('https://'):
                referer = "https://" + urlparse(ref_text).netloc + "/"
        temp = f"{cf_cdn}transcript"
        data = {
            'url' : url , 
            'domain' : domain,
            'referer': referer,
            'sleep': str(sleep_time),
            'cookies' : str(cookies) ,
            'headers' : str(headers)
        }
        response = client.post(temp , data = data)
        return response.json()['url']
    except:
        raise DirectDownloadLinkException("Bypass Script For This URL Is Not Working !")

def aws_transcript(url , domain , referer , sleep_time):
    try:
        client = cloudscraper.create_scraper()
        temp = f"{AWS_API}transcript"
        data = {
            'url' : url , 
            'domain' : domain,
            'ref': referer,
            'sltime': str(sleep_time),
        }
        response = client.post(temp , data = data)
        return response.json()['url']
    except:
        raise DirectDownloadLinkException("Bypass Script For This URL Is Not Working !")

def transcript(url: str, DOMAIN: str, ref: str, sltime) -> str:
    useragent = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    code = url.rstrip("/").split("/")[-1]
    cget = cloudscraper.create_scraper(allow_brotli=False).request
    resp = cget("GET", f"{DOMAIN}/{code}", headers={"referer": ref , 'User-Agent': useragent})
    soup = BeautifulSoup(resp.content, "html.parser")
    data = {inp.get('name'): inp.get('value') for inp in soup.find_all('input') if inp.get('name') and inp.get('value')}
    sleep(sltime)
    resp = cget("POST", f"{DOMAIN}/links/go", data=data, headers={ "x-requested-with": "XMLHttpRequest" , 'User-Agent': useragent})
    try: 
        return resp.json()['url']
    except Exception as e: raise DirectDownloadLinkException('Bypass Script For This URL Is Not Working !')

def turnstile_solver(client , domain , site_key):
     _json = {
         'url' : domain ,
         'siteKey' : site_key,
         'mode' : 'turnstile-min'
     }
     session = client.post(f'{cf_api}cf-clearance-scraper' , json = _json).json()
     return session['token']

def decrypt_alias(client , alias):
    resp = client.post("https://decrypt.streamed.workers.dev/" , json = {'key' : alias})
    return resp.json()['result']

def decrypt_transcript(url , domain , ref , sltime , decrypt = False):
    ref_netloc = urlparse(ref).netloc
    domain_netloc = urlparse(domain).netloc
    code = url.split('/')[-1]
    url = f"https://{domain_netloc}/{code}"
    client = cloudscraper.create_scraper()
    cget = client.request
    resp = cget('GET' , url)
    if decrypt:
        new_url = re.search(r'window.location.href\s*=\s*\"(http[^\"]+)\"', resp.text).group(1)
        resp11 = cget('GET' , new_url)
    resp2 = cget('GET' , ref ,  headers = {'referer' : 'https://www.google.com/'})
    if decrypt:
        data = re.search(r'encryptedDataa\s*=\s*\"([^\"]+)\"', resp2.text).group(1)
        data = decrypt_alias(client , data)
    else:
        data = re.search(r'data\s*:\s*\'([^\']+)\'', resp2.text).group(1)
    verify_link = f"https://{domain_netloc}/link/verify.php"
    data = {
        'step_1' : code,
        'data' : data
    }
    headers = {
        'authority' : domain_netloc,
        'origin' : f'https://{ref_netloc}',
    }
    resp3 = cget('POST', verify_link , data = data , headers = headers).json()
    sid = resp3['inserted_data']["id"]
    resp6 = cget('GET' , ref ,  headers = {'referer' : 'https://www.google.com/'})
    if decrypt:
        data = re.search(r'encryptedDataa\s*=\s*\"([^\"]+)\"', resp6.text).group(1)
        data = decrypt_alias(client , data)
    else:
        data = re.search(r'data\s*:\s*\'([^\']+)\'', resp6.text).group(1)
    data = {
        'id' : sid,
        'step_2' : code,
        'data' : data
    }
    resp6 = cget('POST', verify_link , data = data , headers = headers)
    if decrypt:
        resp4 = cget("GET" , f"{url}/?sid={sid}" , headers = {'referer' : ref})
    else:
        resp4 = cget("GET" , f"{url}?sid={sid}" , headers = {'referer' : ref})
    soup = BeautifulSoup(resp4.text , 'html.parser')
    data = {inp.get('name'): inp.get('value') for inp in soup.find_all('input') if inp.get('name') and inp.get('value')}
    sleep(sltime)
    resp5 = cget("POST", f"https://{domain_netloc}/links/go", data = data , headers={"Referer" : resp4.url , "x-requested-with": "XMLHttpRequest" , 'User-Agent': 'Mozilla/5.0'})
    try:
        return resp5.json()['url']
    except Exception as e: raise DirectDownloadLinkException("Bypass Script For This URL Is Not Working !")

def cf_decrypt_transcript(url , domain , referer , sleep_time):
    try:
        client = cloudscraper.create_scraper()
        temp = f"{cf_cdn}decrypt_transcript"
        data = {
            'url' : url,
            'domain' : domain,
            'referer' : referer,
            'sleep' : str(sleep_time),
            'dapi' : 'https://decrypt.streamed.workers.dev/'
        }
        response = client.post(temp , data = data)
        return response.json()['url']
    except:
        raise DirectDownloadLinkException("Bypass Script For This URL Is Not Working !")

#----------------------Linkcents------------------------#

slowaes_js_template = """
{slowaescode}

function toNumbers(hexStr) {
    if (typeof hexStr !== 'string') {
        throw new TypeError("Input must be a hex string");
    }
    if (hexStr.length % 2 !== 0) {
        throw new Error("Hex string must have an even length");
    }
    let result = [];
    for (let i = 0; i < hexStr.length; i += 2) {
        result.push(parseInt(hexStr.slice(i, i + 2), 16));
    }
    return result;
}

function toHex() {
    var hexStr = '';
    var input = (arguments.length === 1 && Array.isArray(arguments[0])) ? arguments[0] : arguments;
    for (var i = 0; i < input.length; i++) {
        hexStr += (input[i] < 16 ? '0' : '') + input[i].toString(16);
    }
    return hexStr;
}

key = toNumbers('{key}');
iv = toNumbers('{iv}');
cipher = toNumbers(atob('{cipher}'));
dec = toHex(slowAES.decrypt(iv,{mode},key,cipher));
console.log(dec);
"""

def custom_base64_encode(data: bytes) -> str:
    b64 = base64.b64encode(data).decode()
    return b64.replace("+", "xMl3Jk").replace("/", "Por21Ld").replace("=", "Ml32")

def generate_token():
    password = "9092820657d9d95a636093a1d1b832c0422a17ff"
    salt = get_random_bytes(16)
    iv = get_random_bytes(16)
    timestamp = str(int(time.time() * 1000))
    key = PBKDF2(password, salt, dkLen=32, count=1000)
    plaintext = f"{iv.hex()}:{timestamp}".encode()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
    encoded_ciphertext = custom_base64_encode(ciphertext)
    encoded_iv = custom_base64_encode(iv)
    salt_hex = salt.hex()
    token = f"verify={encoded_ciphertext}&iv={encoded_iv}&salt={salt_hex}&iterations=100"
    return token

def get_server_pie_token(url, user_agent, text=None, minn=None):
    client = cloudscraper.create_scraper(allow_brotli=False)
    if not text:
        resp = client.get(url, headers={'User-Agent': user_agent}, allow_redirects=False).text
    else:
        resp = text
    if not minn:
        slowaes_ = client.get(f"{url}min.js").text
    else:
        slowaes_ = minn
    array_match = re.search(r'var\s+(\w+)\s*=\s*(\[[^\]]+\]);', resp)
    try:
        key = eval(array_match.group(2))[-1]
    except:
        key = re.search(r'\["([^"]+)"\]', resp).group(1)
        key = bytes(key, "utf-8").decode("unicode_escape")
    try:
        key = b64decode(key).decode('utf-8')
    except:
        pass
    iv = re.search(r'toNumbers\("([^"]+)"\)', resp).group(1)
    cipher = re.search(r'atob\("([^"]+)"\)', resp).group(1)
    mode = re.search(r'slowAES\.decrypt\([^,]+,\s*([^,]+)', resp).group(1)
    cname = re.search(r'document\.cookie\s*=\s*"([^=]+)=', resp).group(1)
    js_code = slowaes_js_template.replace('{key}', key).replace('{iv}', iv).replace('{cipher}', cipher).replace('{mode}', mode).replace('{slowaescode}', slowaes_)
    process = subprocess.Popen(['node', '-e', js_code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return {cname: stdout.decode('utf-8').strip()}

def linkcents(url):
    code = url.split('/')[-1]
    url = f"https://linkcents.com/{code}"
    useragent = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    cookies = get_server_pie_token("https://linkcents.com/", useragent)
    cget = cloudscraper.create_scraper(allow_brotli=False).request
    resp = cget('GET', url, cookies=cookies, headers={'user-agent': useragent}, allow_redirects=False)
    match = re.search(r'href\s*=\s*"([^"]+)"', resp.text)
    if not match:
        loc = resp.headers.get('location')
        if loc and 'linkcents.com' not in loc:
            return loc
        raise Exception('Linkcents No Match!')
    extracted_url = parse_qs(urlparse(match.group(1)).query)['next'][0]
    str_cookie = ", ".join([f"{k}={v}" for k, v in cookies.items()])
    headers = {
        'Cookie': 'referer=unknown|no,' + str_cookie,
        'Referer': extracted_url,
        'User-Agent': useragent,
    }
    token = generate_token()
    new_resp = cget('GET', f"{url}?{token}", cookies=cookies, headers=headers, allow_redirects=False)
    location = new_resp.headers.get('location')
    if not location:
        raise Exception('Linkcents Location Not Found!')
    return location

def gyanilinks(url , domain , ref):
    try:
        client = cloudscraper.create_scraper()
        cookies , headers = get_cf_clearance(domain)
        temp = f"{cf_cdn}transcript"
        data = {
            'url' : url , 
            'domain' : domain,
            'referer': ref,
            'sleep': str(7),
            'cookies' : str(cookies) ,
            'headers' : str(headers),
            'cf-turnstile-response': ""
        }
        response = client.post(temp , data = data)
        return response.json()['url']
    except:
        raise DirectDownloadLinkException("Bypass Script For This URL Is Not Working !")

def gplinks(url , domain):
    cookies , headers = get_cf_clearance(domain)
    scraper = cloudscraper.create_scraper(allow_brotli=False)
    data = {
        'url' : url ,
        'cookies' : str(cookies),
        'headers' : str(headers)
    }
    res = scraper.post(f'{cf_cdn}gplinks' , data = data)
    return res.json()['url']

def droplink(url , ref ):
    client = cloudscraper.create_scraper(allow_brotli=False)
    res = client.get(url, timeout=5)
    h = {"referer": ref}
    res = client.get(url, headers=h)
    bs4 = BeautifulSoup(res.content, "html.parser")
    inputs = bs4.find_all("input")
    data = {input.get("name"): input.get("value") for input in inputs}
    h = {
            "content-type": "application/x-www-form-urlencoded",
            "x-requested-with": "XMLHttpRequest",
        }
    p = urlparse(url)
    final_url = f"{p.scheme}://{p.netloc}/links/go"
    sleep(3.1)
    res = client.post(final_url, data=data, headers=h).json()
    if res["status"] == "success": return res["url"]
    return 'Something went wrong :('

# ---------------------------------------------------------------- Website Scraping ------------------------------------------------------#

def gdflix(url):
    client = create_scraper().request
    parsed = urlparse(url)
    if 'gdlink' in parsed.netloc:
        res = client('GET', url).url
        url = "https://" + res.split('/c/s/')[-1]
    res = client('GET', url)
    url = res.url
    domain = urlparse(url).netloc
    dcode = url.split('/')[-1]
    soup = BeautifulSoup(res.text, 'html.parser')
    if "/pack/" in url:
        title = soup.find('h3').text
        final_string = f"☰ {title}\n\n"
        all_links = soup.select('a[href^="/file/"]')
        for index, link in enumerate(all_links, start=1):
            temp_url = f"https://{domain}{link['href']}"
            final_string += gdflix(temp_url).replace('┎', f"{index}.") + "\n\n"
        return final_string.strip()
    title = soup.find('li', class_='list-group-item', string=lambda text: text and 'Name :' in text).text.split('Name : ')[-1]
    size = soup.find('li', class_='list-group-item', string=lambda text: text and 'Size :' in text).text.split('Size : ')[-1]

    gofile, dl_link, tg_link = None, None, None

    go_ = soup.find(lambda tag: tag.name == "a" and "gofile" in tag.get_text(strip=True).lower())

    if go_:
        if 'multiup.php' in go_['href']:
            gofile = "Status Uploading, Try Later"
        else:
            res2 = client('GET', go_['href'])
            match = re.search(r"https://gofile\.io/d/\w+", res2.text)
            if match:
                gofile = match.group()

    tg_ = soup.find(lambda tag: tag.name == "a" and "telegram generate" in tag.get_text(strip=True).lower())
    if tg_:
        tg_link = tg_['href']

    tg_ = soup.find(lambda tag: tag.name == "a" and "telegram file" in tag.get_text(strip=True).lower())
    if tg_:
        parsed = parse_qs(urlparse(tg_['href']).query)
        code, bot = parsed['start'][0], parsed['bot'][0]
        tg_link = f"https://t.me/{bot}?start={code}"

    cloud_dl = soup.find(lambda tag: tag.name == "a" and "cloud download" in tag.get_text(strip=True).lower() and '.dev' in tag.get('href', ''))
    if cloud_dl:
        dl_link = cloud_dl['href']

    if not dl_link:
        fast_dl = soup.find(lambda tag: tag.name == "a" and "fast cloud download" in tag.get_text(strip=True).lower() and ('xfile' in tag.get('href', '') or 'zfile' in tag.get('href', '')))
        if fast_dl:
            res3 = client('GET', f"https://{domain}" + fast_dl['href'])
            soup3 = BeautifulSoup(res3.text, 'html.parser')
            item = soup3.find(lambda tag: tag.name == "a" and "cloud resume download" in tag.get_text(strip=True).lower())
            if item:
                dl_link = item['href']

    if not dl_link:
        instant_dl = soup.find(lambda tag: tag.name == "a" and "instant dl" in tag.get_text(strip=True).lower() and 'cdn' in tag.get('href', ''))
        if instant_dl:
            res4 = client('GET', instant_dl['href'])
            url = res4.url.split('?url=')[-1]
            if url.startswith('http'):
                dl_link = url
            else:
                ddd = urlparse(res4.url).netloc
                match1 = re.search(r'href\s?=\s?"([^"]+)"', res4.text)
                if match1:
                    res6 = client('GET', "https://" + ddd + match1.group(1))
                    soup6 = BeautifulSoup(res6.text, 'html.parser')
                    ff = soup6.select_one('a[href^="https://video-downloads.googleusercontent.com"]')
                    if ff:
                        dl_link = ff['href']

    if not dl_link:
        lnks = f"https://{domain}/wfile/{dcode}"
        res5 = client('GET', lnks)
        soup4 = BeautifulSoup(res5.text, 'html.parser')
        d_j = soup4.find_all(lambda tag: tag.name == "a" and "download" in tag.get_text(strip=True).lower() and '.dev' in tag.get('href', ''))
        for i in d_j:
            dl_link = i['href']

    if dl_link:
        dl_link = quote(dl_link, safe=":/=&?")

    return dl_link if dl_link else None

def hubdrive(url):
    client = cloudscraper.create_scraper()
    res = client.get(url)
    soup = BeautifulSoup(res.text , 'html.parser')
    hubcloud_link = soup.select_one('a[href^="https://hubcloud"]')
    if not hubcloud_link: raise DirectDownloadLinkException('HubCloud Link Not Found For This HubDrive Link !')
    return hubcloud(hubcloud_link['href'])

def hubcloud(url):
    client = create_scraper()
    res = client.get(url)
    domain = urlparse(res.url).netloc
    soup = BeautifulSoup(res.text, 'html.parser')

    anchor = soup.find('a', href=lambda x: x and '?token' in x)
    if not anchor:
        anchor = soup.find('a', href=lambda x: x and '&token' in x)
    if not anchor:
        raise DirectDownloadLinkException("No download link found!")

    anchor = anchor['href']
    if not anchor.startswith('http'):
        anchor = f"https://{domain}" + anchor

    res1 = client.get(anchor)
    soup1 = BeautifulSoup(res1.text, 'html.parser')
    anchors = soup1.find_all('a')

    dl_links = {}

    for i in anchors:
        if not i.get('href'):
            continue
        domain = urlparse(i['href']).netloc
        if 'pixeldrain.net' in domain:
            dl_links['Pixeldrain'] = i['href']
        elif 'bzzhr.co' in domain:
            dl_links['BuzzServer'] = i['href']
        elif 'FSL Server' in i.text:
            dl_links['FSL Server'] = i['href']
        elif 'Download File' in i.text and 'workers.dev' in domain:
            dl_links['DL Server'] = i['href']
        elif '10Gbps' in i.text and 'workers.dev' in domain:
            res2 = client.get(i['href'])
            soup2 = BeautifulSoup(res2.text, 'html.parser')
            anchor = soup2.find('a', id='vd')
            if anchor:
                dl_links['Resume Server'] = anchor['href']

    if 'Resume Server' in dl_links:
        return quote(dl_links['Resume Server'], safe=":/")
    
    if dl_links:
        return quote(next(iter(dl_links.values())), safe=":/")

    raise DirectDownloadLinkException("No valid direct download link found!")

def real_debrid(url: str, tor=False):
    """ Real-Debrid Link Extractor (VPN Maybe Needed)
    Based on Real-Debrid v1 API (Heroku/VPS) [Without VPN]"""
    def __unrestrict(url, tor=False):
        cget = create_scraper().request
        resp = cget('POST', f"https://api.real-debrid.com/rest/1.0/unrestrict/link?auth_token={config_dict['REAL_DEBRID_API']}", data={'link': url})
        if resp.status_code == 200:
            if tor:
                _res = resp.json()
                return (_res['filename'], _res['download'])
            else:
                return resp.json()['download']
        else:
            raise DirectDownloadLinkException(f"ERROR: {resp.json()['error']}")

    def __addMagnet(magnet):
        cget = create_scraper().request
        hash_ = search(r'(?<=xt=urn:btih:)[a-zA-Z0-9]+', magnet).group(0)
        resp = cget('GET', f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{hash_}?auth_token={config_dict['REAL_DEBRID_API']}")
        if resp.status_code != 200 or len(resp.json()[hash_.lower()]['rd']) == 0:
            return magnet
        resp = cget('POST', f"https://api.real-debrid.com/rest/1.0/torrents/addMagnet?auth_token={config_dict['REAL_DEBRID_API']}", data={'magnet': magnet})
        if resp.status_code == 201:
            _id = resp.json()['id']
        else:
            raise DirectDownloadLinkException(f"ERROR: {resp.json()['error']}")
        if _id:
            _file = cget('POST', f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{_id}?auth_token={config_dict['REAL_DEBRID_API']}", data={'files': 'all'})
            if _file.status_code != 204:
                raise DirectDownloadLinkException(f"ERROR: {resp.json()['error']}")

        contents = {'links': []}
        while len(contents['links']) == 0:
            _res = cget('GET', f"https://api.real-debrid.com/rest/1.0/torrents/info/{_id}?auth_token={config_dict['REAL_DEBRID_API']}")
            if _res.status_code == 200:
                contents = _res.json()
            else:
                raise DirectDownloadLinkException(f"ERROR: {_res.json()['error']}")
            sleep(0.5)

        details = {'contents': [], 'title': contents['original_filename'], 'total_size': contents['bytes']}

        for file_info, link in zip(contents['files'], contents['links']):
            link_info = __unrestrict(link, tor=True)
            item = {
                "path": path.join(details['title'], path.dirname(file_info['path']).lstrip("/")), 
                "filename": unquote(link_info[0]),
                "url": link_info[1],
            }
            details['contents'].append(item)
        return details
    try:
        if tor:
            details = __addMagnet(url)
        else:
            return __unrestrict(url)
    except Exception as e:
        raise DirectDownloadLinkException(e)
    if isinstance(details, dict) and len(details['contents']) == 1:
        return details['contents'][0]['url']
    return details
    
    
def debrid_link(url):
    cget = create_scraper().request
    resp = cget('POST', f"https://debrid-link.com/api/v2/downloader/add?access_token={config_dict['DEBRID_LINK_API']}", data={'url': url}).json()
    if resp['success'] != True:
        raise DirectDownloadLinkException(f"ERROR: {resp['error']} & ERROR ID: {resp['error_id']}")
    if isinstance(resp['value'], dict):
        return resp['value']['downloadUrl']
    elif isinstance(resp['value'], list):
        details = {'contents': [], 'title': unquote(url.rstrip('/').split('/')[-1]), 'total_size': 0}
        for dl in resp['value']:
            if dl.get('expired', False):
                continue
            item = {
                "path": path.join(details['title']),
                "filename": dl['name'],
                "url": dl['downloadUrl']
            }
            if 'size' in dl:
                details['total_size'] += dl['size']
            details['contents'].append(item)
        return details

def get_captcha_token(session, params):
    recaptcha_api = 'https://www.google.com/recaptcha/api2'
    res = session.get(f'{recaptcha_api}/anchor', params=params)
    anchor_html = HTML(res.text)
    if not (anchor_token:= anchor_html.xpath('//input[@id="recaptcha-token"]/@value')):
        return
    params['c'] = anchor_token[0]
    params['reason'] = 'q'
    res = session.post(f'{recaptcha_api}/reload', params=params)
    if token := findall(r'"rresp","(.*?)"', res.text):
        return token[0]
        
def mediafire(url, session=None):
    if '/folder/' in url:
        return mediafireFolder(url)
    if final_link := findall(r'https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+', url):
        return final_link[0]
    if session is None:
        session = Session()
        parsed_url = urlparse(url)
        url = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}'
    try:
        html = HTML(session.get(url).text)
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if error:= html.xpath('//p[@class="notranslate"]/text()'):
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {error[0]}")
    if not (final_link := html.xpath("//a[@id='downloadButton']/@href")):
        session.close()
        raise DirectDownloadLinkException("ERROR: No links found in this page Try Again")
    if final_link[0].startswith('//'):
        return mediafire(f'https://{final_link[0][2:]}', session)
    session.close()
    return final_link[0]


def osdn(url):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        if not (direct_link:= html.xapth('//a[@class="mirror_link"]/@href')):
            raise DirectDownloadLinkException("ERROR: Direct link not found")
        return f'https://osdn.net{direct_link[0]}'


def github(url):
    try:
        findall(r'\bhttps?://.*github\.com.*releases\S+', url)[0]
    except IndexError as e:
        raise DirectDownloadLinkException("No GitHub Releases links found") from e
    with create_scraper() as session:
        _res = session.get(url, stream=True, allow_redirects=False)
        if 'location' in _res.headers:
            return _res.headers["location"]
        raise DirectDownloadLinkException("ERROR: Can't extract the link")

def letsupload(url):
    with create_scraper() as session:
        try:
            res = session.post(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        if direct_link := findall(r"(https?://letsupload\.io\/.+?)\'", res.text):
            return direct_link[0]
        else:
            raise DirectDownloadLinkException('ERROR: Direct Link not found')

def anonfilesBased(url):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        if sa := html.xpath('//*[@id="download-url"]/@href'):
            return sa[0]
        raise DirectDownloadLinkException("ERROR: File not found!")

def onedrive(link):
    with create_scraper() as session:
        try:
            link = session.get(link).url
            parsed_link = urlparse(link)
            link_data = parse_qs(parsed_link.query)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        if not link_data:
            raise DirectDownloadLinkException("ERROR: Unable to find link_data")
        folder_id = link_data.get('resid')
        if not folder_id:
            raise DirectDownloadLinkException('ERROR: folder id not found')
        folder_id = folder_id[0]
        authkey = link_data.get('authkey')
        if not authkey:
            raise DirectDownloadLinkException('ERROR: authkey not found')
        authkey = authkey[0]
        boundary = uuid4()
        headers = {'content-type': f'multipart/form-data;boundary={boundary}'}
        data = f'--{boundary}\r\nContent-Disposition: form-data;name=data\r\nPrefer: Migration=EnableRedirect;FailOnMigratedFiles\r\nX-HTTP-Method-Override: GET\r\nContent-Type: application/json\r\n\r\n--{boundary}--'
        try:
            resp = session.get( f'https://api.onedrive.com/v1.0/drives/{folder_id.split("!", 1)[0]}/items/{folder_id}?$select=id,@content.downloadUrl&ump=1&authKey={authkey}', headers=headers, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if "@content.downloadUrl" not in resp:
        raise DirectDownloadLinkException('ERROR: Direct link not found')
    return resp['@content.downloadUrl']


def pixeldrain(url):
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    if url.split("/")[-2] == "l":
        info_link = f"https://pixeldrain.com/api/list/{file_id}"
        dl_link = f"https://pixeldrain.com/api/list/{file_id}/zip?download"
    else:
        info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
        dl_link = f"https://pixeldrain.com/api/file/{file_id}?download"
    with create_scraper() as session:
        try:
            resp = session.get(info_link).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if resp["success"]:
        return dl_link
    else:
        raise DirectDownloadLinkException(
            f"ERROR: Cant't download due {resp['message']}.")

def streamtape(url):
    splitted_url = url.split("/")
    _id = splitted_url[4] if len(splitted_url) >= 6 else splitted_url[-1]
    try:
        with Session() as session:
            html = HTML(session.get(url).text)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if not (script := html.xpath("//script[contains(text(),'ideoooolink')]/text()")):
        raise DirectDownloadLinkException("ERROR: requeries script not found")
    if not (link := findall(r"(&expires\S+)'", script[0])):
        raise DirectDownloadLinkException("ERROR: Download link not found")
    return f"https://streamtape.com/get_video?id={_id}{link[-1]}"


def racaty(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            json_data = {
                'op': 'download2',
                'id': url.split('/')[-1]
            }
            html = HTML(session.post(url, data=json_data).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if (direct_link := html.xpath("//a[@id='uniqueExpirylink']/@href")):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Direct link not found')


def fichier(link):
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = match(regex, link)
    if not gan:
        raise DirectDownloadLinkException(
            "ERROR: The link you entered is wrong!")
    if "::" in link:
        pswd = link.split("::")[-1]
        url = link.split("::")[-2]
    else:
        pswd = None
        url = link
    cget = create_scraper().request
    try:
        if pswd is None:
            req = cget('post', url)
        else:
            pw = {"pass": pswd}
            req = cget('post', url, data=pw)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if req.status_code == 404:
        raise DirectDownloadLinkException("ERROR: File not found/The link you entered is wrong!")
    html = HTML(req.text)
    if dl_url:= html.xpath('//a[@class="ok btn-general btn-orange"]/@href'):
        return dl_url[0]
    if not (ct_warn := html.xpath('//div[@class="ct_warn"]')):
        raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")
    if len(ct_warn) == 3:
        str_2 = ct_warn[-1].text
        if "you must wait" in str_2.lower():
            if numbers := [int(word) for word in str_2.split() if word.isdigit()]:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
            else:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
        elif "protect access" in str_2.lower():
            raise DirectDownloadLinkException(f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(link)}")
        else:
            raise DirectDownloadLinkException("ERROR: Failed to generate Direct Link from 1fichier!")
    elif len(ct_warn) == 4:
        str_1 = ct_warn[-2].text
        str_3 = ct_warn[-1].text
        if "you must wait" in str_1.lower():
            if numbers := [int(word) for word in str_1.split() if word.isdigit()]:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
            else:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
        elif "bad password" in str_3.lower():
            raise DirectDownloadLinkException("ERROR: The password you entered is wrong!")
    raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")


def solidfiles(url):
    with create_scraper() as session:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'
            }
            pageSource = session.get(url, headers=headers).text
            mainOptions = str(
                search(r'viewerOptions\'\,\ (.*?)\)\;', pageSource).group(1))
            return loads(mainOptions)["downloadUrl"]
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e

def krakenfiles(url):
    with Session() as session:
        try:
            _res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        html = HTML(_res.text)
        if post_url:= html.xpath('//form[@id="dl-form"]/@action'):
            post_url = f'https:{post_url[0]}'
        else:
            raise DirectDownloadLinkException('ERROR: Unable to find post link.')
        if token:= html.xpath('//input[@id="dl-token"]/@value'):
            data = {'token': token[0]}
        else:
            raise DirectDownloadLinkException('ERROR: Unable to find token for post.')
        try:
            _json = session.post(post_url, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__} While send post request') from e
    if _json['status'] != 'ok':
        raise DirectDownloadLinkException("ERROR: Unable to find download after post request")
    return _json['url']

def uploadee(url):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if link := html.xpath("//a[@id='d_l']/@href"):
        return link[0]
    else:
        raise DirectDownloadLinkException("ERROR: Direct Link not found")

def encode_to_base64(input_string):
    encoded_bytes = b64encode(input_string.encode("utf-8"))
    encoded_string = encoded_bytes.decode("utf-8")
    return encoded_string

def parse_size(size_str):
    size_str = str(size_str).strip().upper()
    if size_str.endswith("GB"):
        return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
    elif size_str.endswith("MB"):
        return int(float(size_str[:-2]) * 1024 * 1024)
    elif size_str.endswith("KB"):
        return int(float(size_str[:-2]) * 1024)
    elif size_str.endswith("B"):
        return int(float(size_str[:-1]))
    else:
        try:
            return int(size_str)
        except Exception:
            return 0

def terabox(url):
    cookies = {"ndus": "YQ3MouKteHuig3Qws-VZhyEFjrJ-eRC-Bj7vPZ5h"}
    with Session() as session:
        try:
            res = session.get(url, cookies=cookies)
            shortUrl = parse_qs(urlparse(res.url).query).get('surl')
            if not shortUrl:
                raise DirectDownloadLinkException("Could not find surl")
            shortUrl = "1" + shortUrl[0]
            res_ = session.get(f'https://bingesubscription-o3m2.onrender.com/tera?url={shortUrl}')
            details = eval(res_.text)
        except Exception as e:
            raise DirectDownloadLinkException(str(e))

    def linker(url):
        return 'https://dl.bypassbot.workers.dev/' + encode_to_base64(url)

    details_dict = {
        "contents": [],
        "title": details.get("title", "Terabox Folder"),
        "total_size": 0
    }
    for file in details['contents']:
        details_dict["contents"].append({
            "path": "",
            "filename": file.get("name", ""),
            "url": linker(file["url"])
        })
        if "size" in file:
            try:
                details_dict["total_size"] += parse_size(file["size"])
            except Exception:
                pass
    if len(details_dict["contents"]) == 1:
        return details_dict["contents"][0]["url"]
    return details_dict

def gofile(url, auth):
    try:
        _password = sha256(auth[1].encode("utf-8")).hexdigest() if auth else ""
        _id = url.split("/")[-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")

    def __get_token(session):
        headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        __url = "https://api.gofile.io/accounts"
        try:
            __res = session.post(__url, headers=headers).json()
            if __res["status"] != "ok":
                raise DirectDownloadLinkException("ERROR: Failed to get token.")
            return __res["data"]["token"]
        except Exception as e:
            raise e

    def __fetch_links(session, _id, folderPath=""):
        _url = f"https://api.gofile.io/contents/{_id}?wt=4fd6sg89d7s6&cache=true"
        headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Authorization": "Bearer" + " " + token,
        }
        if _password:
            _url += f"&password={_password}"
        try:
            _json = session.get(_url, headers=headers).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        if _json["status"] in "error-passwordRequired":
            raise DirectDownloadLinkException(
                f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(url)}"
            )
        if _json["status"] in "error-passwordWrong":
            raise DirectDownloadLinkException("ERROR: This password is wrong !")
        if _json["status"] in "error-notFound":
            raise DirectDownloadLinkException(
                "ERROR: File not found on gofile's server"
            )
        if _json["status"] in "error-notPublic":
            raise DirectDownloadLinkException("ERROR: This folder is not public")

        data = _json["data"]

        if not details["title"]:
            details["title"] = data["name"] if data["type"] == "folder" else _id

        contents = data["children"]
        for content in contents.values():
            if content["type"] == "folder":
                if not content["public"]:
                    continue
                if not folderPath:
                    newFolderPath = path.join(details["title"], content["name"])
                else:
                    newFolderPath = path.join(folderPath, content["name"])
                __fetch_links(session, content["id"], newFolderPath)
            else:
                if not folderPath:
                    folderPath = details["title"]
                item = {
                    "path": path.join(folderPath),
                    "filename": content["name"],
                    "url": content["link"],
                }
                if "size" in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details["total_size"] += size
                details["contents"].append(item)

    details = {"contents": [], "title": "", "total_size": 0}
    with Session() as session:
        try:
            token = __get_token(session)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        details["header"] = f"Cookie: accountToken={token}"
        try:
            __fetch_links(session, _id)
        except Exception as e:
            raise DirectDownloadLinkException(e)

    if len(details["contents"]) == 1:
        return (details["contents"][0]["url"], details["header"])
    return details

def gd_index(url, auth):
    if not auth:
        auth = ("admin", "admin")
    try:
        _title = url.rstrip('/').split("/")[-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")

    details = {'contents': [], 'title': unquote(_title), 'total_size': 0}

    def __fetch_links(url, folderPath, username, password):
        with create_scraper() as session:
            payload = {
                "id": "",
                "type": "folder",
                "username": username,
                "password": password,
                "page_token": "",
                "page_index": 0
            }
            try:
                data = (session.post(url, json=payload)).json()
            except:
                raise DirectDownloadLinkException("Use Latest Bhadoo Index Link")
        
        if "data" in data:
            for file_info in data["data"]["files"]:
                if file_info.get("mimeType", "") == "application/vnd.google-apps.folder":
                    if not folderPath: 
                         newFolderPath = path.join(details['title'], file_info["name"]) 
                    else: 
                         newFolderPath = path.join(folderPath, file_info["name"])
                    __fetch_links(f"{url}{file_info['name']}/", newFolderPath, username, password)
                else:
                    if not folderPath:
                        folderPath = details['title']
                    item = { 
                         "path": path.join(folderPath),
                         "filename": unquote(file_info["name"]),
                         "url": urljoin(url, file_info.get("link", "") or ""), 
                     } 
                    if 'size' in file_info:
                         details['total_size'] += int(file_info["size"])
                    details['contents'].append(item)

    try:
        __fetch_links(url, "", auth[0], auth[1])
    except Exception as e:
        raise DirectDownloadLinkException(e)
    if len(details['contents']) == 1:
        return details['contents'][0]['url']
    return details


def filepress(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            raw = urlparse(url)
            json_data = {
                'id': raw.path.split('/')[-1],
                'method': 'publicDownlaod',
            }
            api = f'{raw.scheme}://{raw.hostname}/api/file/downlaod/'
            res = session.post(api, headers={'Referer': f'{raw.scheme}://{raw.hostname}'}, json=json_data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if 'data' not in res:
        raise DirectDownloadLinkException(f'ERROR: {res["statusText"]}')
    return f'https://drive.google.com/uc?id={res["data"]}&export=download'

def jiodrive(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            cookies = {
                    'access_token': config_dict['JIODRIVE_TOKEN']
            }

            data = {
                'id': url.split("/")[-1]
            }

            resp = session.post('https://www.jiodrive.xyz/ajax.php?ajax=download', cookies=cookies, data=data).json()

        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        if resp['code'] != '200':
            raise DirectDownloadLinkException("ERROR: The user's Drive storage quota has been exceeded.")
        return resp['file']
        
def gdtot(url):
    cget = create_scraper().request
    try:
        res = cget('GET', f'https://gdtot.pro/file/{url.split("/")[-1]}')
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    token_url = HTML(res.text).xpath("//a[contains(@class,'inline-flex items-center justify-center')]/@href")
    if not token_url:
        try:
            url = cget('GET', url).url
            p_url = urlparse(url)
            res = cget("POST", f"{p_url.scheme}://{p_url.hostname}/ddl", data={'dl': str(url.split('/')[-1])})
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        if (drive_link := findall(r"myDl\('(.*?)'\)", res.text)) and "drive.google.com" in drive_link[0]:
            return drive_link[0]
        elif config_dict['GDTOT_CRYPT']:
            cget('GET', url, cookies={'crypt': config_dict['GDTOT_CRYPT']})
            p_url = urlparse(url)
            js_script = cget('POST', f"{p_url.scheme}://{p_url.hostname}/dld", data={'dwnld': url.split('/')[-1]})
            g_id = findall('gd=(.*?)&', js_script.text)
            try:
                decoded_id = b64decode(str(g_id[0])).decode('utf-8')
            except:
                raise DirectDownloadLinkException("ERROR: Try in your browser, mostly file not found or user limit exceeded!")
            return f'https://drive.google.com/open?id={decoded_id}'
        else:
            raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer! GDTOT_CRYPT not Provided, it increases efficiency!')
    token_url = token_url[0]
    try:
        token_page = cget('GET', token_url)
    except Exception as e:
        raise DirectDownloadLinkException(
            f'ERROR: {e.__class__.__name__} with {token_url}'
        ) from e
    path = findall('\("(.*?)"\)', token_page.text)
    if not path:
        raise DirectDownloadLinkException('ERROR: Cannot bypass this')
    path = path[0]
    raw = urlparse(token_url)
    final_url = f'{raw.scheme}://{raw.hostname}{path}'
    return sharer_scraper(final_url)


def sharer_scraper(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        raw = urlparse(url)
        header = {"useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10"}
        res = cget('GET', url, headers=header)
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    key = findall('"key",\s+"(.*?)"', res.text)
    if not key:
        raise DirectDownloadLinkException("ERROR: Key not found!")
    key = key[0]
    if not HTML(res.text).xpath("//button[@id='drc']"):
        raise DirectDownloadLinkException("ERROR: This link don't have direct download button")
    boundary = uuid4()
    headers = {
        'Content-Type': f'multipart/form-data; boundary=----WebKitFormBoundary{boundary}',
        'x-token': raw.hostname,
        'useragent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10'
    }

    data = f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n' \
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n' \
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action_token"\r\n\r\n\r\n' \
        f'------WebKitFormBoundary{boundary}--\r\n'
    try:
        res = cget("POST", url, cookies=res.cookies,
                   headers=headers, data=data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if "url" not in res:
        raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer')
    if "drive.google.com" in res["url"]:
        return res["url"]
    try:
        res = cget('GET', res["url"])
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if (drive_link := HTML(res.text).xpath("//a[contains(@class,'btn')]/@href")) and "drive.google.com" in drive_link[0]:
        return drive_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer')



def wetransfer(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            splited_url = url.split('/')
            json_data = {
                'security_hash': splited_url[-1],
                'intent': 'entire_transfer'
            }
            res = session.post(f'https://wetransfer.com/api/v4/transfers/{splited_url[-2]}/download', json=json_data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if "direct_link" in res:
        return res["direct_link"]
    elif "message" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['message']}")
    elif "error" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['error']}")
    else:
        raise DirectDownloadLinkException("ERROR: cannot find direct link")


def akmfiles(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            json_data = {
                'op': 'download2',
                'id': url.split('/')[-1]
            }
            res = session.post('POST', url, data=json_data)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if (direct_link := HTML(res.text).xpath("//a[contains(@class,'btn btn-dow')]/@href")):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Direct link not found')

def shrdsk(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            res = session.get(f'https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={url.split("/")[-1]}')
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if res.status_code != 200:
        raise DirectDownloadLinkException(f'ERROR: Status Code {res.status_code}')
    res = res.json()
    if ("type" in res and res["type"].lower() == "upload" and "video_url" in res):
        return res["video_url"]
    raise DirectDownloadLinkException("ERROR: cannot find direct link")


def linkbox(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            res = session.get(f'https://www.linkbox.to/api/file/detail?itemId={url.split("/")[-1]}').json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if 'data' not in res:
        raise DirectDownloadLinkException('ERROR: Data not found!!')
    data = res['data']
    if not data:
        raise DirectDownloadLinkException('ERROR: Data is None!!')
    if 'itemInfo' not in data:
        raise DirectDownloadLinkException('ERROR: itemInfo not found!!')
    itemInfo = data['itemInfo']
    if 'url' not in itemInfo:
        raise DirectDownloadLinkException('ERROR: url not found in itemInfo!!')
    if "name" not in itemInfo:
        raise DirectDownloadLinkException('ERROR: Name not found in itemInfo!!')
    name = quote(itemInfo["name"])
    raw = itemInfo['url'].split("/", 3)[-1]
    return f'https://wdl.nuplink.net/{raw}&filename={name}'


def route_intercept(route, request):
    if request.resource_type == 'script':
        route.abort()
    else:
        route.continue_()


def mediafireFolder(url):
    try:
        raw = url.split('/', 4)[-1]
        folderkey = raw.split('/', 1)[0]
        folderkey = folderkey.split(',')
    except:
        raise DirectDownloadLinkException('ERROR: Could not parse ')
    if len(folderkey) == 1:
        folderkey = folderkey[0]
    details = {'contents': [], 'title': '', 'total_size': 0, 'header': ''}

    session = req_session()
    adapter = HTTPAdapter(max_retries=Retry(
        total=10, read=10, connect=10, backoff_factor=0.3))
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session = create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False},
        delay=10,
        sess=session,
    )
    folder_infos = []

    def __get_info(folderkey):
        try:
            if isinstance(folderkey, list):
                folderkey = ','.join(folderkey)
            _json = session.post('https://www.mediafire.com/api/1.5/folder/get_info.php', data={
                'recursive': 'yes',
                'folder_key': folderkey,
                'response_format': 'json'
            }).json()
        except Exception as e:
            raise DirectDownloadLinkException(
                f"ERROR: {e.__class__.__name__} While getting info")
        _res = _json['response']
        if 'folder_infos' in _res:
            folder_infos.extend(_res['folder_infos'])
        elif 'folder_info' in _res:
            folder_infos.append(_res['folder_info'])
        elif 'message' in _res:
            raise DirectDownloadLinkException(f"ERROR: {_res['message']}")
        else:
            raise DirectDownloadLinkException("ERROR: something went wrong!")

    try:
        __get_info(folderkey)
    except Exception as e:
        raise DirectDownloadLinkException(e)
    details['title'] = folder_infos[0]["name"]

    def __scraper(url):
        try:
            html = HTML(session.get(url).text)
        except Exception:
            return
        if final_link := html.xpath("//a[@id='downloadButton']/@href"):
            return final_link[0]

    def __get_content(folderKey, folderPath='', content_type='folders'):
        try:
            params = {
                'content_type': content_type,
                'folder_key': folderKey,
                'response_format': 'json',
            }
            _json = session.get(
                'https://www.mediafire.com/api/1.5/folder/get_content.php', params=params).json()
        except Exception as e:
            raise DirectDownloadLinkException(
                f"ERROR: {e.__class__.__name__} While getting content")
        _res = _json['response']
        if 'message' in _res:
            raise DirectDownloadLinkException(f"ERROR: {_res['message']}")
        _folder_content = _res['folder_content']
        if content_type == 'folders':
            folders = _folder_content['folders']
            for folder in folders:
                if folderPath:
                    newFolderPath = path.join(folderPath, folder["name"])
                else:
                    newFolderPath = path.join(folder["name"])
                __get_content(folder['folderkey'], newFolderPath)
            __get_content(folderKey, folderPath, 'files')
        else:
            files = _folder_content['files']
            for file in files:
                item = {}
                if not (_url := __scraper(file['links']['normal_download'])):
                    continue
                item['filename'] = file["filename"]
                if not folderPath:
                    folderPath = details['title']
                item['path'] = path.join(folderPath)
                item['url'] = _url
                if 'size' in file:
                    size = file["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details['total_size'] += size
                details['contents'].append(item)

    try:
        for folder in folder_infos:
            __get_content(folder['folderkey'], folder['name'])
    except Exception as e:
        raise DirectDownloadLinkException(e)
    finally:
        session.close()
    if len(details['contents']) == 1:
        return (details['contents'][0]['url'], details['header'])
    return details


def doods(url):
    if "/e/" in url:
        url = url.replace("/e/", "/d/")
    parsed_url = urlparse(url)
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__} While fetching token link') from e
        if not (link := html.xpath("//div[@class='download-content']//a/@href")):
            raise DirectDownloadLinkException('ERROR: Token Link not found or maybe not allow to download! open in browser.')
        link = f'{parsed_url.scheme}://{parsed_url.hostname}{link[0]}'
        sleep(2)
        try:
            _res = session.get(link)
        except Exception as e:
            raise DirectDownloadLinkException(
                f'ERROR: {e.__class__.__name__} While fetching download link') from e
    if not (link := search(r"window\.open\('(\S+)'", _res.text)):
        raise DirectDownloadLinkException("ERROR: Download link not found try again")
    return (link.group(1), f'Referer: {parsed_url.scheme}://{parsed_url.hostname}/')

def easyupload(url):
    if "::" in url:
        _password = url.split("::")[-1]
        url = url.split("::")[-2]
    else:
        _password = ''
    file_id = url.split("/")[-1]
    with create_scraper() as session:
        try:
            _res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        first_page_html = HTML(_res.text)
        if first_page_html.xpath("//h6[contains(text(),'Password Protected')]") and not _password:
            raise DirectDownloadLinkException(f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(url)}")
        if not (match := search(r'https://eu(?:[1-9][0-9]?|100)\.easyupload\.io/action\.php', _res.text)):
            raise DirectDownloadLinkException("ERROR: Failed to get server for EasyUpload Link")
        action_url = match.group()
        session.headers.update({'referer': 'https://easyupload.io/'})
        recaptcha_params = {
            'k': '6LfWajMdAAAAAGLXz_nxz2tHnuqa-abQqC97DIZ3',
            'ar': '1',
            'co': 'aHR0cHM6Ly9lYXN5dXBsb2FkLmlvOjQ0Mw..',
            'hl': 'en',
            'v': '0hCdE87LyjzAkFO5Ff-v7Hj1',
            'size': 'invisible',
            'cb': 'c3o1vbaxbmwe'
        }
        if not (captcha_token :=get_captcha_token(session, recaptcha_params)):
            raise DirectDownloadLinkException('ERROR: Captcha token not found')
        try:
            data = {'type': 'download-token',
                    'url': file_id,
                    'value': _password,
                    'captchatoken': captcha_token,
                    'method': 'regular'}
            json_resp = session.post(url=action_url, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if 'download_link' in json_resp:
        return json_resp['download_link']
    elif 'data' in json_resp:
        raise DirectDownloadLinkException(
            f"ERROR: Failed to generate direct link due to {json_resp['data']}")
    raise DirectDownloadLinkException(
        "ERROR: Failed to generate direct link from EasyUpload.")



def filelions(url):
    if not config_dict['FILELION_API']:
        raise DirectDownloadLinkException('ERROR: FILELION_API is not provided get it from https://filelions.com/?op=my_account')
    file_code = url.split('/')[-1]
    quality = ''
    if bool(file_code.endswith(('_o', '_h', '_n', '_l'))):
        spited_file_code = file_code.rsplit('_', 1)
        quality = spited_file_code[1]
        file_code = spited_file_code[0]
    parsed_url = urlparse(url)
    url = f'{parsed_url.scheme}://{parsed_url.hostname}/{file_code}'
    with Session() as session:
        try:
            _res = session.get('https://api.filelions.com/api/file/direct_link', params={'key': config_dict['FILELION_API'], 'file_code': file_code, 'hls': '1'}).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if _res['status'] != 200:
        raise DirectDownloadLinkException(f"ERROR: {_res['msg']}")
    result = _res['result']
    if not result['versions']:
        raise DirectDownloadLinkException("ERROR: No versions available")
    error = '\nProvide a quality to download the video\nAvailable Quality:'
    for version in result['versions']:
        if quality == version['name']:
            return version['url']
        elif version['name'] == 'l':
            error += f"\nLow"
        elif version['name'] == 'n':
            error += f"\nNormal"
        elif version['name'] == 'o':
            error += f"\nOriginal"
        elif version['name'] == "h":
            error += f"\nHD"
        error +=f" <code>{url}_{version['name']}</code>"
    raise DirectDownloadLinkException(f'ERROR: {error}')



def streamvid(url: str):
    file_code = url.split('/')[-1]
    parsed_url = urlparse(url)
    url = f'{parsed_url.scheme}://{parsed_url.hostname}/d/{file_code}'
    quality_defined = bool(url.endswith(('_o', '_h', '_n', '_l')))
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if quality_defined:
            data = {}
            if not (inputs := html.xpath('//form[@id="F1"]//input')):
                raise DirectDownloadLinkException('ERROR: No inputs found')
            for i in inputs:
                if key := i.get('name'):
                    data[key] = i.get('value')
            try:
                html = HTML(session.post(url, data=data).text)
            except Exception as e:
                raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
            if not (script := html.xpath('//script[contains(text(),"document.location.href")]/text()')):
                if error := html.xpath('//div[@class="alert alert-danger"][1]/text()[2]'):
                    raise DirectDownloadLinkException(f'ERROR: {error[0]}')
                raise DirectDownloadLinkException("ERROR: direct link script not found!")
            if directLink:=findall(r'document\.location\.href="(.*)"', script[0]):
                return directLink[0]
            raise DirectDownloadLinkException("ERROR: direct link not found! in the script")
        elif (qualities_urls := html.xpath('//div[@id="dl_versions"]/a/@href')) and (qualities := html.xpath('//div[@id="dl_versions"]/a/text()[2]')):
            error = '\nProvide a quality to download the video\nAvailable Quality:'
            for quality_url, quality in zip(qualities_urls, qualities):
                error += f"\n{quality.strip()} <code>{quality_url}</code>"
            raise DirectDownloadLinkException(f'ERROR: {error}')
        elif error:= html.xpath('//div[@class="not-found-text"]/text()'):
            raise DirectDownloadLinkException(f'ERROR: {error[0]}')
        raise DirectDownloadLinkException('ERROR: Something went wrong')
