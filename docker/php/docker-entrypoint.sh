#!/bin/bash
set -e

# avoid "not found" error by checking dest dir
if [ -d "/docker-entrypoint/" ] && [ "$(ls -A /docker-entrypoint/)" ]; then
    for file in /docker-entrypoint/*.sh; do
        /bin/bash ${file}
    done
fi

# first arg is `-f` or `--some-option`
if [ "${1#-}" != "$1" ]; then
	set -- php-fpm "$@"
fi

# php-fpm running
if [ "$1" = 'php-fpm' ]; then
	echo "Checking write permissions on volumes..."

	DIRS=("${SYMFONY_CACHE_DIR}" "${SYMFONY_LOG_DIR}" "${SYMFONY_ARQUIVOS_DIR}")

	for DIR in ${DIRS[*]}; do
		echo "Checking write permissions on '${DIR}'..."

		FILE="${DIR}/.check"

		touch ${FILE}
		rm --force --verbose ${FILE}

		echo "'${DIR}' have sufficient permissions!"
	done
fi

exec docker-php-entrypoint "$@"