.PHONY: build
build:
	docker build -t plebiscite .

.PHONY: shell
shell:
	docker run -it --rm \
	--name plebiscite \
	-v $(shell pwd)/config.json:/usr/src/plebiscite/config.json \
	-p 8080:8080 \
	plebiscite \
	/bin/ash

.PHONY: run
run:
	docker run -it --rm \
	--name plebiscite \
	-v $(shell pwd)/config.json:/usr/src/plebiscite/config.json \
	-p 8080:8080 \
	plebiscite
