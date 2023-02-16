# Define global build args
ARG PHP_VERSION="8.0"
ARG COMPOSER_SUM="28a8d9740d615137a8c01d32aef9184db16f543fca36db038501a294d8e95b24"
ARG COMPOSER_VERSION="2.2.18"

#
# PHP
#
FROM php:${PHP_VERSION}-fpm AS php

# Define build args
ARG APCU_VERSION=5.1.17

# Update, best practices and install dependencies
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        acl \
        apt-utils \
        coreutils \
        file \
#        fontconfig \
        gettext \
        git \
#        libfontconfig \
#        libfreetype6-dev \
        libicu-dev \
#        libjpeg62-turbo \
#        libjpeg62-turbo-dev \
#        libpng-dev \
        libtool \
#        libwebp-dev \
        libxrender1 \
        libzip-dev \
        procps \
        ssh \
        unzip \
        wget \
#        xfonts-75dpi \
#        xfonts-base \
        xvfb \
        zlib1g-dev \
    && docker-php-ext-install \
        -j$(nproc) \
        exif \
#    	gd \
        intl \
#        pdo_mysql \
        zip \
#	 && docker-php-ext-configure \
#        gd --with-jpeg-dir=/usr/include/ \
#        --with-png-dir=/usr/include/  \
#     && docker-php-ext-configure \
#         zip --with-libzip \
    && pecl install \
        apcu-${APCU_VERSION} \
    && docker-php-ext-enable \
        apcu \
#       gd \
        opcache \
    && pecl clear-cache \
#   && wget --no-check-certificate https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_amd64.deb \
#       && dpkg -i wkhtmltox_0.12.6-1.buster_amd64.deb \
#       && rm wkhtmltox_0.12.6-1.buster_amd64.deb \
    && apt-get clean \
    && rm --recursive --force --verbose /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && true

#
# BUILDER
#
FROM php AS builder

# Define bash instead of shell
SHELL [ "/bin/bash", "-l", "-c" ]

# Why are we installing `composer` instead of using the result of compilation from another container (the same way it was done with `node`)?
#
# Composer was designed to respect the platform requirements as stated in the official documentation, even though this can be done through the `config` directive, the recommendation is to run with the real dependencies.
# @see https://getcomposer.org/doc/articles/composer-platform-dependencies.md#composer-platform-dependencies

ARG COMPOSER_SUM
ARG COMPOSER_VERSION

# Install `composer`
RUN curl -LO "https://getcomposer.org/download/${COMPOSER_VERSION}/composer.phar" \
    && echo "${COMPOSER_SUM}  composer.phar" | sha256sum -c - \
    && chmod +x composer.phar \
    && mv composer.phar /usr/local/bin/composer \
    && composer --version \
    && true

# Define environment vars
ENV WORKDIR=/var/www/steam
ENV SYMFONY_VAR_DIR="${WORKDIR}/var"
ENV SYMFONY_CACHE_DIR="${SYMFONY_VAR_DIR}/cache"
ENV SYMFONY_LOG_DIR="${SYMFONY_VAR_DIR}/log"
ENV SYMFONY_WEB_DIR="${WORKDIR}/public"
ENV SYMFONY_ARQUIVOS_DIR="${SYMFONY_WEB_DIR}/arquivos"

# Create volumes structure dir
RUN mkdir --parents --verbose \
        "${SYMFONY_CACHE_DIR}" \
        "${SYMFONY_LOG_DIR}" \
        "${SYMFONY_ARQUIVOS_DIR}" \
        && true

# Set container workdir
WORKDIR ${WORKDIR}

# Define exposed port
EXPOSE 9000

# Copy bin and entrypoint
COPY docker/php/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["php-fpm"]

#
# APP
#
FROM builder AS app

# Define volumes
VOLUME ["${SYMFONY_CACHE_DIR}", "${SYMFONY_LOG_DIR}", "${SYMFONY_ARQUIVOS_DIR}"]

# Even with .dockerignore we will highlight the items to be copied
COPY bin bin/
COPY config config/
COPY src src/
COPY public public/
COPY composer.json composer.json
COPY composer.lock composer.lock

#
# APP DEV
#
FROM builder AS app_dev

# Define environment variables
ENV APP_ENV="dev"

# Set PHP configurations
COPY docker/php/${APP_ENV}/php.ini $PHP_INI_DIR/php.ini

# Prepare local user into container
ARG HOST_UID=0
ARG HOST_USER=root
ARG HOST_GID=0
ARG HOST_GROUP=root

# Prepare user and group
RUN ((id --group ${HOST_GID} 2> /dev/null) || (groupadd --gid=${HOST_GID} ${HOST_GROUP})) \
        && ((id --user ${HOST_UID} 2> /dev/null) || (useradd --uid=${HOST_UID} --gid=${HOST_GID} ${HOST_USER})) \
        && mkdir --parents /home/${HOST_USER}/.ssh/ \
        && chown --recursive ${HOST_USER}:${HOST_GROUP} /home/${HOST_USER}/ \
        && true

# Fix permissions
RUN chown --recursive ${HOST_USER}:${HOST_GROUP} \
        "${SYMFONY_CACHE_DIR}" \
        "${SYMFONY_LOG_DIR}" \
        "${SYMFONY_ARQUIVOS_DIR}" \
        "/usr/local/etc/php/conf.d/" \
        && true

# Define bash instead of shell
SHELL [ "/bin/bash", "-l", "-c" ]

# Define default user
USER ${HOST_USER}:${HOST_GROUP}

#
# APP STAGE
#
FROM app AS app_stage

# Define environment variables
ENV APP_ENV=stage

# Set PHP configurations
COPY docker/php/stage/php.ini $PHP_INI_DIR/php.ini

# Install vendors
RUN --mount=type=ssh COMPOSER_ALLOW_SUPERUSER=1 composer install --prefer-dist --optimize-autoloader --no-interaction -vvv \
        && composer clear-cache \
        && true

# Fix permissions
RUN chown --recursive www-data:www-data \
        "${SYMFONY_CACHE_DIR}" \
        "${SYMFONY_LOG_DIR}" \
        "${SYMFONY_ARQUIVOS_DIR}" \
        && true

# Set PHP user as default
USER www-data:www-data

# Clear de Syfmony's cache
RUN bin/console cache:clear --env=${APP_ENV} --no-interaction


#
# APP PROD
#
FROM app AS app_prod

# Define environment variables
ENV APP_ENV=stage

# Set PHP configurations
COPY docker/php/prod/php.ini $PHP_INI_DIR/php.ini

# Install vendors
RUN --mount=type=ssh COMPOSER_ALLOW_SUPERUSER=1 composer install --prefer-dist --optimize-autoloader --no-interaction -vvv \
        && composer clear-cache \
        && true

# Fix permissions
RUN chown --recursive www-data:www-data \
        "${SYMFONY_CACHE_DIR}" \
        "${SYMFONY_LOG_DIR}" \
        "${SYMFONY_ARQUIVOS_DIR}" \
        && true

# Set PHP user as default
USER www-data:www-data

# Clear de Syfmony's cache
RUN bin/console cache:clear --env=${APP_ENV} --no-interaction
