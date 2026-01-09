import os
import re
import sys
import threading
import logging
try:
    from colorama import init
    from colorama import Fore, Style
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

if HAS_COLOR:

    class ColoredFormatter(logging.Formatter):
        LEVEL_COLORS = {
            logging.DEBUG: Style.BRIGHT + Fore.CYAN,
            logging.INFO: Style.BRIGHT + Fore.BLUE,
            logging.WARNING: Style.BRIGHT + Fore.YELLOW,
            logging.ERROR: Style.BRIGHT + Fore.RED,
            logging.CRITICAL: Style.BRIGHT + Fore.RED,
        }
        DEFAULT_HIGHLIGHTS = [
            (re.compile(r'\bPASSED\b', re.IGNORECASE), Fore.GREEN),
            (re.compile(r'\bFAILED\b', re.IGNORECASE), Fore.RED),
            (re.compile(r'\bSKIPPED\b', re.IGNORECASE), Fore.YELLOW),
            (re.compile(r'Scheduler::State:\s*(\{.*?^})', re.DOTALL | re.MULTILINE), Fore.MAGENTA)
        ]

        def __init__(self, workers, *args, **kwargs):
            self.highlights = kwargs.pop('highlights', []) or self.DEFAULT_HIGHLIGHTS
            self.verbose = kwargs.pop('verbose', False)
            self.workers = workers
            super().__init__(*args, **kwargs)

        def _apply_highlights(self, message):
            out = message
            for pattern, color in self.highlights:
                def replace(m):
                    text = m.group(0)
                    return f'{color}{text}{Style.RESET_ALL}{Fore.WHITE}'
                out = pattern.sub(replace, out)
            return out

        def format(self, record):
            timestamp = self.formatTime(record, self.datefmt)
            level_color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)

            raw_msg = record.getMessage()
            colored_msg = self._apply_highlights(raw_msg)

            # only log thread name if it's not MainThread
            # to avoid cluttering the logs with 'MainThread' entries
            if record.threadName == 'MainThread':
                thread_name = ''
            else:
                thread_name = f'[{self.pad_thread_name(record.threadName)}] '

            if self.verbose:
                msg = (
                    f"{Style.DIM}{timestamp}{Style.RESET_ALL} "
                    f"{level_color}{record.levelname:<5}{Style.RESET_ALL} "
                    f"{thread_name}"
                    f"{Fore.WHITE}{record.funcName}: {colored_msg}{Style.RESET_ALL}"
                )
            else:
                msg = (
                    f"{Style.DIM}{timestamp}{Style.RESET_ALL} "
                    f"{thread_name}"
                    f"{colored_msg}{Style.RESET_ALL}"
                )
            if record.exc_info:
                msg += '\n' + self.formatException(record.exc_info)

            return msg

        def pad_thread_name(self, name):
            width = len(str(self.workers - 1))
            return re.sub(r'(\d+)$', lambda m: m.group(1).zfill(width), name)

class MainThreadAwareFormatter(logging.Formatter):
    def __init__(self, main_fmt, thread_fmt, workers, thread_prefix='thread_', *args, **kwargs):
        super().__init__(fmt=main_fmt, *args, **kwargs)
        self.main_fmt = main_fmt
        self.thread_fmt = thread_fmt
        self.thread_prefix = thread_prefix
        self.thread_width = len(str(workers - 1))

    def format(self, record):
        if record.threadName.startswith(self.thread_prefix):
            try:
                idx = int(record.threadName[len(self.thread_prefix):])
                padded = f'{self.thread_prefix}{idx:0{self.thread_width}d}'
            except ValueError:
                padded = record.threadName
        else:
            padded = record.threadName
        
        record.paddedThreadName = padded

        if record.threadName == 'MainThread':
            self._style._fmt = self.main_fmt
        else:
            self._style._fmt = self.thread_fmt
        return super().format(record)

class ThreadProxyLogger:
    def __getattr__(self, name):
        return getattr(logging.getLogger(threading.current_thread().name), name)

def configure_logging(workers, prefix='thread', add_stream_handler=False, highlights=None,
                      verbose=False):

    root_logger = logging.getLogger()
    if getattr(root_logger, '_logging_initialized', False):
        return

    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    file_formatter = logging.Formatter(
        '%(asctime)s %(levelname)-5s [%(threadName)s] %(funcName)s: %(message)s')

    if add_stream_handler or verbose:
        if HAS_COLOR:
            init(autoreset=False)
            stream_formatter = ColoredFormatter(workers, highlights=highlights, verbose=verbose)
        else:
            main_fmt = '%(asctime)s %(message)s'
            thread_fmt = '%(asctime)s [%(paddedThreadName)s] %(message)s'
            stream_formatter = MainThreadAwareFormatter(main_fmt, thread_fmt, workers)

        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(stream_formatter)
        stream_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        root_logger.addHandler(stream_handler)

        root_logger._logging_initialized = True

    base = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    def add_handler(name):
        filename = f'{base}_{name}.log'
        logger = logging.getLogger(name)
        if not any(
            isinstance(handler, logging.FileHandler)
            and getattr(handler, 'baseFilename', '').endswith(filename)
            for handler in logger.handlers
        ):
            fhandler = logging.FileHandler(filename, mode='a', encoding='utf-8')
            fhandler.setLevel(logging.DEBUG)
            fhandler.setFormatter(file_formatter)
            logger.addHandler(fhandler)
        logger.setLevel(logging.DEBUG)
        return logger

    add_handler(threading.current_thread().name)
    for index in range(workers):
        add_handler(f'{prefix}_{index}')
