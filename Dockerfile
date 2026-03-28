FROM node:16-alpine AS builder


WORKDIR /app

# Copy package files first for layer caching
COPY package*.json ./

# Install dependencies
RUN apk update && apk upgrade
RUN npm ci --only=production

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 3000

# Run as non-root user
USER node

CMD ["node", "src/index.js"]
