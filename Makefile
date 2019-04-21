data/interim/synthesized_sightings.csv: data/raw/synthesized_sightings.csv
	python data_processing/weather.py $< | \
		slamdring --num-tasks 10 | \
		python data_processing/unpack_weather_results.py --output-file $@