# POC1 App - Production-Ready Express Application

Express web application containerized with Docker for AWS ECS Fargate deployment via CodePipeline blue/green strategy.

## Features

- Express server on port 3000
- Health check endpoint for ALB and ECS
- Environment variable configuration
- Docker optimized for layer caching
- Jest unit and integration tests
- ESLint with JUnit XML output
- SonarCloud integration
- Graceful shutdown for ECS task draining

## Environment Variables

- `PORT` - Server port (default: 3000)
- `NODE_ENV` - Environment mode (development/production)
- `DATABASE_URL` - Database connection string
- `API_KEY` - API authentication key

## Local Development

```bash
npm install
npm run dev
```

## Testing

```bash
# All tests
npm test

# Unit tests only
npm run test:unit

# Integration tests only
npm run test:integration

# Lint
npm run lint
```

## Docker Build

```bash
docker build -t poc1-app .
docker run -p 3000:3000 poc1-app
```

## Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check (returns `{ "status": "healthy" }`)

## AWS Deployment

The application is configured for ECS Fargate deployment with:
- `taskdef-template.json` - ECS task definition
- `appspec.yml` - CodeDeploy blue/green deployment spec
- Health checks for ALB and ECS task monitoring
- Graceful SIGTERM handling for task draining
