#!/bin/bash
set -e -u
SOURCE=estonia-latest.osm.pbf
JSONL=toelised-rattateed.jsonl
BBOX=24.5185,59.322118,25.014945,59.533062
TMP=/tmp
HERE=$(dirname "$0")
FORMAT=pmtiles
TIPPECANOE=${TIPPECANOE:-tippecanoe}
OSMIUM=${OSMIUM:-osmium}
UV=${UV:-uv}
DIFF=diff-$(date +%y%m%d)
DIFF_BASE=../web/diffs/$DIFF

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

mv $JSONL tr-old.jsonl
mkdir -p ../web/diffs
if $UV -V; then
  $UV run process.py $TMP/cycleways.jsonl -o $TMP/cycleways2.jsonl
  $UV run trim_measure.py $TMP/cycleways2.jsonl -p tallinn.json -l -o $JSONL
  # mv $TMP/cycleways2.jsonl $JSONL
  $UV run diff.py tr-old.jsonl $JSONL -o $DIFF_BASE.json -r $DIFF_BASE.html
else
  python3 process.py $TMP/cycleways.jsonl -o $JSONL
  python3 diff.py tr-old.jsonl $JSONL -o $DIFF_BASE.json -r $DIFF_BASE.html
fi
echo "$(date +%Y-%m-%d) $DIFF.json" >> ../web/diffs/index.txt
rm $TMP/cycleways.jsonl
rm -f $TMP/cycleways2.jsonl
rm tr-old.jsonl

rm -f toelised-rattateed.$FORMAT
$TIPPECANOE -z 13 -o toelised-rattateed.$FORMAT -l rattateed --generate-ids $JSONL
