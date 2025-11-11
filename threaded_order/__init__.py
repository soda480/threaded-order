from importlib import metadata as _metadata
from os import getenv

__all__ = [
    'ThreadedOrder',
    'configure_logging',
    'ThreadProxyLogger',
    '__version__']

def __getattr__(name):
    if name == 'ThreadedOrder':
        from .threaded import ThreadedOrder
        return ThreadedOrder
    if name == 'configure_logging':
        from .logger import configure_logging
        return configure_logging
    if name == 'ThreadProxyLogger':
        from .logger import ThreadProxyLogger
        return ThreadProxyLogger
    raise AttributeError(name)

try:
    __version__ = _metadata.version(__name__)
except _metadata.PackageNotFoundError:
    __version__ = '1.2.0'

if getenv('DEV'):
    __version__ = f'{__version__}+dev'
