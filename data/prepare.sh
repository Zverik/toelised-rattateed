#!/bin/bash
set -e -u
SOURCE=estonia-latest.osm.pbf
BBOX=24.5185,59.322118,25.014945,59.533062
TMP=/tmp
HERE=$(dirname "$0")
FORMAT=pmtiles
TIPPECANOE=${TIPPECANOE:-../../tippecanoe/tippecanoe}
OSMIUM=${OSMIUM:-osmium}
UV=${UV:-uv}

if [ ! -e $SOURCE ]; then
  wget https://download.geofabrik.de/europe/$SOURCE -O $SOURCE
  $OSMIUM renumber $SOURCE -o estonia.osm.pbf -t node
  mv estonia.osm.pbf $SOURCE
fi

$OSMIUM extract -b $BBOX -O $SOURCE -o $TMP/tallinn.osm.pbf -S relations=false
$OSMIUM tags-filter -O $TMP/tallinn.osm.pbf w/highway -o $TMP/highways.osm.pbf
$OSMIUM export $TMP/highways.osm.pbf -O -o $TMP/cycleways.jsonl -f jsonseq -c osmium-export-config.json
rm $TMP/tallinn.osm.pbf
rm $TMP/highways.osm.pbf

if $UV -V; then
  $UV run process.py $TMP/cycleways.jsonl -o $TMP/cycleways2.jsonl
  $UV run trim_measure.py $TMP/cycleways2.jsonl -p tallinn.json -l -o toelised-rattateed.jsonl
else
  python3 process.py $TMP/cycleways.jsonl -o toelised-rattateed.jsonl
fi
rm $TMP/cycleways.jsonl
rm -f $TMP/cycleways2.jsonl

rm -f toelised-rattateed.$FORMAT
$TIPPECANOE -z 13 -o toelised-rattateed.$FORMAT \
  -l rattateed --use-attribute-for-id=way_id toelised-rattateed.jsonl
