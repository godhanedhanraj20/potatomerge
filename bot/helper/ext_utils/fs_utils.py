#!/usr/bin/env python3
import json, os, subprocess, re, tempfile, asyncio, concurrent.futures
from random import randint
from os import walk, path as ospath, replace as osreplace, remove, rename
from aiofiles.os import remove as aioremove, path as aiopath, listdir, rmdir, makedirs
from aioshutil import rmtree as aiormtree, move
from shutil import rmtree, disk_usage
from json import loads as jsonloads
from magic import Magic
from asyncio import create_subprocess_exec, gather, sleep, Queue, Lock
from asyncio.subprocess import PIPE
from re import split as re_split, I, search as re_search, findall, sub as re_sub
from subprocess import run as srun
from sys import exit as sexit
from time import time
from typing import List, Tuple

from .exceptions import NotSupportedExtractionArchive
from bot import bot_cache, config_dict, aria2, LOGGER, DOWNLOAD_DIR, get_client, GLOBAL_EXTENSION_FILTER, cpu_no, bot_loop, download_dict
from bot.helper.ext_utils.bot_utils import sync_to_async, cmd_exec

ARCH_EXT = [".tar.bz2", ".tar.gz", ".bz2", ".gz", ".tar.xz", ".tar", ".tbz2", ".tgz", ".lzma2",
            ".zip", ".7z", ".z", ".rar", ".iso", ".wim", ".cab", ".apm", ".arj", ".chm",
            ".cpio", ".cramfs", ".deb", ".dmg", ".fat", ".hfs", ".lzh", ".lzma", ".mbr",
            ".msi", ".mslz", ".nsis", ".ntfs", ".rpm", ".squashfs", ".udf", ".vhd", ".xar"]

FIRST_SPLIT_REGEX = r'(\.|_)part0*1\.rar$|(\.|_)7z\.0*1$|(\.|_)zip\.0*1$|^(?!.*(\.|_)part\d+\.rar$).*\.rar$'

SPLIT_REGEX = r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$'

def is_first_archive_split(file):
    return bool(re_search(FIRST_SPLIT_REGEX, file))


def is_archive(file):
    return file.endswith(tuple(ARCH_EXT))


def is_archive_split(file):
    return bool(re_search(SPLIT_REGEX, file))


async def clean_target(path):
    if await aiopath.exists(path):
        LOGGER.info(f"Cleaning Target: {path}")
        if await aiopath.isdir(path):
            try:
                await aiormtree(path)
            except Exception:
                pass
        elif await aiopath.isfile(path):
            try:
                await aioremove(path)
            except Exception:
                pass


async def clean_download(path):
    if await aiopath.exists(path):
        LOGGER.info(f"Cleaning Download: {path}")
        try:
            await aiormtree(path)
        except Exception:
            pass


async def start_cleanup():
    get_client().torrents_delete(torrent_hashes="all")
    try:
        await aiormtree(DOWNLOAD_DIR)
    except Exception:
        pass
    await makedirs(DOWNLOAD_DIR, exist_ok=True)


def clean_all():
    aria2.remove_all(True)
    get_client().torrents_delete(torrent_hashes="all")
    try:
        rmtree(DOWNLOAD_DIR)
    except Exception:
        pass


def exit_clean_up(signal, frame):
    try:
        LOGGER.info(
            "Please wait, while we clean up and stop the running downloads")
        clean_all()
        srun(['pkill', '-9', '-f', f'gunicorn|{bot_cache["pkgs"][-1]}'])
        sexit(0)
    except KeyboardInterrupt:
        LOGGER.warning("Force Exiting before the cleanup finishes!")
        sexit(1)


async def clean_unwanted(path):
    LOGGER.info(f"Cleaning unwanted files/folders: {path}")
    for dirpath, _, files in await sync_to_async(walk, path, topdown=False):
        for filee in files:
            if filee.endswith(".!qB") or filee.endswith('.parts') and filee.startswith('.'):
                await aioremove(ospath.join(dirpath, filee))
        if dirpath.endswith((".unwanted", "splited_files_mltb", "copied_mltb")):
            await aiormtree(dirpath)
    for dirpath, _, files in await sync_to_async(walk, path, topdown=False):
        if not await listdir(dirpath):
            await rmdir(dirpath)


async def get_path_size(path):
    if await aiopath.isfile(path):
        return await aiopath.getsize(path)
    total_size = 0
    for root, dirs, files in await sync_to_async(walk, path):
        for f in files:
            abs_path = ospath.join(root, f)
            total_size += await aiopath.getsize(abs_path)
    return total_size


