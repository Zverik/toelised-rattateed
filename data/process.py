#!/usr/bin/env python3
import argparse
import json
import sys
import re
from datetime import date
from enum import Enum


class Grade(Enum):
    SKIP = 0
    ANY = 1
    DEDICATED = 2
    BASIC = 3
    MAIN = 4


def main_or_basic(tags: dict[str, str]) -> Grade | str:
    separated = 'separation' in tags and tags['separation'] not in ('none', 'lowered_kerb')
    is_coloured = tags.get('colour') in ('red', 'blue')
    oneway = tags['oneway'] in ('yes', '-1')
    incline_match = re.match(r'(\d+)%$', tags.get('incline', ''))
    incline = 0 if not incline_match else int(incline_match[1])

    is_main = True

    sm = tags.get('smoothness') or tags.get('s_smoothness')
    if sm and sm not in ('perfect', 'good'):
        return f'smoothness {sm}'

    if tags['type'] == 'track':
        width = 2.0 if 'width' not in tags else float(tags['width'])

        min_width_main = 2.0 if oneway else 3.0
        min_width_basic = 1.5 if oneway else 2.5

        if tags['track_type'] != 'dedicated':
            is_main = False
            min_width_basic = min_width_main

        if incline >= 3:
            # Per Oslo design guide.
            min_width_main *= 1.2
            min_width_basic *= 1.2

        if width < min_width_main:
            is_main = False
        if width < min_width_basic:
            return f'width<{min_width_basic}' if 'width' in tags else 'no width'

    elif tags['type'] == 'lane':
        if tags['lane_type'] != 'lane':
            # Shared lanes are haram. Maybe ok with 20 km/h but not now.
            return tags['lane_type']

        # Note that is_transit means only MAIN is acceptable.
        width = 1.0 if 'width' not in tags else float(tags['width'])
        is_transit = tags['highway'] in (
            'trunk', 'trunk_link', 'primary', 'primary_link',
            'secondary', 'secondary_link')
        high_traffic = is_transit or tags['highway'] == 'tertiary'

        if 'maxspeed' in tags and re.match(r'^\d+$', tags['maxspeed']):
            speed = int(tags['maxspeed'])
        else:
            speed = 50 if is_transit else 30

        if not oneway and not separated:
            # This is absurd.
            return 'not separated'

        if not separated and not is_coloured:
            # Oslo required red surface for all, but we relax it to just not separated.
            return 'not red'

        if high_traffic and not separated:
            # We'll allow for basic roads
            is_main = False

        if speed > 30 and not separated:
            # Must be separated or high danger roads.
            return 'not separated'

        min_width_main = 2.0 if oneway else 3.0
        if not separated:
            # Unofficial, but we'll allow it.
            min_width_basic = min_width_main
        else:
            min_width_basic = 1.5 if oneway else 2.5

        if incline >= 3:
            # Per Oslo design guide.
            min_width_main *= 1.2
            min_width_basic *= 1.2

        if width < min_width_main:
            is_main = False
        if width < min_width_basic:
            return f'width<{min_width_basic}' if 'width' in tags else 'no width'

    else:
        raise Exception(f'Wrong type: {tags["type"]}')

    # If we're here, we didn't return None, so all checks have passed.
    return Grade.MAIN if is_main else Grade.BASIC


def set_grade(tags: dict[str, str]) -> None:
    if not tags:
        return

    grade: Grade | None = None

    # Main and Basic
    mb = main_or_basic(tags)
    if isinstance(mb, Grade):
        grade = mb
    else:
        # Failed checks
        tags['reason'] = mb

        # Dedicated
        if tags.get('track_type') == 'dedicated':
            grade = Grade.DEDICATED
        elif tags.get('lane_type') == 'lane':
            grade = Grade.DEDICATED
        else:
            grade = Grade.ANY

    tags['grade'] = grade.name.lower()


def find_age(tags: dict[str, str]) -> str | None:
    check_date = tags.get('cycleway:check_date') or tags.get('check_date')
    if not check_date:
        return None
    parts = re.match(r'^\s*(20\d\d)-(\d\d?)(?:-(\d\d))?', check_date)
    if parts:
        checked_at = date(
            int(parts[1]), int(parts[2]),
            1 if not parts[3] else int(parts[3]))
        delta = date.today() - checked_at
        return str(round(delta.total_seconds() / (3600*24)))
    return None


