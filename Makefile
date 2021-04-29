ENV_FILE := .env
include ${ENV_FILE}

start:
	docker-compose up -d redis
	python app.py

stop:
	docker-compose stop

retrain:
	python retrain.py

retrain_init:
	python retrain.py init

logs:
	docker-compose logs -f

build:
	${MAKE} build_core
	${MAKE} build_retrain

build_core:
	pip freeze > requirements.txt
	docker build -t ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG} -f ./docker/app/Dockerfile .
	docker tag ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG} ${DOCKER_REGISTRY}:${DOCKER_IMAGE_TAG}
	docker push ${DOCKER_REGISTRY}:${DOCKER_IMAGE_TAG}

build_retrain:
	pip freeze > requirements.txt
	docker build -t ${DOCKER_IMAGE_NAME_RETRAIN}:${DOCKER_IMAGE_TAG} -f ./docker/retrain/Dockerfile .
	docker tag ${DOCKER_IMAGE_NAME_RETRAIN}:${DOCKER_IMAGE_TAG} ${DOCKER_REGISTRY_RETRAIN}:${DOCKER_IMAGE_TAG}
	docker push ${DOCKER_REGISTRY_RETRAIN}:${DOCKER_IMAGE_TAG}