async def count_files_and_folders(path):
    total_files = 0
    total_folders = 0
    for _, dirs, files in await sync_to_async(walk, path):
        total_files += len(files)
        for f in files:
            if f.endswith(tuple(GLOBAL_EXTENSION_FILTER)):
                total_files -= 1
        total_folders += len(dirs)
    return total_folders, total_files


def get_base_name(orig_path):
    extension = next(
        (ext for ext in ARCH_EXT if orig_path.lower().endswith(ext)), ''
    )
    if extension != '':
        return re_split(f'{extension}$', orig_path, maxsplit=1, flags=I)[0]
    else:
        raise NotSupportedExtractionArchive(
            'File format not supported for extraction')


def get_mime_type(file_path):
    mime = Magic(mime=True)
    mime_type = mime.from_file(file_path)
    mime_type = mime_type or "text/plain"
    return mime_type


def check_storage_threshold(size, threshold, arch=False, alloc=False):
    free = disk_usage(DOWNLOAD_DIR).free
    if not alloc:
        if (not arch and free - size < threshold or arch and free - (size * 2) < threshold):
            return False
    elif not arch:
        if free < threshold:
            return False
    elif free - size < threshold:
        return False
    return True


async def join_files(path):
    files = await listdir(path)
    results = []
    for file_ in files:
        if re_search(r"\.0+2$", file_) and await sync_to_async(get_mime_type, f'{path}/{file_}') == 'application/octet-stream':
            final_name = file_.rsplit('.', 1)[0]
            cmd = f'cat {path}/{final_name}.* > {path}/{final_name}'
            _, stderr, code = await cmd_exec(cmd, True)
            if code != 0:
                LOGGER.error(f'Failed to join {final_name}, stderr: {stderr}')
            else:
                results.append(final_name)
        else:
            LOGGER.warning('No Binary files to join!')
    if results:
        LOGGER.info('Join Completed!')
        for res in results:
            for file_ in files:
                if re_search(fr"{res}\.0[0-9]+$", file_):
                    await aioremove(f'{path}/{file_}')

async def get_audio_info(input_file: str) -> List[Tuple[str, int, int]]:
    
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a', 
           '-show_entries', 'stream=codec_name,bit_rate,channels,codec_type', 
           '-of', 'json', input_file]

    try:
        output = subprocess.check_output(cmd).decode('utf-8')
        audio_info = json.loads(output)
        return [(stream['codec_name'], 
                 int(stream['bit_rate']) // 1000 if stream.get('bit_rate') else '0', 
                 stream['channels'])
                for stream in audio_info['streams'] if stream.get('codec_type') == 'audio']
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"Error getting audio info: {e}")
        return []
    except json.JSONDecodeError as e:
        LOGGER.error(f"Error decoding JSON from ffprobe output: {e}")
        return []
        
async def edit_metadata(listener, base_dir: str, media_file: str, outfile: str, metadata: str = ''):
    # Construct the ffmpeg command to update only necessary metadata (title) and remove unwanted fields
    cmd = [
        bot_cache['pkgs'][2], '-hide_banner', '-ignore_unknown', '-i', media_file,
        # Set 'title' metadata and remove unwanted fields
        '-metadata', f'title={metadata}',
        '-metadata:s:v', f'title={metadata}',
        '-metadata:s:a', f'title={metadata}',
        '-metadata:s:s', f'title={metadata}',

        # Remove unwanted metadata fields
        '-metadata', 'Description=', 
        '-metadata', 'Copyright=', 
        '-metadata', 'Comment=', 
        '-metadata', 'AUTHOR=', 
        '-metadata', 'SUMMARY=',
        '-metadata', 'WEBSITE=',
        '-metadata', 'DATE=',
        '-metadata', 'Encoded_by=',

        '-map', '0:v:0?',   # Map video stream
        '-map', '0:a:?',    # Map audio stream
        '-map', '0:s:?',    # Map subtitle stream
        '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'copy',  # Copy streams without re-encoding
        outfile, '-y'       # Output file and overwrite
    ]

    listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
    code = await listener.suproc.wait()

    if code == 0:
        await clean_target(media_file)
        listener.seed = False
        await move(outfile, base_dir)
    else:
        error_msg = (await listener.suproc.stderr.read()).decode()
        await clean_target(outfile)
        LOGGER.error(f'Changing metadata failed for {media_file}. Error: {error_msg}')

