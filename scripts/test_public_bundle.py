"""Exercise the public check against staged files in an isolated repository."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class PublicBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='public-bundle-test-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        scripts = self.repo / 'scripts'
        scripts.mkdir()
        self.check = scripts / 'check_public_bundle.py'
        shutil.copy2(Path(__file__).with_name(self.check.name), self.check)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)

    def run_check(self):
        subprocess.run(['git', 'add', '--all'], cwd=self.repo, check=True)
        return subprocess.run([sys.executable, '-B', str(self.check)],
                              capture_output=True, text=True)

    def test_generic_text_passes(self):
        (self.repo / 'README.md').write_text('A fictional code teaching example.\n')
        self.assertEqual(self.run_check().returncode, 0)

    def test_private_assets_and_locations_fail(self):
        cases = [
            ('.env', 'configuration=value'),
            ('recording.mp3', 'not a real recording'),
            ('README.md', '/Users/' + 'example/private/file.py'),
            ('README.md', 'AKIA' + 'A' * 16),
        ]
        for name, content in cases:
            with self.subTest(name=name):
                target = self.repo / name
                target.write_text(content)
                result = self.run_check()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(name + ':', result.stderr)
                self.assertNotIn(content, result.stderr)
                target.unlink()

    def test_symlinks_fail(self):
        (self.repo / 'link.py').symlink_to('scripts/check_public_bundle.py')
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('symlinks', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
