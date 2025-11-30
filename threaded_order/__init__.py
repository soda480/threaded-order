from importlib import metadata as _metadata
from os import getenv

__all__ = [
    'Scheduler',
    'DAGraph',
    'configure_logging',
    'ThreadProxyLogger',
    'dmark',
    'tag'
    '__version__']

def __getattr__(name):
    if name == 'Scheduler':
        from .scheduler import Scheduler
        return Scheduler
    if name == 'DAGraph':
        from .graph import DAGraph
        return DAGraph
    if name == 'configure_logging':
        from .logger import configure_logging
        return configure_logging
    if name == 'ThreadProxyLogger':
        from .logger import ThreadProxyLogger
        return ThreadProxyLogger
    if name == 'dmark':
        from .scheduler import dmark
        return dmark
    if name == 'tag':
        from .scheduler import tag
        return tag
    raise AttributeError(name)

try:
    __version__ = _metadata.version(__name__)
except _metadata.PackageNotFoundError:
    __version__ = '1.5.0'

if getenv('DEV'):
    __version__ = f'{__version__}+dev'