def side_tag(tags: dict[str, str], side: str | None, key: str) -> str | None:
    if side is None:
        return None
    if key == '':
        keys = [f'cycleway:{side}', 'cycleway:both']
    else:
        keys = [f'cycleway:{side}:{key}', f'cycleway:both:{key}']
    for k in keys:
        if k in tags:
            return tags[k]
    return None


def clear_none(d: dict[str, str | None]) -> dict[str, str]:
    return {k: v for k, v in d.items() if v}


def unwind_tags(tags: dict[str, str], side: str | None) -> dict[str, str]:
    SMOOTHNESS_TO_ECS = {
        'excellent': 'perfect',
        'good': 'good',
        'intermediate': 'moderate',
        'bad': 'bad',
        'very_bad': 'bad',
    }
    SMOOTHNESS_VALUES = {
        'perfect': 1,
        'good': 2,
        'moderate': 3,
        'bad': 4,
    }
    TOP_SURFACE_SMOOTHNESS = {
        'asphalt': 'perfect',
        'chipseal': 'perfect',
        'concrete': 'perfect',

        'paved': 'good',
        'concrete:plates': 'good',
        'paving_stones': 'good',

        'concrete:lanes': 'moderate',
        'grass_paver': 'moderate',
        'sett': 'moderate',
        'bricks': 'moderate',
        'fine_gravel': 'moderate',
        'tiles': 'moderate',
        'unpaved': 'moderate',
        'compacted': 'moderate',

        'unhewn_cobblestone': 'bad',
        'cobblestone': 'bad',
        'metal_grid': 'bad',
        'wood': 'bad',
        'metal': 'bad',
        'gravel': 'bad',
        'ground': 'bad',
        'woodchips': 'bad',
        'dirt': 'bad',
        'grass': 'bad',
        'mud': 'bad',
        'sand': 'bad',
        'mulch': 'bad',
        'pebblestone': 'bad',
        'rock': 'bad',
    }

    result: dict[str, str | None] = {}
    result['surface'] = side_tag(tags, side, 'surface') or tags.get('cycleway:surface') or tags.get('surface')
    result['colour'] = side_tag(tags, side, 'surface:colour') or tags.get('cycleway:surface:colour')
    result['width'] = side_tag(tags, side, 'width') or tags.get('cycleway:width')
    result['incline'] = tags.get('cycleway:incline') or tags.get('incline')
    oneway = side_tag(tags, side, 'oneway') or tags.get('oneway:bicycle') or tags.get('cycleway:oneway')
    if tags.get('lit') == 'yes':
        result['lit'] = tags['lit']

    if 'width' in result and not re.match(r'^\d+(\.\d+)?$', result['width'] or ''):
        del result['width']
    if not re.match(r'^\d+%$', result['incline'] or ''):
        del result['incline']

    expected_smoothness = TOP_SURFACE_SMOOTHNESS.get(result.get('surface'))
    result['smoothness'] = (
        side_tag(tags, side, 'smoothness:ecs')
        or tags.get('cycleway:smoothness:ecs') or tags.get('smoothness:ecs')
        or SMOOTHNESS_TO_ECS.get(side_tag(tags, side, 'smoothness'))
        or SMOOTHNESS_TO_ECS.get(tags.get('cycleway:smoothness'))
        or SMOOTHNESS_TO_ECS.get(tags.get('smoothness')))
    if result['smoothness'] not in SMOOTHNESS_VALUES:
        del result['smoothness']

    # Downgrade smoothness if it's too optimistic.
    if expected_smoothness and 'smoothness' in result:
        if SMOOTHNESS_VALUES[expected_smoothness] > SMOOTHNESS_VALUES[result['smoothness']]:
            result['smoothness'] = expected_smoothness

    # Write backup smoothness from surface.
    if expected_smoothness and 'smoothness' not in result:
        result['s_smoothness'] = expected_smoothness

    if tags['highway'] in ('cycleway', 'footway', 'path'):
        # Dedicated track or shared footway
        if side:
            # Not a lane.
            return {}
        if tags['highway'] != 'cycleway' and tags.get('bicycle') != 'designated':
            # Bicycles not explicitly allowed.
            return {}

        result['type'] = 'track'
        track_type = ''
        segregated = tags.get('segregated') == 'yes'  # False by default
        if segregated:
            result['segregated'] = 'yes'
            separation = tags.get('cycleway:separation')
            result['separation'] = separation
            other_surface = tags.get('footway:surface') or tags.get('surface')
            if (not separation or separation == 'none') and (not other_surface or other_surface == result['surface']):
                track_type = 'painted'
            else:
                track_type = 'dedicated'

            if not result.get('width') and re.match(r'^\d+(\.\d+)?$', tags.get('width') or ''):
                # Doing with what we have.
                result['width'] = str(float(tags['width']) / 2.0)
        else:
            if tags['highway'] != 'footway' and ('foot' not in tags or tags.get('foot') in ('no', 'discouraged')):
                track_type = 'dedicated'
            else:
                track_type = 'shared'

            if not result.get('width') and re.match(r'^\d+(\.\d+)?$', tags.get('width') or ''):
                # Total width is perfectly fine here.
                result['width'] = str(float(tags['width']))
        result['track_type'] = track_type
        if not oneway:
            oneway = tags.get('oneway') or 'no'
        result['oneway'] = oneway
        return clear_none(result)

    if tags['highway'] not in (
        'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary',
        'secondary_link', 'tertiary', 'tertiary_link', 'residential',
        'unclassified', 'service', 'living_street',
    ):
        # Not a road, and not a cycle road, so what's the point.
        return {}

    if not side:
        # Check for mixed/cycle street
        if tags.get('cyclestreet') != 'yes':
            return {}  # not supporting for now
        return {}

    cycleway = side_tag(tags, side, '')
    if cycleway not in ('lane', 'shared_lane', 'share_busway'):
        # Only considering lanes.
        return {}

    result['type'] = 'lane'
    result['lane_type'] = cycleway
    result['side'] = side
    result['highway'] = tags['highway']
    segregated = side_tag(tags, side, 'segregated') == 'yes'
    result['separation'] = side_tag(tags, side, 'separation')
    result['maxspeed'] = tags.get(f'maxspeed:{side}') or tags.get('maxspeed')
    result['oneway'] = oneway or ('yes' if side == 'right' else '-1')

    return clear_none(result)


