#!/bin/sh
../../tippecanoe/tippecanoe -z12 -o ametlikud-rattateed.pmtiles \
  -l rattateed -y rattatee_liik -T rattatee_liik:int \
  --use-attribute-for-id=objectid --convert-stringified-ids-to-numbers \
  tallinna-rattateed-260319.geojson harjumaa-rattateed-260319.geojson
