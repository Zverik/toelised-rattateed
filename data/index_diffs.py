#!/bin/env python3
import json
import argparse
import os
import re
import sys


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Indexes the json diff files')
    parser.add_argument(
        '-p', '--path', required=True,
        help='Path to all the diff jsons')
    parser.add_argument('-o', '--output', help='Output json file')
    parser.add_argument(
        '-r', '--refresh', help='Read all diffs instead of just missing')
    options = parser.parse_args()

    data = []
    if options.output and not options.refresh:
        try:
            with open(options.output, 'r') as f:
                data = json.load(f)
        except IOError:
            pass  # doesn't matter
    present = set(d.get('name') for d in data)

    for fn in os.listdir(options.path):
        if not re.search(r'diff-.+\.json$', fn):
            continue
        if fn in present:
            continue

        filename = os.path.join(options.path, fn)
        try:
            with open(filename, 'r') as f:
                diff = json.load(f)
        except IOError as e:
            sys.stderr.write(f'Could not load {filename}: {e}\n')
            continue  # skip the file

        count = 0
        for field in ('created', 'deleted', 'tags'):
            if field in diff:
                count += len(diff[field])
        data.append({'name': fn, 'count': count})

    data.sort(key=lambda d: d['name'], reverse=True)

    out = sys.stdout if not options.output else open(options.output, 'w')
    json.dump(data, out)
