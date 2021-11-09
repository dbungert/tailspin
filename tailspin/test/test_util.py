
from contextlib import contextmanager
import os
from tailspin import util
import tempfile
import unittest


@contextmanager
def tmpdir_curdir():
    with tempfile.TemporaryDirectory() as tdir:
        try:
            saved_cwd = os.getcwd()
            os.chdir(tdir)
            yield tdir
        finally:
            os.chdir(saved_cwd)


class TestLogfileName(unittest.TestCase):
    def test_range(self):
        actual = [x for x in range(1, 3)]
        self.assertEqual([1, 2], actual)

    def test_logdir_name(self):
        with tmpdir_curdir() as tdir:
            actual = util.create_logdir()
            self.assertEqual('logs/001', actual)
            self.assertTrue(os.path.isdir(actual))
            actual = os.path.abspath(actual)

            self.assertEqual('logs/002', util.create_logdir())

        self.assertFalse(os.path.exists(actual))

    def test_generate_logfile_name(self):
        mapping = {
            'a': 'a',
            '/b': 'b',
            './c': 'c',
            './d/e/f': 'd-e-f',
            '/g/h': 'g-h',
            '../i': 'i',
            '../j/k.l/m-n/./o': 'j-k.l-m-n-o',
        }
        basedir = 'mycooldirname'
        for key in mapping.keys():
            actual = util.generate_logfile_name(key, basedir, 27)
            expected = f'{basedir}/{mapping[key]}-0027.log'
            self.assertEqual(expected, actual)

    def test_adjust_runid(self):
        mapping = {
            1: '0001',
            20: '0020',
            300: '0300',
            4000: '4000',
        }
        basedir = 'mycooldirname'
        for key in mapping.keys():
            actual = util.generate_logfile_name('foo', basedir, key)
            expected = f'{basedir}/foo-{mapping[key]}.log'
            self.assertEqual(expected, actual)
