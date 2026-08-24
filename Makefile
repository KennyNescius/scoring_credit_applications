.PHONY: run test clean

run:
	python scoring_engine.py && python app.py

test:
	python -m pytest tests/ -v

docker:
	docker-compose up --build

clean:
	rm -f model.pkl
	rm -rf natija/
	rm -rf __pycache__/
