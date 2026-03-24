from time import time
from bot import LOGGER
from bot.helper.ext_utils.bot_utils import EngineStatus, MirrorStatus, get_readable_file_size, get_readable_time


class WatermarkStatus:
    def __init__(self, listener, obj, gid):
        self.listener = listener
        self._gid = gid
        self._obj = obj
        self._time = time()
        self.upload_details = listener.upload_details
        self.message = listener.message

    def gid(self):
        return self._gid

    def progress(self):
        return self._obj.percentage

    def speed(self):
        return f'{get_readable_file_size(self._obj.speed)}/s'

    def name(self):
        return self._obj.name
    def size(self):
        return get_readable_file_size(self._obj.size)

    def eta(self):
        return get_readable_time(self._obj.eta)

    def status(self):
        return MirrorStatus.STATUS_WATERMARK

    def elapsed(self):
        return get_readable_time(time() - self._time)

    def processed_bytes(self):
        return get_readable_file_size(self._obj.processed_bytes)

    def download(self):
        return self

    async def cancel_download(self):
        LOGGER.info('Cancelling watermak: %s', self.name())
        if self.listener.suproc and self.listener.suproc.returncode is None:
            self.listener.suproc.kill()
        self.listener.suproc = 'cancelled'
        await self.listener.onUploadError('Watermark has stopped by user!')

    def eng(self):
        return EngineStatus().STATUS_SPLIT_MERGE
