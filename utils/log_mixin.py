"""
基于tornado的提供的日志服务
"""
import logging
import settings
import os, re, time
from tornado.options import options
from utils.log_formatter import MyLogFormatter
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler, BaseRotatingHandler


class MyLogger(logging.Logger):

    pass

class SizeTimeHandler(TimedRotatingFileHandler):

    def __init__(self, level, file_prefix, when, backup_count, max_bytes, mode='a', encoding=None, delay=False
                 ,interval=1, ST_MTIME = 8):
        BaseRotatingHandler.__init__(self, file_prefix, mode, encoding, delay)
        self.maxBytes = max_bytes
        self.backupCount = backup_count
        self.when = when.upper()
        self.utc = False
        self.atTime = None
        if self.when == 'S':
            self.interval = 1 # one second
            self.suffix = "%Y-%m-%d_%H-%M-%S"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(\.\w+)?$"
        elif self.when == 'M':
            self.interval = 60 # one minute
            self.suffix = "%Y-%m-%d_%H-%M"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}(\.\w+)?$"
        elif self.when == 'H':
            self.interval = 60 * 60 # one hour
            self.suffix = "%Y-%m-%d_%H"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}_\d{2}(\.\w+)?$"
        elif self.when == 'D' or self.when == 'MIDNIGHT':
            self.interval = 60 * 60 * 24 # one day
            self.suffix = "%Y-%m-%d"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}(\.\w+)?$"
        elif self.when.startswith('W'):
            self.interval = 60 * 60 * 24 * 7 # one week
            if len(self.when) != 2:
                raise ValueError("You must specify a day for weekly rollover from 0 to 6 (0 is Monday): %s" % self.when)
            if self.when[1] < '0' or self.when[1] > '6':
                raise ValueError("Invalid day specified for weekly rollover: %s" % self.when)
            self.dayOfWeek = int(self.when[1])
            self.suffix = "%Y-%m-%d"
            self.extMatch = r"^\d{4}-\d{2}-\d{2}(\.\w+)?$"
        else:
            raise ValueError("Invalid rollover interval specified: %s" % self.when)

        self.extMatch = re.compile(self.extMatch, re.ASCII)
        self.interval = self.interval * interval  # multiply by units requested
        if os.path.exists(file_prefix):
            t = os.stat(file_prefix)[ST_MTIME]
        else:
            t = int(time.time())
        self.rolloverAt = self.computeRollover(t)

    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename("%s.%d" % (self.baseFilename, i))
                dfn = self.rotation_filename("%s.%d" % (self.baseFilename,
                                                        i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.rotation_filename(self.baseFilename + ".1")
            if os.path.exists(dfn):
                os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
        if not self.delay:
            self.stream = self._open()

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        Basically, see if the supplied record would cause the file to exceed
        the size limit we have.
        """
        if self.stream is None:                 # delay was set...
            self.stream = self._open()
        if self.maxBytes > 0:                   # are we rolling over?
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)  #due to non-posix-compliant Windows feature
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return 1
        return 0

class LogMixix(object):


    def _get_logger(self, level_name):
        if hasattr(self.__class__, 'logger_inited'):
            log_base_name = getattr(self.__class__, 'log_base_name')
            min_level = getattr(logging, options.logging.upper())
            if getattr(logging, level_name.upper()) < min_level:
                level_name = options.logging
            logger_name = '%s_%s' % (self.log_base_name, level_name)
            logger = getattr(self.__class__, logger_name)
        else:
            log_to_file = hasattr(options, 'log_to_file') and options.log_to_file
            logging.setLoggerClass(MyLogger)
            if log_to_file and hasattr(self.__class__,"logBaseDir"):
                log_base_name = getattr(self.__class__,"logBaseDir")
            else:
                log_base_name = "default_log"
            setattr(self.__class__, 'log_base_name', log_base_name)
            log_dir = os.path.abspath(os.path.join(settings.log_base_dir, log_base_name))
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            level_names = dict(debug=logging.DEBUG, info=logging.INFO, warning=logging.WARNING, error=logging.ERROR)
            min_level = getattr(logging, options.logging.upper())
            for n,l in level_names.items():
                if l < min_level:
                    continue
                log_name = '%s_%s' % (log_base_name,n)
                logger = self.create_logger(log_name,l)
                if log_to_file:
                    # print('1')
                    path = self.get_log_file(n, log_dir)
                    # time_handler = self.create_TimedRotatingFileHandler(
                    #     l, path, settings.log_rotating_when, settings.log_backup_count
                    # )
                    # size_handler = self.create_RotatingFileHandler(path, l, settings.log_max_bytes, settings.log_backup_count)
                    # logger.addHandler(time_handler)
                    # logger.addHandler(size_handler)
                    handler = self.create_time_size_handler(l, path, settings.log_rotating_when, settings.log_backup_count,
                                                            settings.log_max_bytes)
                    logger.addHandler(handler)
                else:
                    logger = self.create_logger(log_name, l)
                    chanel = logging.StreamHandler()  # 默认的handler
                    file_chanel = logging.FileHandler(self.get_log_file(n, log_dir))
                    formatter = MyLogFormatter(color=True)
                    chanel.setFormatter(formatter)
                    file_chanel.setFormatter(formatter)
                    logger.addHandler(chanel)
                    logger.addHandler(file_chanel)
                setattr(self.__class__, log_name, logger)
            setattr(self.__class__, 'logger_inited', True)

            if getattr(logging, level_name.upper()) < min_level:
                level_name = options.logging

            logger_name = '%s_%s' % (log_base_name,level_name)
            logger = getattr(self.__class__, logger_name)
        return logger

    def create_logger(self, name, level):
        logger = logging.getLogger(name)
        logger.propagate = False
        logger.setLevel(level)
        # logger 默认有多个 handler, 移除自己手动添加
        [logger.removeHandler(h) for h in logger.handlers]
        return logger

    def get_log_file(self, level_name, parent_file):
        """区分不同的日志输出文件"""
        return os.path.join(parent_file, '{}@{}.log'.format(level_name, options.port))

    # 以下是一些高级handler
    def create_RotatingFileHandler(self, file_prefix, level, max_bytes, backup_count):
        """根据大小切割日志"""
        channel = RotatingFileHandler(
            filename=file_prefix, maxBytes=max_bytes, backupCount=backup_count
        )
        channel.setLevel(level)
        channel.setFormatter(MyLogFormatter(color=True))
        return channel

    def create_TimedRotatingFileHandler(self, level, file_prefix, when, backup_count):
        """根据时间切割日志"""
        channel = TimedRotatingFileHandler(
            filename=file_prefix,
            when=when,
            backupCount=backup_count
        )
        channel.setLevel(level)
        channel.setFormatter(MyLogFormatter(color=True))
        return channel

    def create_time_size_handler(self, level, file_prefix, when, backup_count, max_bytes):
        """根据大小和时间共同划分"""
        channel = SizeTimeHandler(level, file_prefix, when, backup_count, max_bytes)
        channel.setLevel(level)
        channel.setFormatter(MyLogFormatter(color=True))
        return channel

    def log_info(self, msg, *args, **kwargs):
        self._get_logger('info').info(msg, *args, **kwargs)

    def log_debug(self, msg, *args, **kwargs):
        self._get_logger('debug').debug(msg, *args, **kwargs)

    def log_warning(self, msg, *args, **kwargs):
        self._get_logger('warning').warning(msg,*args,**kwargs)

    def log_error(self, msg, *args, **kwargs):
        self._get_logger('error').error(msg, *args, **kwargs)


if __name__ == "__main__":

    pass

