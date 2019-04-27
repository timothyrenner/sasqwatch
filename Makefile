# External data source reference:
# https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.2016.html

US_RESOLUTION ?= 5
SYNTHESIZED_RESOLUTION ?= 11
MIN_SYNTHESIZED_DATE ?= "1990-01-01"
NUM_SYNTHESIZED_SAMPLES ?= 4000

data/raw/us.geojson: data/external/cb_2016_us_state_500k.shp
	python model/us_shp_to_geojson.py $< --output-file $@

data/raw/us_hexagons.csv: data/raw/us.geojson data/raw/bigfoot_sightings.csv
	python model/us_hexagons.py $^ \
	--resolution $(US_RESOLUTION) \
	--output-file $@

data/raw/synthesized_not_sightings.csv: data/raw/us_hexagons.csv
	python model/synthesize.py \
	--num-samples $(NUM_SYNTHESIZED_SAMPLES) \
	--min-date $(MIN_SYNTHESIZED_DATE) \
	--hexagon-file $< \
	--location-resolution $(SYNTHESIZED_RESOLUTION) \
	--output-file $@

data/interim/synthesized_not_sightings.csv: data/raw/synthesized_not_sightings.csv
	python model/weather.py $< | \
		slamdring --num-tasks 10 | \
		tqdm --total $(NUM_SYNTHESIZED_SAMPLES) | \
		python model/unpack_weather_results.py --output-file $@

data/processed/raw_training_data.csv: data/raw/bigfoot_sightings.csv data/interim/synthesized_not_sightings.csv
	python model/assemble.py $^ --output-file $@

data/processed/training_data.csv: data/processed/raw_training_data.csv
	python model/features.py $< --output-file $@

training_data: data/processed/training_data.csv

data/visualizations/sightings_point_map.html: data/raw/bigfoot_sightings.csv
	python analysis/point_map.py $< --output-file $@
	open $@

data/visualizations/not_sightings_point_map.html: data/raw/synthesized_not_sightings.csv
	python analysis/point_map.py $< --output-file $@
	open $@

data/visualizations/sighting_hex_map.html: data/raw/bigfoot_sightings.csv data/raw/us.geojson
	python analysis/hex_map.py $^ --resolution 4 --output-file $@
	open $@

data/visualizations/not_sighting_hex_map.html: data/raw/synthesized_not_sightings.csv data/raw/us.geojson
	python analysis/hex_map.py $^ --resolution 4 --output-file $@
	open $@

data/visualizations/raw_training_data.html: data/processed/raw_training_data.csv
	svl analysis/raw_training_data.svl --dataset bigfoot=$< --output-file $@

data/visualizations/training_data.html: data/processed/training_data.csv
	svl analysis/training_data.svl --dataset bigfoot=$< --output-file $@

visualizations: \
	data/visualizations/sightings_point_map.html \
	data/visualizations/not_sightings_point_map.html \
	data/visualizations/sighting_hex_map.html \
	data/visualizations/not_sighting_hex_map.html \
	data/visualizations/raw_training_data.html \
	data/visualizations/training_data.html