async def add_attachment(listener, base_dir: str, media_file: str, outfile: str, attach: str = ''):
    attachment_ext = attach.split(".")[-1].lower()
    mime_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
    }.get(attachment_ext, "application/octet-stream")

    cmd = [
        bot_cache['pkgs'][2], '-hide_banner', '-ignore_unknown', '-i', media_file,
        '-attach', attach, '-metadata:s:t', f'mimetype={mime_type}',
        '-c', 'copy', '-map', '0', outfile, '-y'
    ]

    listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
    code = await listener.suproc.wait()

    if code == 0:
        await clean_target(media_file)  
        listener.seed = False
        await move(outfile, base_dir)  
    else:
        stderr_output = await listener.suproc.stderr.read()
        LOGGER.error(
            '%s. Adding Attachment failed, Path %s', stderr_output.decode(), media_file
        )
        await clean_target(outfile)  
                
async def get_media_info(path: str):
    try:
        result = await cmd_exec(['ffprobe', '-hide_banner', '-loglevel', 'error', '-print_format', 'json', '-show_format', path])
        if res := result[1]:
            LOGGER.warning('Get Media Info: %s', res)
    except Exception as e:
        LOGGER.error('Get Media Info: %s. Mostly File not found!', e)
        return 0, None, None
    if result[0] and result[2] == 0:
        fields = jsonloads(result[0]).get('format')
        if fields is None:
            LOGGER.error('Get_media_info: %s', result)
            return 0, None, None
        duration = round(float(fields.get('duration', 0)))
        tags = fields.get('tags', {})
        artist = tags.get('artist') or tags.get('ARTIST') or tags.get('Artist')
        title = tags.get('title') or tags.get('TITLE') or tags.get('Title')
        return duration, artist, title
    return 0, None, None

class FFProgress:
    def __init__(self):
        self.outfile = ''
        self._duration = 0
        self._start_time = time()
        self._eta = 0
        self._percentage = '0%'
        self._processed_bytes = 0
    @property
    def processed_bytes(self):
        return self._processed_bytes
    @property
    def percentage(self):
        return self._percentage
    @property
    def eta(self):
        return self._eta
    @property
    def speed(self):
        return self._processed_bytes / (time() - self._start_time)
    @staticmethod
    async def read_lines(stream):
        data = bytearray()
        while not stream.at_eof():
            lines = re_split(br'[\r\n]+', data)
            data[:] = lines.pop(-1)
            for line in lines:
                yield line
            data.extend(await stream.read(1024))
    async def progress(self, status: str=''):
        start_time = time()
        async for line in self.read_lines(self.listener.suproc.stderr):
            if self.listener.suproc.returncode is not None:
                return
            if progress := dict(findall(r'(frame|fps|size|time|bitrate|speed)\s*\=\s*(\S+)', line.decode('utf-8').strip())):
                if not self._duration:
                    self._duration = (await get_media_info(self.path))[0]
                hh, mm, sms = progress['time'].split(':')
                time_to_second = (int(hh) * 3600) + (int(mm) * 60) + float(sms)
                self._processed_bytes = int(re_search(r'\d+', progress['size']).group()) * 1024
                self._percentage = f'{round((time_to_second / self._duration) * 100, 2)}%'
                try:
                    self._eta = (self._duration / float(progress['speed'].strip('x'))) - (time() - start_time)
                except:
                    pass
class Watermark(FFProgress):
    def __init__(self, listener):
        self.listener = listener
        self.path = ''
        self.name = ''
        self.size = 0
        self._start_time = time()
        super().__init__()
    async def add_watermark(self, media_file: str, wm_position: str, wm_size: str):
        self.path = media_file
        self.size = await get_path_size(media_file)
        base_file, _ = ospath.splitext(media_file)
        if media_file.endswith(".mkv"):
            self.outfile = f'{base_file}_HB.mkv'
        else:
            self.outfile = f'{base_file}_HB.mp4'
        self.name = ospath.basename(self.outfile)
        cmd = [bot_cache['pkgs'][2], '-hide_banner', '-y', '-threads', f'{max(1, cpu_no // 2)}', '-i', media_file, '-i', f'/usr/src/wm/{self.listener.user_id}.png','-filter_complex',
        f"[1][0]scale2ref=w='iw*{wm_size}/100':h='ow/mdar'[wm][vid];[vid][wm]overlay={wm_position}",
        '-crf', config_dict['FFMPEG_CRF'], '-preset', config_dict['LIB264_PRESET'], '-map', '0:a:?', '-map', '0:s:?', '-c:a', 'copy', '-c:s', 'copy', self.outfile]
        self.listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
        _, code = await gather(self.progress(), self.listener.suproc.wait())
        if code == 0:
            await clean_target(media_file)
            self.listener.seed = False
            rename(self.outfile, media_file)
            self.outfile = media_file
            return self.outfile
        if code == -9:
            self.suproc = 'cancelled'
            return False
        await clean_target(self.outfile)
        LOGGER.error('%s. Watermarking failed, Path %s', (await self.listener.suproc.stderr.read()).decode(), media_file)
        return media_file

