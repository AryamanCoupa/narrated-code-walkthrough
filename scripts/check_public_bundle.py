#!/usr/bin/env python3
"""Check tracked public-package files for selected accidental disclosures.

This is a small packaging check, not proof that arbitrary source is public-safe.
Review new content and its provenance before publishing it.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DENIED_SUFFIXES = {'.wav', '.mp3', '.mp4', '.onnx', '.bin', '.pem', '.key', '.pyc', '.zip'}
PATTERNS = [
    ('personal filesystem path', re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/')),
    ('temporary machine path', re.compile(r'/private/(?:tmp|var)/')),
    ('private-key header', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('AWS access-key ID', re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('GitHub token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b')),
]


def main():
    listed = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached'], cwd=ROOT
    ).decode().split('\0')
    errors = []
    count = 0
    for name in filter(None, listed):
        path = ROOT / name
        count += 1
        if path.is_symlink():
            errors.append(f'{name}: symlinks are not part of the standalone bundle')
            continue
        if (path.suffix.lower() in DENIED_SUFFIXES
                or any(part.startswith('.env') for part in path.parts)
                or any(part in {'output', 'voice', 'dist', '.venv', '__pycache__'}
                       for part in Path(name).parts)):
            errors.append(f'{name}: generated, environment, or private asset')
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            errors.append(f'{name}: expected a readable UTF-8 package file')
            continue
        for label, pattern in PATTERNS:
            for line, text in enumerate(content.splitlines(), 1):
                if pattern.search(text):
                    errors.append(f'{name}:{line}: {label}')
    if not count:
        errors.append('No staged or tracked files to review; git add the package first')
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f'Public-bundle checks passed for {count} tracked files. Manual review is still required.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
