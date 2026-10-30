"""Trusted development scaffolding; never register as an unrestricted agent tool."""
from dataclasses import dataclass
from pathlib import Path
import re
from .guardian.policy import Policy

KINDS = ('website', 'web_application', 'api', 'automation', 'dashboard', 'ecommerce')


@dataclass(frozen=True)
class ProjectPlan:
    name: str
    kind: str
    scope: str
    limitations: tuple[str, ...]


def plan_project(name, kind):
    if type(name) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', name) or kind not in KINDS:
        raise ValueError('Invalid project name or kind.')
    return ProjectPlan(name, kind, 'New isolated development project only.',
                       ('No production deployment, paid service or customer contact.',
                        'Only the website skeleton is generated; other kinds are plans, not implemented applications.',
                        'E-commerce requires separate payment/privacy/security design; no payments are connected.'))


def create_sample(parent: Path, plan: ProjectPlan, policy: Policy):
    """Operator supplies an approved disposable parent; no model controls it."""
    policy.require('file.create')
    if type(plan) is not ProjectPlan or plan != plan_project(plan.name, plan.kind) or plan.kind != 'website':
        raise ValueError('Only the reviewed website sample can be scaffolded.')
    parent = Path(parent)
    if parent.is_symlink() or not parent.is_dir() or parent.resolve() == Path('/'):
        raise ValueError('An explicit trusted development parent is required.')
    root = parent / plan.name
    root.mkdir(mode=0o700)  # Never overwrite an existing project or follow its symlink.
    files = {'index.html': '<!doctype html><html lang="en"><meta charset="utf-8"><title>IGRIS sample</title><h1>Development sample</h1></html>\n',
             'README.md': '# Development sample\n\nGenerated static website only. No backend, payment or production deployment.\n'}
    for name, content in files.items():
        with (root / name).open('x') as handle:
            handle.write(content)
        (root / name).chmod(0o600)
    return root