async def edit_audioremove(listener, base_dir: str, media_file: str, outfile: str, audioremove: str = ''):    
    audio_keys = audioremove.split(',')
    cmd = [
        bot_cache['pkgs'][2],
        '-hide_banner',
        '-i', media_file,
        '-map', '0:v:0',
        '-map', '0:a',
        '-map', '0:s',
    ]
    for audio_key in audio_keys:
        cmd.extend(['-map', f'-0:a:{audio_key}'])
    cmd.extend([
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-c:s', 'copy',
        '-y',
        outfile
    ])  
    listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
    code = await listener.suproc.wait()
    
    if code == 0:
        await clean_target(media_file)
        listener.seed = False
        await move(outfile, base_dir)
    else:
        await clean_target(outfile)
        LOGGER.error('%s. Removing Audio Failed, Path %s', await listener.suproc.stderr.read().decode(), media_file)

async def get_audio_stream_count(file_path):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', file_path]
    process = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        err = stderr.decode().strip()
        LOGGER.error(f"FFprobe error: {err}")
        raise RuntimeError(f"FFprobe failed with error: {err}")
    return len(stdout.decode().strip().split('\n'))

async def edit_audiochange(listener, base_dir: str, media_file: str, outfile: str, audiochange: str = ''): 
    LOGGER.info(f"Starting audio modification for file: {media_file}")
    try:
        audio_stream_count = await get_audio_stream_count(media_file)
    except Exception as e:
        LOGGER.error(f"Failed to get audio stream count for file {media_file}: {str(e)}")
        return media_file

    audio_keys = audiochange.split(',')

    if len(audio_keys) > audio_stream_count:
        LOGGER.error(f"Invalid key format: {audiochange}. More indices provided than available audio streams ({audio_stream_count}).")
        return media_file        
    try:
        audio_keys = [int(key) for key in audio_keys]
        if any(key < 0 or key >= audio_stream_count for key in audio_keys):
            raise ValueError("Audio key indices are out of range.")
    except ValueError:
        LOGGER.error(f"Invalid audio key indices: {audiochange}. All indices must be integers within the range of available audio streams.")
        return media_file

    cmd = [
        bot_cache['pkgs'][2],
        '-hide_banner',
        '-i', media_file,
        '-map', '0:v:0',
    ]

    for audio_key in audio_keys:
        cmd.extend(['-map', f'0:a:{audio_key}'])
        
    cmd.extend([
        '-c:v', 'copy',
        '-c:a', 'copy', 
        '-map', '0:s?', '-c:s', 'copy',  
        '-y',
        outfile
    ])

    listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
    code = await listener.suproc.wait()

    if code == 0:
        await clean_target(media_file)
        listener.seed = False
        await move(outfile, base_dir)
    else:
        await clean_target(outfile)
        LOGGER.error('%s. Changing Audio Failed, Path %s', await listener.suproc.stderr.read().decode(), media_file)

