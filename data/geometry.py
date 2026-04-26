import math


def distance(point: list[float], other: list[float]) -> float:
    """Returns euclidian distance from self to other."""
    l1 = math.radians(point[0])
    l2 = math.radians(other[0])
    f1 = math.radians(point[1])
    f2 = math.radians(other[1])
    x = (l2 - l1) * math.cos((f1 + f2) / 2)
    y = f2 - f1
    return math.sqrt(x * x + y * y) * 6371000


def length(points: list[list[float]]) -> float:
    d = 0.0
    for i in range(1, len(points)):
        d += distance(points[i-1], points[i])
    return round(d, 2)


def flen(feature: dict) -> float:
    geom_type = feature['geometry']['type']
    if geom_type == 'MultiLineString':
        result = 0.0
        for s in feature['geometry']['coordinates']:
            result += length(s)
        return result
    if geom_type != 'LineString':
        raise Exception(f'Feature type is {geom_type}')
    return length(feature['geometry']['coordinates'])
