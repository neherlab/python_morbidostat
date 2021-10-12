export DOCKER_IMAGE_NAME=docker-morbidostat
export UID=$(shell id -u)
export GID=$(shell id -g)

SHELL:=bash

.ONESHELL:
docker-image-build:
	@set -euo >/dev/null
	@docker build -t ${DOCKER_IMAGE_NAME} \
	--network=host \
	--build-arg UID=$(shell id -u) \
	--build-arg GID=$(shell id -g) \
	.

.ONESHELL:
docker-image-run: docker-image-build
	@set -euo >/dev/null
	@export DOCKER_CONTAINER_NAME=${DOCKER_IMAGE_NAME}-$(shell date +%s)
	@docker run -it --rm \
	--init \
	--name=$${DOCKER_CONTAINER_NAME} \
	--hostname=$${DOCKER_IMAGE_NAME} \
	--env DOCKER_IMAGE_NAME=$${DOCKER_IMAGE_NAME} \
	--env DOCKER_CONTAINER_NAME=$${DOCKER_CONTAINER_NAME} \
	--user=$(shell id -u):$(shell id -g) \
	--volume=$(shell pwd)/:/home/user/src \
	--workdir=/home/user/src \
	${DOCKER_IMAGE_NAME} \
	bash -c "${COMMAND}"

docker-shell: docker-image-build
	@$(MAKE) --no-print-directory docker-image-run COMMAND="bash"