async def intro_subedit(listener, base_dir: str, media_file: str, outfile: str, introsub: str, clean_regex: str = None, replace_text: str = ""):
    try:
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 's',
            '-show_entries', 'stream=index:stream_tags=language',
            '-of', 'json', media_file
        ]

        listener.suproc = await create_subprocess_exec(*probe_cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = await listener.suproc.communicate()

        raw_output = stdout.decode().strip()
        if not raw_output:
            LOGGER.error(f"ffprobe returned empty output.\nstderr: {stderr.decode().strip()}")
            return

        try:
            probe_data = json.loads(raw_output)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to parse ffprobe output as JSON: {e}\nOutput: {raw_output}")
            return

        subtitle_streams = probe_data.get("streams", [])

        temp_dir = tempfile.mkdtemp()
        input_args = ['-i', media_file]
        map_args = ['-map', '0:v?', '-map', '0:a?', '-map', '0:t?']
        metadata_args = []
        index_offset = 0

        if subtitle_streams:
            for i, stream in enumerate(subtitle_streams):
                lang = stream.get("tags", {}).get("language", "und")
                s_index = stream.get("index")
                sub_path = os.path.join(temp_dir, f"sub_{i}.srt")

                extract_cmd = [
                    bot_cache['pkgs'][2], '-hide_banner', '-y',
                    '-i', media_file,
                    '-map', f"0:s:{i}",
                    '-c:s', 'srt',
                    sub_path
                ]
                listener.suproc = await create_subprocess_exec(*extract_cmd, stderr=PIPE)
                await listener.suproc.wait()

                if not os.path.exists(sub_path):
                    LOGGER.warning(f"Subtitle extraction failed for stream {i}")
                    continue

                with open(sub_path, 'r', encoding='utf-8') as f:
                    subs = f.read()

                if clean_regex:
                    subs = re.sub(clean_regex, replace_text, subs)

                match = re.findall(r'^(\d+)\s*$', subs, re.MULTILINE)
                next_index = int(match[-1]) + 1 if match else 1
                intro_block = f"\n{next_index}\n00:00:05,000 --> 00:00:30,000\n{introsub.strip()}\n"
                subs += intro_block

                with open(sub_path, 'w', encoding='utf-8') as f:
                    f.write(subs)

                input_args.extend(['-i', sub_path])
                map_args.extend(["-map", f"{i + 1}:s:0"])
                metadata_args.extend([
                    f"-metadata:s:s:{index_offset}", f"language={lang}",
                    f"-disposition:s:{index_offset}", "default"
                ])
                index_offset += 1
        else:
            new_sub = os.path.join(temp_dir, 'new_intro.srt')
            with open(new_sub, 'w', encoding='utf-8') as f:
                f.write(f"1\n00:00:05,000 --> 00:00:30,000\n{introsub.strip()}\n")

            input_args.extend(['-i', new_sub])
            map_args.append(f"-map 1:s:0")
            metadata_args.extend([
                "-metadata:s:s:0", "language=eng",
                "-disposition:s:0", "default"
            ])

        subtitle_codec = 'mov_text' if media_file.endswith('.mp4') else 'subrip'

        remux_cmd = [bot_cache['pkgs'][2], '-hide_banner', '-y'] + input_args + [
            '-c:v', 'copy', '-c:a', 'copy', '-c:s', subtitle_codec, '-c:t', 'copy'
        ] + map_args + metadata_args + [outfile]

        listener.suproc = await create_subprocess_exec(*remux_cmd, stderr=PIPE)
        code = await listener.suproc.wait()

        if code == 0:
            # LOGGER.info('Intro Edited Successfully')
            await clean_target(media_file)
            listener.seed = False
            await move(outfile, base_dir)
        else:
            stderr_output = await listener.suproc.stderr.read()
            LOGGER.error(f"Failed to edit subtitle: {stderr_output.decode().strip()}")
            await clean_target(outfile)

    except Exception as e:
        LOGGER.error(f"Error in Intro Subedit: {str(e)}")

async def trim_video(listener, base_dir: str, media_file: str, outfile: str, trim_times: str = ''):
    try:
        if not trim_times or len(trim_times.split()) != 2:
            LOGGER.error(f"Invalid trim format: {trim_times}. Expected 'HH:MM:SS HH:MM:SS'")
            return
            
        start_time, end_time = trim_times.split()

        time_pattern = re.compile(r'^\d{2}:\d{2}:\d{2}$')
        if not time_pattern.match(start_time) or not time_pattern.match(end_time):
            LOGGER.error(f"Invalid time format. Expected HH:MM:SS, got {start_time} and {end_time}")
            return
            
        if not outfile:
            base_file, ext = os.path.splitext(media_file)
            outfile = f'{base_file}_trimmed{ext}'

        cmd = [
            bot_cache['pkgs'][2], '-hide_banner', '-y',
            '-i', media_file,
            '-ss', start_time,
            '-to', end_time,
            '-map', '0:v:0?',  
            '-map', '0:a:?',   
            '-map', '0:s:?',  
            '-map', '0:t?',    
            '-c:v', 'copy',    
            '-c:a', 'copy',   
            '-c:s', 'copy',    
            '-c:t', 'copy',    
            '-avoid_negative_ts', 'make_zero',  
            outfile
        ]

        if listener.suproc == 'cancelled':
            return
            
        listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
        code = await listener.suproc.wait()
        
        if code == 0:
            await clean_target(media_file)
            listener.seed = False
            await move(outfile, base_dir)
        else:
            stderr_output = await listener.suproc.stderr.read()
            LOGGER.error(f"Failed to trim video: {stderr_output.decode().strip()}")
            await clean_target(outfile)
            
    except Exception as e:
        LOGGER.error(f"Error in trim_video: {str(e)}")
