from importlib import metadata as _metadata
from os import getenv

__all__ = ['Threaded', 'configure_logging', '__version__']

def __getattr__(name):
    if name == 'Threaded':
        from .threaded import Threaded
        return Threaded
    if name == 'configure_logging':
        from .logger import configure_logging
        return configure_logging
    raise AttributeError(name)

try:
    __version__ = _metadata.version(__name__)
except _metadata.PackageNotFoundError:
    __version__ = '1.0.0'

if getenv('DEV'):
    __version__ = f'{__version__}+dev'
