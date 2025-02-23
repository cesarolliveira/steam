SHELL := /bin/bash
-include .env
export

export HOST_UID:=$(shell id --user)
export HOST_USER:=$(shell id --user --name)
export HOST_GID:=$(shell id --group)
export HOST_GROUP:=$(shell id --group --name)


COLOR_RESET := $(shell tput sgr0)
COLOR_ITEM := $(shell tput setaf 2)
COLOR_VAL := $(shell tput setaf 4)
COLOR_SESSION := $(shell tput setaf 208)
COLOR_DEFAULT_VAL := $(shell tput setaf 130)

CMAKE := $(MAKE) --no-print-directory
SPACE_CHAR=$(subst ,, )

SERVICE_APP=app
DOCKER_COMPOSE_FILE=docker/compose/dev.yml

# General targets:
.PHONY: help build rebuild up down run exec bash shell log

help:	
	@echo '${COLOR_SESSION}Getting started to use the application:${COLOR_RESET}'
	@echo '  ${COLOR_ITEM}Restore:${COLOR_RESET} the production database'
	@echo '  ${COLOR_ITEM}  Go to:${COLOR_RESET} the main branch'
	@echo '  ${COLOR_ITEM}Execute:${COLOR_RESET} make deploy'
	@echo ''
	@echo '${COLOR_SESSION}Using the targets:${COLOR_RESET}'
	@echo '  make TARGET [OPTIONS]'
	@echo ''
	@echo '${COLOR_SESSION}General targets:${COLOR_RESET}'
	@echo '  ${COLOR_ITEM}help${COLOR_RESET}                   Display this help message'
	@echo ''
	@echo '  ${COLOR_ITEM}build${COLOR_RESET}                  Build docker image'
	@echo '                           Options:'	
	@echo '                             ${COLOR_ITEM}service=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: all services will be executed]${COLOR_RESET}'
	@echo '                             ${COLOR_ITEM}options=${COLOR_VAL}VAL${COLOR_RESET} (optional)'
	@echo ''
	@echo '  ${COLOR_ITEM}rebuild${COLOR_RESET}                Rebuild docker image without cache'
	@echo '                           Options:'	
	@echo '                             ${COLOR_ITEM}service=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: all services will be executed]${COLOR_RESET}'
	@echo '                             ${COLOR_ITEM}options=${COLOR_VAL}VAL${COLOR_RESET} (optional)'
	@echo ''	
	@echo '  ${COLOR_ITEM}up${COLOR_RESET}                     Start the application'
	@echo ''
	@echo '  ${COLOR_ITEM}down${COLOR_RESET}                   Stop the application'
	@echo ''	
	@echo '  ${COLOR_ITEM}run${COLOR_RESET}                    Execute the command in a new service container'
	@echo '                           Options:'	
	@echo '                             ${COLOR_ITEM}service=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: $(SERVICE_APP)]${COLOR_RESET}'
	@echo '                             ${COLOR_ITEM}cmd=${COLOR_VAL}VAL${COLOR_RESET}     (mandatory)'
	@echo ''	
	@echo '  ${COLOR_ITEM}exec${COLOR_RESET}                   Execute the command in the current service container'
	@echo '                           Options:'	
	@echo '                             ${COLOR_ITEM}service=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: $(SERVICE_APP)]${COLOR_RESET}'
	@echo '                             ${COLOR_ITEM}cmd=${COLOR_VAL}VAL${COLOR_RESET}     (mandatory)'
	@echo ''		
	@echo '  ${COLOR_ITEM}bash${COLOR_RESET}                   Execute the command in a new service container using bash as command-line'
	@echo '                           Options:'	
	@echo '                             ${COLOR_ITEM}service=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: $(SERVICE_APP)]${COLOR_RESET}'
	@echo '                             ${COLOR_ITEM}cmd=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: the prompt will be executed]${COLOR_RESET}'
	@echo ''		
	@echo '  ${COLOR_ITEM}shell${COLOR_RESET}                  Execute the command in a new service container using shell as command-line'
	@echo '                           Options:'	
	@echo '                             ${COLOR_ITEM}service=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: $(SERVICE_APP)]${COLOR_RESET}'
	@echo '                             ${COLOR_ITEM}cmd=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: the prompt will be executed]${COLOR_RESET}'
	@echo ''	
	@echo "  ${COLOR_ITEM}log${COLOR_RESET}                    Display the service's logs"
	@echo '                           Options:'	
	@echo '                             ${COLOR_ITEM}service=${COLOR_VAL}VAL${COLOR_RESET} (optional) ${COLOR_DEFAULT_VAL}[default: all services will be executed]${COLOR_RESET}'
	@echo ''
	@echo '${COLOR_SESSION}Compound targets:${COLOR_RESET}'
	@echo '  ${COLOR_ITEM}deploy${COLOR_RESET}                 Prepare the environment, prepare the database, and prepare and start the application'
	@echo ''		
	@echo '${COLOR_SESSION}App targets:${COLOR_RESET}'
	@echo ''
	@echo '${COLOR_SESSION}Docker targets:${COLOR_RESET}'
	@echo '  ${COLOR_ITEM}prune${COLOR_RESET}                  Remove unused objects'
	@echo ''
	@echo '  ${COLOR_ITEM}prune-container${COLOR_RESET}        Remove unused containers'
	@echo ''
	@echo '  ${COLOR_ITEM}prune-dangling-image${COLOR_RESET}   Remove dangling images'
	@echo ''	
	@echo '  ${COLOR_ITEM}prune-image${COLOR_RESET}            Remove unused images'
	@echo ''
	@echo '  ${COLOR_ITEM}prune-network${COLOR_RESET}          Remove unused networks'
	@echo ''
	@echo '  ${COLOR_ITEM}prune-volume${COLOR_RESET}           Remove unused volumes'
	@echo ''
	@echo '${COLOR_SESSION}Variables:${COLOR_RESET}'
	@echo '  ${COLOR_ITEM}env${COLOR_RESET}                    dev'
	@echo '  ${COLOR_ITEM}user${COLOR_RESET}                   $(HOST_USER)(uid=$(HOST_UID))'
	@echo '  ${COLOR_ITEM}group${COLOR_RESET}                  $(HOST_GROUP)(gid=$(HOST_GID))'

