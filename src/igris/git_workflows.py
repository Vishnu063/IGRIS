"""Bounded local Git workflows for newly created trusted development repositories."""
import os
from pathlib import Path
import re
import shutil
import subprocess
from .guardian.policy import Policy
from .guardian.scan import scan_repository
from .guardian.secrets import prompt_text


class GitWorkflow:
    @classmethod
    def initialize(cls, parent, name, policy):
        policy.require('git.status')
        policy.require('file.create')
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', name):
            raise ValueError('Invalid new repository name.')
        root = Path(parent) / name
        root.mkdir(mode=0o700)
        obj = cls(root, policy)
        obj._git('init', '--initial-branch=main')
        return obj

    def __init__(self, root, policy):
        self.root, self.policy = Path(root).resolve(strict=True), policy
        self.git = shutil.which('git')
        if not self.git or self.root == Path('/'):
            raise ValueError('Trusted Git workspace required.')

    def _git(self, *args):
        self.policy.require('git.status')
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'GIT_TERMINAL_PROMPT': '0',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}
        return subprocess.run([self.git, '--no-pager', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
                               '-c', 'commit.gpgsign=false', '-c', 'user.name=IGRIS Development',
                               '-c', 'user.email=igris@users.noreply.github.com', *args], cwd=self.root, env=env,
                              text=True, capture_output=True, timeout=5, check=True).stdout

    def branch(self, name):
        if type(name) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', name):
            raise ValueError('Invalid branch name.')
        self._git('switch', '-c', name)

    def prepare(self, paths):
        self.policy.require('file.create')
        if type(paths) is not list or not paths:
            raise ValueError('Explicit paths required.')
        for path in paths:
            if type(path) is not str or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*(?:\.[A-Za-z0-9]+)?', path):
                raise ValueError('Invalid staged path.')
            target = self.root / path
            if target.is_symlink() or not target.resolve().is_relative_to(self.root) or not target.is_file():
                raise ValueError('Unsafe staged path.')
        self._git('add', '--', *paths)
        self._git('diff', '--cached', '--check')
        if scan_repository(self.root):
            raise ValueError('Credential scan requires review; index is retained for owner inspection.')
        return self._git('diff', '--cached', '--no-ext-diff', '--no-textconv')

    def commit(self, message):
        if type(message) is not str or not 1 <= len(message) <= 200 or '\n' in message or prompt_text(message) != message:
            raise ValueError('Safe commit message required.')
        if self.conflicts() or scan_repository(self.root):
            raise ValueError('Resolve conflicts or scanner findings before commit.')
        self._git('diff', '--cached', '--check')
        self._git('commit', '-m', message)
        return self._git('rev-parse', 'HEAD').strip()

    def conflicts(self):
        return bool(self._git('ls-files', '-u'))

    def rollback(self, expected_head):
        if not re.fullmatch(r'[a-f0-9]{40,64}', expected_head) or self._git('rev-parse', 'HEAD').strip() != expected_head:
            raise ValueError('Rollback head mismatch.')
        if self._git('status', '--porcelain') or self.conflicts():
            raise ValueError('Clean development state required.')
        self._git('revert', '--no-edit', expected_head)  # Preserve history; never force/reset/delete.

    def pull_request_draft(self, base='main'):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', base):
            raise ValueError('Invalid base.')
        return {'base': base, 'head': self._git('branch', '--show-current').strip(),
                'summary': self._git('diff', '--stat', base + '...HEAD'), 'submitted': False}
