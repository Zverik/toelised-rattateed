#!/usr/bin/env python3
import argparse
import json
import shapely
from geometry import length
from shapely.geometry import shape, mapping


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Trims a GeoJSON lines file to a given shape, '
        'and adds line lengths')
    parser.add_argument(
        'input', type=argparse.FileType('r'), help='Source GeoJSON')
    parser.add_argument(
        '-p', '--polygon', required=True, type=argparse.FileType('r'),
        help='A GeoJSON with a single polygon')
    parser.add_argument(
        '-l', '--lengths', action='store_true',
        help='Add line lengths in meters into "length" properties')
    parser.add_argument(
        '-o', '--output', required=True, type=argparse.FileType('w'),
        help='Output GeoJSON')
    options = parser.parse_args()

    area = shape(json.load(options.polygon))
    shapely.prepare(area)

    for line in options.input:
        feature = json.loads(line)
        geometry = shape(feature['geometry'])
        if not shapely.intersects(area, geometry):
            continue
        if not shapely.covers(area, geometry):
            trimmed = shapely.intersection(area, geometry)
            feature['geometry'] = mapping(trimmed)
        if options.lengths and feature['geometry']['type'] == 'LineString':
            feature['properties']['length'] = length(
                feature['geometry']['coordinates'])
        json.dump(feature, options.output, ensure_ascii=False)
        options.output.write('\n')
