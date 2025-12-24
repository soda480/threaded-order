import importlib
import os
import sys
import unittest
from unittest import mock

PKG = 'threaded_order'

class TestInitModule(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop(PKG, None)

    def _reload_pkg(self):
        mod = importlib.import_module(PKG)
        return importlib.reload(mod)

    def test___getattr___covers_all_lazy_exports(self):
        pkg = self._reload_pkg()

        Scheduler = getattr(pkg, 'Scheduler')
        DAGraph = getattr(pkg, 'DAGraph')
        configure_logging = getattr(pkg, 'configure_logging')
        ThreadProxyLogger = getattr(pkg, 'ThreadProxyLogger')
        dmark = getattr(pkg, 'dmark')
        mark = getattr(pkg, 'mark')
        default_workers = getattr(pkg, 'default_workers')

        self.assertEqual(Scheduler.__name__, 'Scheduler')
        self.assertEqual(DAGraph.__name__, 'DAGraph')
        self.assertEqual(configure_logging.__name__, 'configure_logging')
        self.assertEqual(ThreadProxyLogger.__name__, 'ThreadProxyLogger')
        self.assertEqual(dmark.__name__, 'dmark')
        self.assertEqual(mark.__name__, 'mark')
        self.assertTrue(isinstance(default_workers, int))

    def test___getattr___unknown_raises_attributeerror(self):
        pkg = self._reload_pkg()
        with self.assertRaises(AttributeError) as cm:
            getattr(pkg, 'DoesNotExist')
        self.assertEqual(str(cm.exception), 'DoesNotExist')

    def test_version_falls_back_when_metadata_missing(self):
        with mock.patch(f'{PKG}._metadata.version') as mv:
            tmp = importlib.import_module(PKG)
            pnf = tmp._metadata.PackageNotFoundError
            sys.modules.pop(PKG, None)

            mv.side_effect = pnf
            pkg = self._reload_pkg()

        self.assertIsNotNone(pkg.__version__, '1.6.3')

    def test_version_appends_dev_suffix_when_DEV_set(self):
        with mock.patch(f'{PKG}._metadata.version', return_value='9.9.9'):
            with mock.patch.dict(os.environ, {'DEV': '1'}, clear=False):
                sys.modules.pop(PKG, None)
                pkg = self._reload_pkg()

        self.assertEqual(pkg.__version__, '9.9.9+dev')

    def test_version_no_dev_suffix_when_DEV_not_set(self):
        with mock.patch(f'{PKG}._metadata.version', return_value='9.9.9'):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop('DEV', None)
                sys.modules.pop(PKG, None)
                pkg = self._reload_pkg()

        self.assertEqual(pkg.__version__, '9.9.9')
