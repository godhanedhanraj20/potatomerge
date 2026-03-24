import re, urllib.parse
from hashlib import md5
from time import strftime, gmtime, time
from re import sub as re_sub, search as re_search
from shlex import split as ssplit
from natsort import natsorted
from os import path as ospath
from aiofiles.os import remove as aioremove, path as aiopath, mkdir, makedirs, listdir
from aioshutil import rmtree as aiormtree
from contextlib import suppress
from asyncio import create_subprocess_exec, create_task, gather, Semaphore
from asyncio.subprocess import PIPE
from telegraph import upload_file
from langcodes import Language

from bot import bot_cache, LOGGER, MAX_SPLIT_SIZE, config_dict, user_data
from bot.modules.mediainfo import parseinfo
from bot.helper.ext_utils.bot_utils import cmd_exec, sync_to_async, get_readable_file_size, get_readable_time
from bot.helper.ext_utils.fs_utils import ARCH_EXT, get_mime_type
from bot.helper.ext_utils.telegraph_helper import telegraph, telup


async def is_multi_streams(path):
    try:
        result = await cmd_exec(["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format",
                                 "json", "-show_streams", path])
        if res := result[1]:
            LOGGER.warning(f'Get Video Streams: {res}')
    except Exception as e:
        LOGGER.error(f'Get Video Streams: {e}. Mostly File not found!')
        return False
    fields = eval(result[0]).get('streams')
    if fields is None:
        LOGGER.error(f"get_video_streams: {result}")
        return False
    videos = 0
    audios = 0
    for stream in fields:
        if stream.get('codec_type') == 'video':
            videos += 1
        elif stream.get('codec_type') == 'audio':
            audios += 1
    return videos > 1 or audios > 1


async def get_media_info(path, metadata=False):
    try:
        result = await cmd_exec(["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format",
                                 "json", "-show_format", "-show_streams", path])
        if res := result[1]:
            LOGGER.warning(f'Media Info FF: {res}')
    except Exception as e:
        LOGGER.error(f'Media Info: {e}. Mostly File not found!')
        return (0, "", "", "") if metadata else (0, None, None)
    ffresult = eval(result[0])
    fields = ffresult.get('format')
    if fields is None:
        LOGGER.error(f"Media Info Sections: {result}")
        return (0, "", "", "") if metadata else (0, None, None)
    duration = round(float(fields.get('duration', 0)))
    if metadata:
        lang, qual, stitles = "", "", ""
        if (streams := ffresult.get('streams')) and streams[0].get('codec_type') == 'video':
            qual = int(streams[0].get('height'))
            qual = f"{480 if qual <= 480 else 540 if qual <= 540 else 720 if qual <= 720 else 1080 if qual <= 1080 else 2160 if qual <= 2160 else 4320 if qual <= 4320 else 8640}p"
            for stream in streams:
                if stream.get('codec_type') == 'audio' and (lc := stream.get('tags', {}).get('language')):
                    with suppress(Exception):
                        lc = Language.get(lc).display_name()
                    if lc not in lang:
                        lang += f"{lc}, "
                if stream.get('codec_type') == 'subtitle' and (st := stream.get('tags', {}).get('language')):
                    with suppress(Exception):
                        st = Language.get(st).display_name()
                    if st not in stitles:
                        stitles += f"{st}, "
        return duration, qual, lang[:-2], stitles[:-2]
    tags = fields.get('tags', {})
    artist = tags.get('artist') or tags.get('ARTIST') or tags.get("Artist")
    title = tags.get('title') or tags.get('TITLE') or tags.get("Title")
    return duration, artist, title


