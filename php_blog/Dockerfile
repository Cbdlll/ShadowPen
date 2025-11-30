FROM php:8.3-apache

# Install SQLite3 dependencies
RUN apt-get update && apt-get install -y \
    libsqlite3-dev \
    && docker-php-ext-install pdo_sqlite

# Enable Apache mod_rewrite
RUN a2enmod rewrite

# Set working directory
WORKDIR /var/www/html

# Copy source code
COPY src/ /var/www/html/

# Set permissions for SQLite database file (will be created by init script)
RUN chown -R www-data:www-data /var/www/html
