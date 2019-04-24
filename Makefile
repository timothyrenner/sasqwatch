# External data source reference:
# https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.2016.html

US_RESOLUTION ?= 5
SYNTHESIZED_RESOLUTION ?= 11
MIN_SYNTHESIZED_DATE ?= "1990-01-01"
NUM_SYNTHESIZED_SAMPLES ?= 4000

data/raw/us.geojson: data/external/cb_2016_us_state_500k.shp
	python data_processing/us_shp_to_geojson.py $< --output-file $@

data/raw/us_hexagons.csv: data/raw/us.geojson data/raw/bigfoot_sightings.csv
	python data_processing/us_hexagons.py $^ \
	--resolution $(US_RESOLUTION) \
	--output-file $@

data/raw/synthesized_not_sightings.csv: data/raw/us_hexagons.csv
	python data_processing/synthesize.py \
	--num-samples $(NUM_SYNTHESIZED_SAMPLES) \
	--min-date $(MIN_SYNTHESIZED_DATE) \
	--hexagon-file $< \
	--location-resolution $(SYNTHESIZED_RESOLUTION) \
	--output-file $@

data/interim/synthesized_not_sightings.csv: data/raw/synthesized_not_sightings.csv
	python data_processing/weather.py $< | \
		slamdring --num-tasks 10 | \
		python data_processing/unpack_weather_results.py --output-file $@

data/interim/raw_training_data.csv: data/raw/bigfoot_sightings.csv data/interim/synthesized_not_sightings.csv
	python data_processing/assemble.py $^ --output-file $@
