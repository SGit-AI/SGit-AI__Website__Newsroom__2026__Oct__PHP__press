#!/usr/bin/env python3
"""Where the newsroom's data files live, for the tools that run outside the build: the drains, the exporters, the
invitations. Kept by dev@php.newsroom.

In v1 these tools sat at admin/build/ and read and wrote ../../data/<file>. Since the split (26 October 2026) the data is
the data repository's files/, a clone beside the press (sgit-ai__website__newsroom__2026__oct__php__data), released with
its own tools/release.sh. The tools run from the press's build/ (or from the box's admin/build/); either way the data
clone is found beside the repository they run from. NEWSROOM_DATA_FILES names another folder.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PREFIX = 'sgit-ai__website__newsroom__2026__oct__php'


def repository():
    """The top of the repository these tools run from (the press, or the box)."""
    d = HERE
    while not os.path.exists(os.path.join(d, '.git')) and os.path.dirname(d) != d:
        d = os.path.dirname(d)
    return d if os.path.exists(os.path.join(d, '.git')) else os.path.dirname(HERE)


def data_files():
    """The data repository's files/: where a drain or an exporter writes, before that repository's release."""
    env = os.environ.get('NEWSROOM_DATA_FILES')
    d = os.path.abspath(env) if env else os.path.join(os.path.dirname(repository()), PREFIX + '__data', 'files')
    if not os.path.isdir(d):
        sys.exit(f'no data clone at {d}: clone SGit-AI/{PREFIX}__data beside the press, or set NEWSROOM_DATA_FILES')
    return d


def data_file(name):
    return os.path.join(data_files(), name)


def published():
    """Every folder whose contents are published: the clones of the six beside this one, the box, and this repository."""
    top = os.path.dirname(repository())
    return sorted({repository()} | {os.path.join(top, d) for d in os.listdir(top) if d.startswith(PREFIX)})


def is_published(path):
    p = os.path.abspath(path)
    return any(p == r or p.startswith(r + os.sep) for r in published())


if __name__ == '__main__':
    print(data_files())
