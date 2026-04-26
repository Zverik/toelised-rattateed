import sys
from geometry import flen


def total_length(features: list[dict]) -> int:
    result = 0.0
    for f in features:
        result += flen(f)
    return round(result)


def describe(f: dict) -> str:
    p = f['properties']
    typ = p['type']
    sub = p.get('track_type') or p.get('lane_type')
    w = '' if 'width' not in p else '+width'
    return f'{typ}/{sub}{w}'


def classify_tags(f: dict) -> str:
    prev = f['previous']
    cur = f['properties']
    for k in ('type', 'track_type', 'lane_type'):
        if cur.get(k, '') != prev.get(k, ''):
            return f'{k}:{prev[k]}→{cur[k]}'
    for k in ('width', 'surface', 'smoothness'):
        if k in cur and k not in prev:
            return f'+{k}'
        if k in prev and k not in cur:
            return f'-{k}'
    return 'other'


def sort_by_desc(features: list[dict],
                 fn=describe) -> list[tuple[str, list[dict]]]:
    sorts: dict[str, list[dict]] = {}
    for f in features:
        d = fn(f)
        if d not in sorts:
            sorts[d] = []
        sorts[d].append(f)
    return [(k, sorts[k]) for k in sorted(sorts.keys())]


def way_url(f: dict, extra: str) -> str:
    way_id = f['properties']['way_id']
    url = f'https://www.openstreetmap.org/way/{way_id}'
    return f'    <li><a href="{url}">way {way_id}</a> {extra}</li>'


def print_urls(out, features: list[dict], max_urls: int):
    if not features:
        return
    print('    <ul>', file=out)
    fs = sorted(features, key=lambda f: flen(f), reverse=True)
    for f in fs[:max_urls]:
        print(way_url(f, f'{flen(f)} m'), file=out)
    if len(fs) > max_urls:
        print('    <li>...</li>', file=out)
    print('    </ul>', file=out)


def print_report(result: dict[str, list[dict]], filename: str,
                 max_urls: int = 3) -> None:
    out = sys.stdout if filename == '-' else open(filename, 'w')

    print('<!doctype html><html lang="en">', file=out)
    print('<head>'
          '<title>Report</title>'
          '<meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '</head><body>', file=out)

    created = result['created']
    print(f'<h1>Confirmed/added {len(created)}, {total_length(created)} m</h1>', file=out)
    print('  <ul>', file=out)
    for typ, fs in sort_by_desc(created):
        print(f'  <li><b>{typ}</b>: {len(fs)}, {total_length(fs)} m</li>', file=out)
        print_urls(out, fs, max_urls)
    print('  </ul>', file=out)

    deleted = result['deleted']
    print(file=out)
    print(f'<h1>Demoted/deleted {len(deleted)}, {total_length(deleted)} m</h1>', file=out)
    print('  <ul>', file=out)
    for typ, fs in sort_by_desc(deleted):
        print(f'  <li><b>{typ}</b>: {len(fs)}, {total_length(fs)} m</li>', file=out)
        print_urls(out, fs, max_urls)
    print('  </ul>', file=out)

    tags = result['tags']
    print(file=out)
    print(f'<h1>Updated tags on {len(tags)}</h1>', file=out)
    print('  <ul>', file=out)
    for typ, fs in sort_by_desc(tags, classify_tags):
        print(f'  <li><b>{typ}</b>: {len(fs)}, {total_length(fs)} m</li>', file=out)
        print_urls(out, fs, max_urls)
    print('  </ul>', file=out)

    geom = result['length']
    print(file=out)
    print(f'<h1>Significant length change on {len(geom)}</h1>', file=out)
    if len(geom) <= max_urls:
        print('    <ul>', file=out)
        for f in geom:
            old_len = round(f['properties']['old_length'])
            new_len = round(f['properties']['new_length'])
            print(way_url(f, f'{old_len} → {new_len}'), file=out)
        print('    </ul>', file=out)

    print('</body></html>', file=out)
