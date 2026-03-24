from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import create_subprocess_exec, sleep, gather
from natsort import natsorted
from os import path as ospath, walk
from time import time

from bot import bot_loop, download_dict, download_dict_lock, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.fs_utils import get_path_size, clean_target
from bot.helper.ext_utils.leech_utils import get_document_type
from bot.helper.mirror_utils.status_utils.merge_status import MergeStatus
from bot.helper.telegram_helper.message_utils import update_all_messages


class Merge:
    def __init__(self, listener):
        self.__listener = listener
        self.__processed_bytes = 0
        self.__start_time = time()

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    @property
    def speed(self):
        return self.__processed_bytes / (time() - self.__start_time)

    async def __progress(self, outfile):
        while True:
            await sleep(1)
            if await aiopath.exists(outfile):
                self.__processed_bytes = await get_path_size(outfile)

    async def merge_vids(self, path, gid):
        list_files, remove_files, size = [], [], 0
        for dirpath, _, files in await sync_to_async(walk, path):
            for file in natsorted(files):
                video_file = ospath.join(dirpath, file)
                if (await get_document_type(video_file))[0]:
                    size += await get_path_size(video_file)
                    list_files.append(f"file '{video_file}'")
                    remove_files.append(video_file)
        if len(list_files) > 1:
            name = ospath.basename(path)
            async with download_dict_lock:
                download_dict[self.__listener.uid] = MergeStatus(name, size, gid, self, self.__listener)
            await update_all_messages()
            input_file = ospath.join(path, 'input.txt')
            async with aiopen(input_file, 'w') as f:
                await f.write('\n'.join(list_files))
            LOGGER.info(f'Merging {len(list_files)} videos --> {name}')
            outfile = f'{ospath.join(path, name)}.mkv'
            cmd = ['ffmpeg', '-ignore_unknown', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', input_file, '-map', '0', '-c', 'copy', outfile]
            self.__listener.suproc = await create_subprocess_exec(*cmd)
            task = bot_loop.create_task(self.__progress(outfile))
            code = await self.__listener.suproc.wait()
            task.cancel()
            if self.__listener.suproc == 'cancelled' or code == -9:
                return
            elif code == 0:
                await clean_target(input_file)
                if not self.__listener.seed:
                    await gather(*[clean_target(file) for file in remove_files])
                LOGGER.info(f'Merge successfully with name: {name}.mkv')
            else:
                LOGGER.error(f'Failed to merge: {name}.mkv')
        return True