build-consumer:
	docker buildx create --use
	docker buildx build --file Dockerfile --no-cache --platform linux/amd64,linux/arm64 --target consumer --tag manoelpg/consumer:v1.0 --push .

build-producer:
	docker buildx create --use
	docker buildx build --file Dockerfile --no-cache --platform linux/amd64,linux/arm64 --target producer --tag manoelpg/producer:v1.0 --push .

build-streamlit:
	docker buildx create --use
	docker buildx build --file Dockerfile --no-cache --platform linux/amd64,linux/arm64 --target streamlit --tag manoelpg/streamlit:v1.0 --push .

start-producer:
	kubectl apply -f resources/producer/deployment.yaml

stop-producer:
	kubectl delete -f resources/producer/deployment.yaml

start-consumer:
#	Verifica se ${environment} foi definido
    if [ -z "${environment}" ]; then \
		echo "Variável environment não definida, opções: vps ou rasp-berry."; \
		exit 1; \
	fi
	helm upgrade --install --create-namespace --namespace steam consumer ./helm -f helm/values.yaml -f helm/environment/${environment}.yaml

stop-consumer:
	helm uninstall -n steam consumer

start-streamlit:
	kubectl apply -f resources/streamlit/deployment.yaml
	kubectl apply -f resources/streamlit/service.yaml
	kubectl apply -f resources/streamlit/ingress.yaml

stop-streamlit:
	kubectl delete -f resources/streamlit/deployment.yaml
	kubectl delete -f resources/streamlit/service.yaml
	kubectl delete -f resources/streamlit/ingress.yaml


# Docker targets:
.PHONY: prune prune-image prune-dangling-image

prune:
	docker system prune --all --force

prune-container:
	docker container prune

prune-dangling-image:
	docker image prune

prune-image:
	docker image prune --all

prune-network:
	docker network prune

prune-volume:
	docker volume prune	
