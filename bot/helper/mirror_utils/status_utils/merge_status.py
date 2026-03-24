from bot import LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, MirrorStatus, EngineStatus, get_readable_time


class MergeStatus:
    def __init__(self, name, size, gid, obj, listener):
        self.__name = name
        self.__gid = gid
        self.__size = size
        self.__obj = obj
        self.upload_details = listener.upload_details
        self.__listener = listener
        self.message = listener.message

    def processed_bytes(self):
        return get_readable_file_size(self.__obj.processed_bytes)

    def gid(self):
        return self.__gid

    def progress(self):
        try:
            progress_raw = self.__obj.processed_bytes / self.__size * 100
        except:
            progress_raw = 0
        return f'{round(progress_raw, 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    def name(self):
        return self.__name

    def size(self):
        return get_readable_file_size(self.__size)

    def eta(self):
        try:
            return get_readable_time((self.__size - self.__obj.processed_bytes) / self.__obj.speed)
        except:
            return '~'

    def status(self):
        return MirrorStatus.STATUS_MERGING

    def download(self):
        return self

    async def cancel_download(self):
        LOGGER.info(f'Cancelling Merge: {self.__name}')
        if self.__listener.suproc:
            self.__listener.suproc.kill()
        else:
            self.__listener.suproc = 'cancelled'
        await self.__listener.onUploadError('Merged stopped by user!')

    def eng(self):
        return EngineStatus().STATUS_SPLIT_MERGE
