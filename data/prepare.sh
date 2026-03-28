#!/bin/bash
set -e -u
BBOX=24.5185,59.322118,25.014945,59.533062
FORMAT=pmtiles
TIPPECANOE=../../tippecanoe/tippecanoe

if [ ! -e estonia-latest.osm.pbf ]; then
  wget https://download.geofabrik.de/europe/estonia-latest.osm.pbf -O estonia-latest.osm.pbf
fi

osmium extract -b $BBOX -O estonia-latest.osm.pbf -o tallinn.osm.pbf
osmium tags-filter -O tallinn.osm.pbf w/highway -o highways.osm.pbf
osmium export highways.osm.pbf -O -o cycleways.jsonl -f jsonseq -c osmium-export-config.json
rm tallinn.osm.pbf
rm highways.osm.pbf
uv run process.py cycleways.jsonl -o cycleways2.jsonl
uv run trim_measure.py cycleways2.jsonl -p tallinn.json -l -o toelised-rattateed.jsonl
rm cycleways.jsonl
rm cycleways2.jsonl
rm -f toelised-rattateed.$FORMAT
$TIPPECANOE -z 13 -o toelised-rattateed.$FORMAT \
  -l rattateed --use-attribute-for-id=way_id toelised-rattateed.jsonl
