import os
import sys
import logging

def configure_logging(workers, prefix='thread', main_thread='thread_M'):
    shandler = logging.StreamHandler()
    shandler.setLevel(logging.INFO)
    shandler.setFormatter(logging.Formatter("%(asctime)s: %(message)s", "%Y-%m-%d %H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(shandler)

    base = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    formatter = logging.Formatter(
        "%(asctime)s [%(threadName)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")

    def add_handler(name):
        filename = f'{base}_{name}.log'
        logger = logging.getLogger(name)
        if not any(
            isinstance(handler, logging.FileHandler)
            and getattr(handler, 'baseFilename', '').endswith(filename)
            for handler in logger.handlers):
            fhandler = logging.FileHandler(filename, mode='a', encoding='utf-8')
            fhandler.setLevel(logging.DEBUG)
            fhandler.setFormatter(formatter)
            logger.addHandler(fhandler)
        logger.setLevel(logging.DEBUG)
        return logger

    add_handler(main_thread)
    for index in range(workers):
        add_handler(f'{prefix}_{index}')
