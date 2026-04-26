#!/usr/bin/env python3
import argparse
import json
import sys
from geometry import flen
from typing import Generator
from reporter import print_report


def iterate_jsonl(filename: str) -> Generator[tuple[str, dict]]:
    with open(filename, 'r') as f:
        for ln, line in enumerate(f, 1):
            if not line.strip().startswith('{'):
                continue
            feature = json.loads(line)
            way_id = feature.get('properties', {}).get('way_id')
            if way_id is None:
                raise Exception(f'Feature on line {ln} in {f} '
                                'does not have way_id')
            if 'type' not in feature['properties']:
                # Skip non-cycling segments with just an age.
                continue
            if 'age_days' in feature['properties']:
                feature['properties']['checked'] = 'yes'
            for k in ('age_days', 'grade', 'reason', 'missing', 'length'):
                # We're not comparing on calculated tags.
                if k in feature['properties']:
                    del feature['properties'][k]
            side = feature['properties'].get('side', '')
            k = f'{way_id}{side}'
            yield (k, feature)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Finds differences between two jsonl files produces by TR')
    parser.add_argument('old', help='Older file')
    parser.add_argument('new', help='Newer file')
    parser.add_argument(
        '-l', '--length', type=int, default=50,
        help='By how many percent the length should differ to be registered')
    parser.add_argument(
        '-r', '--report', help='Generate HTML report to this file')
    parser.add_argument(
        '--urls', type=int, default=10,
        help='How many way links to print for each reported change')
    parser.add_argument(
        '-o', '--output', default='-',
        help='Output json lines file, stdout by default')
    options = parser.parse_args()

    old: dict[str, dict] = {}
    for k, feature in iterate_jsonl(options.old):
        old[k] = feature

    created: list[dict] = []
    tags: list[dict] = []
    geometry: list[dict] = []
    missing_way_ids = set(old.keys())

    for k, feature in iterate_jsonl(options.new):
        if k not in old:
            created.append(feature)
        elif k in missing_way_ids:  # skip duplicates
            missing_way_ids.remove(k)

            old_feature = old[k]
            if old_feature['properties'] != feature['properties']:
                f = feature.copy()
                f['previous'] = old_feature['properties']
                tags.append(f)

            old_len = flen(old_feature)
            new_len = flen(feature)
            perc = 100 * new_len / old_len
            if max([old_len, new_len]) > 50 and abs(100 - perc) > options.length:
                f = feature.copy()
                f['properties']['old_length'] = old_len
                f['properties']['new_length'] = new_len
                geometry.append(f)

    deleted = [f for way_id, f in old.items() if way_id in missing_way_ids]

    result = {
        'created': created,
        'deleted': deleted,
        'tags': tags,
        'length': geometry,
    }
    out = sys.stdout if options.output == '-' else open(options.output, 'w')
    json.dump(result, out)

    if options.report:
        print_report(result, options.report, options.urls)
