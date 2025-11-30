FROM ruby:3.2-alpine

# Install dependencies
RUN apk add --no-cache \
    build-base \
    sqlite-dev \
    sqlite

WORKDIR /app

# Install gems
RUN gem install sinatra sqlite3 rackup webrick

# Copy application code
COPY . .

# Expose port
EXPOSE 4567

# Start the application
CMD ["ruby", "app.rb"]