async def get_document_type(path):
    is_video, is_audio, is_image = False, False, False
    if path.endswith(tuple(ARCH_EXT)) or re_search(r'.+(\.|_)(rar|7z|zip|bin)(\.0*\d+)?$', path):
        return is_video, is_audio, is_image
    mime_type = await sync_to_async(get_mime_type, path)
    if mime_type.startswith('audio'):
        return False, True, False
    if mime_type.startswith('image'):
        return False, False, True
    if not mime_type.startswith('video') and not mime_type.endswith('octet-stream'):
        return is_video, is_audio, is_image
    try:
        result = await cmd_exec(["ffprobe", "-hide_banner", "-loglevel", "error", "-print_format",
                                 "json", "-show_streams", path])
        if res := result[1]:
            LOGGER.warning(f'Get Document Type: {res}')
    except Exception as e:
        LOGGER.error(f'Get Document Type: {e}. Mostly File not found!')
        return is_video, is_audio, is_image
    fields = eval(result[0]).get('streams')
    if fields is None:
        LOGGER.error(f"get_document_type: {result}")
        return is_video, is_audio, is_image
    for stream in fields:
        if stream.get('codec_type') == 'video':
            is_video = True
        elif stream.get('codec_type') == 'audio':
            is_audio = True
    return is_video, is_audio, is_image


async def get_audio_thumb(audio_file):
    des_dir = 'Thumbnails'
    if not await aiopath.exists(des_dir):
        await mkdir(des_dir)
    des_dir = ospath.join(des_dir, f"{time()}.jpg")
    cmd = [bot_cache['pkgs'][2], "-hide_banner", "-loglevel", "error",
           "-i", audio_file, "-an", "-vcodec", "copy", des_dir]
    status = await create_subprocess_exec(*cmd, stderr=PIPE)
    if await status.wait() != 0 or not await aiopath.exists(des_dir):
        err = (await status.stderr.read()).decode().strip()
        LOGGER.error(
            f'Error while extracting thumbnail from audio. Name: {audio_file} stderr: {err}')
        return None
    return des_dir


