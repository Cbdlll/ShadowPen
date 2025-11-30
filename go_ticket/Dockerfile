# Build stage
FROM golang:1.23-bookworm AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application with CGO enabled (better compatibility with glibc)
RUN CGO_ENABLED=1 GOOS=linux go build -o ticket-system .

# Runtime stage
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/

# Copy binary from builder
COPY --from=builder /app/ticket-system .
COPY --from=builder /app/templates ./templates

EXPOSE 8080

CMD ["./ticket-system"]