def list_missing(tags: dict[str, str], orig_tags: dict[str, str]) -> str | None:
    if 'type' not in tags:
        return None
    result = set[str]()
    if 'width' not in tags:
        result.add('w')
    if tags['type'] == 'lane' and 'maxspeed' not in tags:
        result.add('sp')
    if tags.get('lane_type') == 'lane' and 'colour' not in tags:
        result.add('c')
    if 'smoothness' not in tags and 's_smoothness' not in tags:
        result.add('sm')
    if tags.get('track_type') == 'shared' and 'segregated' not in orig_tags:
        result.add('seg')
    if ('segregated' in tags or tags['type'] == 'lane') and 'separation' not in tags:
        result.add('sep')
    return None if not result else ','.join(sorted(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Replaces tags on linestrings with cycleway-specific.')
    parser.add_argument(
        'input', type=argparse.FileType('r'), help='Source json lines file')
    parser.add_argument(
        '-o', '--output', help='Output json lines file, stdout by default')
    options = parser.parse_args()

    out = sys.stdout if not options.output else open(options.output, 'w')
    for line in options.input:
        feature = json.loads(line)
        if feature['geometry']['type'] != 'LineString':
            continue
        if 'cycle' not in line:
            continue
        tags = feature['properties']
        if 'highway' not in tags or tags['@type'] != 'way':
            continue

        for side in (None, 'left', 'right'):
            side_tags = unwind_tags(tags, side)
            check_date = find_age(tags)
            if check_date:
                # This nullifies the empty side_tags check.
                side_tags['age_days'] = check_date

            if not side_tags:
                continue

            side_tags['way_id'] = tags['@id']
            if 'type' in side_tags:
                set_grade(side_tags)
            missing = list_missing(side_tags, tags)
            if missing:
                side_tags['missing'] = missing
            if 'length' in tags:
                side_tags['length'] = tags['length']

            feature['properties'] = side_tags
            json.dump(feature, out, ensure_ascii=False)
            out.write('\n')