async def take_ss(video_file, duration=None, total=1, gen_ss=False):
    des_dir = ospath.join('Thumbnails', f"{time()}")
    await makedirs(des_dir, exist_ok=True)
    if duration is None:
        duration = (await get_media_info(video_file))[0]
    if duration == 0:
        duration = 3
    duration = duration - (duration * 2 / 100)
    cmd = [bot_cache['pkgs'][2], "-hide_banner", "-loglevel", "error", "-ss", "",
           "-i", video_file, "-vf", "thumbnail", "-frames:v", "1", des_dir]
    tstamps = {}
    thumb_sem = Semaphore(3)
    
    async def extract_ss(eq_thumb):
        async with thumb_sem:
            cmd[5] = str((duration // total) * eq_thumb)
            tstamps[f"wz_thumb_{eq_thumb}.jpg"] = strftime("%H:%M:%S", gmtime(float(cmd[5])))
            cmd[-1] = ospath.join(des_dir, f"wz_thumb_{eq_thumb}.jpg")
            task = await create_subprocess_exec(*cmd, stderr=PIPE)
            return (task, await task.wait(), eq_thumb)
    
    tasks = [extract_ss(eq_thumb) for eq_thumb in range(1, total+1)]
    status = await gather(*tasks)
    
    for task, rtype, eq_thumb in status:
        if rtype != 0 or not await aiopath.exists(ospath.join(des_dir, f"wz_thumb_{eq_thumb}.jpg")):
            err = (await task.stderr.read()).decode().strip()
            LOGGER.error(f'Error while extracting thumbnail no. {eq_thumb} from video. Name: {video_file} stderr: {err}')
            await aiormtree(des_dir)
            return None
    return (des_dir, tstamps) if gen_ss else ospath.join(des_dir, "wz_thumb_1.jpg")


async def split_file(path, size, file_, dirpath, split_size, listener, start_time=0, i=1, inLoop=False, multi_streams=True):
    if listener.suproc == 'cancelled' or listener.suproc is not None and listener.suproc.returncode == -9:
        return False
    if listener.seed and not listener.newDir:
        dirpath = f"{dirpath}/splited_files_mltb"
        if not await aiopath.exists(dirpath):
            await mkdir(dirpath)
    user_id = listener.message.from_user.id
    user_dict = user_data.get(user_id, {})
    leech_split_size = user_dict.get(
        'split_size') or config_dict['LEECH_SPLIT_SIZE']
    parts = -(-size // leech_split_size)
    if (user_dict.get('equal_splits') or config_dict['EQUAL_SPLITS'] and 'equal_splits' not in user_dict) and not inLoop:
        split_size = ((size + parts - 1) // parts) + 1000
    if (await get_document_type(path))[0]:
        if multi_streams:
            multi_streams = await is_multi_streams(path)
        duration = (await get_media_info(path))[0]
        base_name, extension = ospath.splitext(file_)
        split_size -= 5000000
        while i <= parts or start_time < duration - 4:
            parted_name = f"{base_name}.part{i:03}{extension}"
            out_path = ospath.join(dirpath, parted_name)
            cmd = [bot_cache['pkgs'][2], "-hide_banner", "-loglevel", "error", "-ss", str(start_time), "-i", path,
                   "-fs", str(split_size), "-map", "0", "-map_chapters", "-1", "-async", "1", "-strict",
                   "-2", "-c", "copy", out_path]
            if not multi_streams:
                del cmd[10]
                del cmd[10]
            if listener.suproc == 'cancelled' or listener.suproc is not None and listener.suproc.returncode == -9:
                return False
            listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
            code = await listener.suproc.wait()
            if code == -9:
                return False
            elif code != 0:
                err = (await listener.suproc.stderr.read()).decode().strip()
                try:
                    await aioremove(out_path)
                except Exception:
                    pass
                if multi_streams:
                    LOGGER.warning(
                        f"{err}. Retrying without map, -map 0 not working in all situations. Path: {path}")
                    return await split_file(path, size, file_, dirpath, split_size, listener, start_time, i, True, False)
                else:
                    LOGGER.warning(
                        f"{err}. Unable to split this video, if it's size less than {MAX_SPLIT_SIZE} will be uploaded as it is. Path: {path}")
                return "errored"
            out_size = await aiopath.getsize(out_path)
            if out_size > MAX_SPLIT_SIZE:
                dif = out_size - MAX_SPLIT_SIZE
                split_size -= dif + 5000000
                await aioremove(out_path)
                return await split_file(path, size, file_, dirpath, split_size, listener, start_time, i, True, )
            lpd = (await get_media_info(out_path))[0]
            if lpd == 0:
                LOGGER.error(
                    f'Something went wrong while splitting, mostly file is corrupted. Path: {path}')
                break
            elif duration == lpd:
                LOGGER.warning(
                    f"This file has been splitted with default stream and audio, so you will only see one part with less size from orginal one because it doesn't have all streams and audios. This happens mostly with MKV videos. Path: {path}")
                break
            elif lpd <= 3:
                await aioremove(out_path)
                break
            start_time += lpd - 3
            i += 1
    else:
        out_path = ospath.join(dirpath, f"{file_}.")
        listener.suproc = await create_subprocess_exec("split", "--numeric-suffixes=1", "--suffix-length=3",
                                                       f"--bytes={split_size}", path, out_path, stderr=PIPE)
        code = await listener.suproc.wait()
        if code == -9:
            return False
        elif code != 0:
            err = (await listener.suproc.stderr.read()).decode().strip()
            LOGGER.error(err)
    return True

async def extract_media_info(filename):
    filename = urllib.parse.unquote(filename)
    filename = re.sub(r'www\S+', '', filename)
    filename = re.sub(r'\.[a-zA-Z0-9]{2,4}$', '', filename)
    filename = re.sub(r'[\._\-]+', ' ', filename)
    filename = re.sub(r'\[.*?\]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    filename = re.sub(r'^[@/\\]\w+\s*', '', filename)
    translations = {
        "Эпизод": "E",
        "エピソード": "E",
        "Saison": "Season",
        "Volumen": "Vol",
        "Часть": "Part"
    }
    for key, val in translations.items():
        filename = filename.replace(key, val)

    resolution_match = re.search(r'\b(480p|720p|1080p|2160p|4K|8K)\b', filename, re.IGNORECASE)
    resolution = resolution_match.group(1) if resolution_match else None

    pattern = re.compile(
        r"""
        (?P<name>.*?)\s*
        (?:\((?P<year>\d{4})\)|
            (?P<year_alt>\d{4})|
            S(?P<season>\d{1,2})\s*[\.\-]?\s*E(?P<episode>\d{1,3})|
            S(?P<season2>\d{1,2})|
            Season\s*(?P<season3>\d{1,2})|
            Episode\s*(?P<episode2>\d{1,3})|
            Part\s*(?P<part>\d{1,2})|
            Vol\s*(?P<volume>\d{1,2})
        )
        """,
        re.VERBOSE | re.IGNORECASE,
    )
    match = pattern.search(filename)
    if match:
        name = match.group("name").strip()
        name = re.sub(
            r'\b(480p|720p|1080p|Hindi|WEB DL|x264|AAC|Zee5|BluRay|HDRip|HQ|DD\+5 1|DD\+5|5 1|192Kbps|Tamil|English|HEVC|H264|10bit|NF|AMZN|WEBRip|DVDRip|UNCUT|Dual Audio|Esubs|Atmos|DTS|TrueHD|Multi|AAC2 0|AAC5 1|AC3|ESub|Subs|Opus|FLAC|MP3|MPEG|AVC|Remux|Proper|Repack|Complete|Limited|Exclusive|Prime|Hotstar|Disney|Netflix|SonyLiv|MXPlayer|Voot|ALTBalaji|Ullu|Kooku|PrimeShots|RabbitMovies|BigMovieZoo|BoomMovies|Voovi|Besharams|MoodX|XPrime|Cineprime|PrimePlay|HuntCinema|DigiMovieplex|Wow|FlizMovies|Balloon|Stream|HD|SD|CAMRip|TS|PreDVD|PreRip|Line Audio|Cleaned|Sample|Trailer|South Movie ORG|Movie ORG)\b',
            '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+', ' ', name).strip()
        year = match.group("year") or match.group("year_alt")
        season = match.group("season") or match.group("season2") or match.group("season3")
        episode = match.group("episode") or match.group("episode2")
        part = match.group("part")
        volume = match.group("volume")
        return name, season, episode, year, part, volume, resolution

    cleaned_name = re.sub(
        r'\b(480p|720p|1080p|Hindi|WEB DL|x264|AAC|Zee5|BluRay|HDRip|HQ|DD\+5 1|DD\+5|5 1|192Kbps|Tamil|English|HEVC|H264|10bit|NF|AMZN|WEBRip|DVDRip|UNCUT|Dual Audio|Esubs|Atmos|DTS|TrueHD|Multi|AAC2 0|AAC5 1|AC3|ESub|Subs|Opus|FLAC|MP3|MPEG|AVC|Remux|Proper|Repack|Complete|Limited|Exclusive|Prime|Hotstar|Disney|Netflix|SonyLiv|MXPlayer|Voot|ALTBalaji|Ullu|Kooku|PrimeShots|RabbitMovies|BigMovieZoo|BoomMovies|Voovi|Besharams|MoodX|XPrime|Cineprime|PrimePlay|HuntCinema|DigiMovieplex|Wow|FlizMovies|Balloon|Stream|HD|SD|CAMRip|TS|PreDVD|PreRip|Line Audio|Cleaned|Sample|Trailer|South Movie ORG|Movie ORG)\b',
        '', filename, flags=re.IGNORECASE)
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    print(f"Unmatched filename: {filename}")
    return cleaned_name, None, None, None, None, None, None

async def format_filename(file_, user_id, dirpath=None, isMirror=False):
    user_dict = user_data.get(user_id, {})
    ftag, ctag = ('m', 'MIRROR') if isMirror else ('l', 'LEECH')
    prefix = config_dict[f'{ctag}_FILENAME_PREFIX'] if (val := user_dict.get(f'{ftag}prefix', '')) == '' else val
    remname = config_dict[f'{ctag}_FILENAME_REMNAME'] if (val := user_dict.get(f'{ftag}remname', '')) == '' else val
    suffix = config_dict[f'{ctag}_FILENAME_SUFFIX'] if (val := user_dict.get(f'{ftag}suffix', '')) == '' else val
    lcaption = config_dict['LEECH_FILENAME_CAPTION'] if (val := user_dict.get('lcaption', '')) == '' else val
    autorename = user_dict.get(f'{ftag}autorename', '')

    prefile_ = file_
    file_cleaned = re.sub(r'www\S+', '', file_)

    name, season, episode, year, part, volume, resolution = await extract_media_info(file_cleaned)

    episode_str = f"EP{episode}" if episode else ''
    season_str = f"S{season}" if season else ''
    part_str = f"Part{part}" if part else ''
    volume_str = f"Vol{volume}" if volume else ''
    quality = resolution or ''

    up_path = ospath.join(dirpath, prefile_) if dirpath else None
    try:
        file_size = get_readable_file_size(await aiopath.getsize(up_path)) if up_path else ''
    except:
        file_size = ''

    _, ext = ospath.splitext(file_cleaned)
    name_only = name

    # Apply all filename transformations first
    if autorename:
        # Create a dictionary of parameters that have values
        params = {}
        if episode_str: params['episode'] = episode_str
        if season_str: params['season'] = season_str
        if part_str: params['part'] = part_str
        if volume_str: params['volume'] = volume_str
        if quality: params['quality'] = quality
        if name_only: params['filename'] = name_only
        if file_size: params['size'] = file_size
        if year: params['year'] = year
        
        # Parse the autorename template to extract parts and separators
        try:
            # Split template by curly braces to get parts and separators
            template_parts = re.split(r'\{([^}]+)\}', autorename)
            
            # Rebuild the filename using only parameters that have values
            new_filename = ''
            last_param_pos = -1  # Track position of last parameter that had a value
            
            for i in range(len(template_parts)):
                if i % 2 == 1:  # This is a parameter (odd indices)
                    param = template_parts[i]
                    if param in params:
                        # If we had a previous parameter with value, add ONE separator between them
                        if last_param_pos >= 0:
                            # Get the separator directly after the last parameter with value
                            sep_idx = last_param_pos + 1
                            if sep_idx < len(template_parts):
                                # Always use the exact separator from the template
                                new_filename += template_parts[sep_idx]
                        
                        # Add the parameter value
                        new_filename += str(params[param])
                        last_param_pos = i
                elif i == 0:  # First separator (prefix)
                    new_filename += template_parts[i]
                elif i == len(template_parts)-1 and last_param_pos >= 0:  # Last separator (suffix)
                    new_filename += template_parts[i]
            
            # DO NOT clean up spaces - preserve exact format
            # new_filename = re.sub(r'\s+', ' ', new_filename)
            
            # If filename was successfully built, use it
            if new_filename:
                file_ = new_filename + ext
            else:
                file_ = file_cleaned
        except Exception as e:
            LOGGER.error(f"Error in autorename formatting: {str(e)}")
            # Fallback to basic formatting
            try:
                file_ = autorename.format(
                    episode=episode_str,
                    season=season_str,
                    part=part_str,
                    volume=volume_str,
                    quality=quality,
                    filename=name_only,
                    size=file_size,
                    year=year
                ) + ext
            except:
                file_ = file_cleaned
    else:
        file_ = file_cleaned

    if remname:
        if not remname.startswith('|'):
            remname = f"|{remname}"
        remname = remname.replace('\s', ' ')
        slit = remname.split("|")
        __newFileName = ospath.splitext(file_)[0]
        for rep in range(1, len(slit)):
            args = slit[rep].split(":")
            if len(args) == 3:
                __newFileName = re.sub(args[0], args[1], __newFileName, int(args[2]))
            elif len(args) == 2:
                __newFileName = re.sub(args[0], args[1], __newFileName)
            elif len(args) == 1:
                __newFileName = re.sub(args[0], '', __newFileName)
        file_ = __newFileName + ospath.splitext(file_)[1]

    if prefix:
        prefix = prefix.replace('\s', ' ')
        # Add a space after prefix if it doesn't end with one and file doesn't start with one
        if not prefix.endswith(' ') and not file_.startswith(' '):
            prefix = f"{prefix} "
        if not file_.lower().startswith(prefix.lower()):
            file_ = f"{prefix}{file_}"

    if suffix and not isMirror:
        suffix = suffix.replace('\s', ' ')
        # Add a space before suffix if it doesn't start with one and _extOutName doesn't end with one
        if not suffix.startswith(' '):
            suffix = f" {suffix}"
        sufLen = len(suffix)
        fileDict = file_.split('.')
        _extIn = 1 + len(fileDict[-1])
        # Don't replace dots with spaces
        _extOutName = '.'.join(fileDict[:-1])
        _newExtFileName = f"{_extOutName}{suffix}.{fileDict[-1]}"
        if len(_extOutName) > (64 - (sufLen + _extIn)):
            _newExtFileName = (_extOutName[:64 - (sufLen + _extIn)] + f"{suffix}.{fileDict[-1]}")
        file_ = _newExtFileName
    elif suffix:
        suffix = suffix.replace('\s', ' ')
        # Add a space before suffix if it doesn't start with one
        if not suffix.startswith(' '):
            suffix = f" {suffix}"
        file_ = f"{ospath.splitext(file_)[0]}{suffix}{ospath.splitext(file_)[1]}" if '.' in file_ else f"{file_}{suffix}"

    # Now set base_filename_for_caption to the fully transformed file_
    base_filename_for_caption = file_

    # Now generate caption
    cap_mono = ''
    if lcaption and dirpath and not isMirror:
        def lowerVars(match): return f"{{{match.group(1).lower()}}}"
        lcaption_tmp = lcaption.replace('\|', '%%').replace('\{', '&%&').replace('\}', '$%$').replace('\s', ' ')
        slit = lcaption_tmp.split("|")
        slit[0] = re.sub(r'\{([^}]+)\}', lowerVars, slit[0])
        try:
            dur, qual, lang, subs = await get_media_info(up_path, True)
        except:
            dur, qual, lang, subs = '', '', '', ''
        cap_mono = slit[0].format(
            filename=base_filename_for_caption,
            size=file_size,
            duration=get_readable_time(dur),
            quality=qual,
            languages=lang,
            subtitles=subs,
            md5_hash=get_md5_hash(up_path),
            episode=episode_str,
            season=season_str,
            part=part_str,
            volume=volume_str,
            year=year or ''
        )
        if len(slit) > 1:
            for rep in range(1, len(slit)):
                args = slit[rep].split(":")
                if len(args) == 3:
                    cap_mono = cap_mono.replace(args[0], args[1], int(args[2]))
                elif len(args) == 2:
                    cap_mono = cap_mono.replace(args[0], args[1])
                elif len(args) == 1:
                    cap_mono = cap_mono.replace(args[0], '')
        cap_mono = cap_mono.replace('%%', '|').replace('&%&', '{').replace('$%$', '}')
    else:
        cap_mono = base_filename_for_caption

    if config_dict['CAP_FONT']:
        cap_mono = f"<{config_dict['CAP_FONT']}>{cap_mono}</{config_dict['CAP_FONT']}>"

    return file_, cap_mono

async def get_ss(up_path, ss_no):
    thumbs_path, tstamps = await take_ss(up_path, total=min(ss_no, 250), gen_ss=True)
    th_html = f"📌 <h4>{ospath.basename(up_path)}</h4><br>📇 <b>Total Screenshots:</b> {ss_no}<br><br>"
    up_sem = Semaphore(25)
    async def telefile(thumb):
        async with up_sem:
            tele_id = await telup(ospath.join(thumbs_path, thumb))
            return tele_id, tstamps[thumb]
    tasks = [telefile(thumb) for thumb in natsorted(await listdir(thumbs_path))]
    results = await gather(*tasks)
    th_html += ''.join(f'<img src="{tele_id}"><br><pre>Screenshot at {stamp}</pre>' for tele_id, stamp in results)
    await aiormtree(thumbs_path)
    link_id = (await telegraph.create_page(title="ScreenShots X", content=th_html))["path"]
    return f"https://graph.org/{link_id}"


async def get_mediainfo_link(up_path):
    stdout, __, _ = await cmd_exec(ssplit(f'mediainfo "{up_path}"'))
    tc = f"📌 <h4>{ospath.basename(up_path)}</h4><br><br>"
    if len(stdout) != 0:
        tc += parseinfo(stdout)
    link_id = (await telegraph.create_page(title="MediaInfo X", content=tc))["path"]
    return f"https://graph.org/{link_id}"


def get_md5_hash(up_path):
    md5_hash = md5()
    with open(up_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
        return md5_hash.hexdigest()
