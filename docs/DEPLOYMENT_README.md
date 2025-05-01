# Deployment Documentation

## Local Development

### Prerequisites
- Docker and Docker Compose
- Node.js 16+
- Python 3.9+
- PostgreSQL 13+

### Local Setup
1. Clone the repository:
```bash
git clone <repository-url>
cd leadGen
```

2. Set up environment variables:
```bash
cp example.env .env
# Edit .env with your local configuration
```

3. Start the development environment:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- Database: localhost:5432

## Production Deployment

### Heroku Deployment

1. Install Heroku CLI:
```bash
brew install heroku/brew/heroku
```

2. Login to Heroku:
```bash
heroku login
```

3. Create Heroku apps:
```bash
# Create backend app
heroku create lead-gen-api

# Create frontend app
heroku create lead-gen-frontend
```

4. Set up Heroku PostgreSQL:
```bash
heroku addons:create heroku-postgresql:hobby-dev --app lead-gen-api
```

5. Configure environment variables:
```bash
# Backend
heroku config:set \
  FLASK_ENV=production \
  SECRET_KEY=<your-secret-key> \
  ALLOWED_ORIGINS=https://lead-gen-frontend.herokuapp.com \
  --app lead-gen-api

# Frontend
heroku config:set \
  NODE_ENV=production \
  NEXT_PUBLIC_API_URL=https://lead-gen-api.herokuapp.com \
  --app lead-gen-frontend
```

6. Deploy:
```bash
# Backend
git subtree push --prefix server heroku-api main

# Frontend
git subtree push --prefix frontend heroku-frontend main
```

### AWS Deployment

#### Prerequisites
- AWS CLI configured
- AWS ECS CLI installed
- Docker images pushed to ECR

#### Infrastructure (Using Terraform)
```hcl
# Example terraform configuration
provider "aws" {
  region = "us-west-2"
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  # VPC configuration
}

module "ecs" {
  source = "terraform-aws-modules/ecs/aws"
  # ECS configuration
}

module "rds" {
  source = "terraform-aws-modules/rds/aws"
  # RDS configuration
}
```

#### Deployment Steps
1. Build and push Docker images:
```bash
# Login to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com

# Build and push
docker build -t lead-gen-api ./server
docker tag lead-gen-api:latest $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/lead-gen-api:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/lead-gen-api:latest
```

2. Apply Terraform configuration:
```bash
terraform init
terraform plan
terraform apply
```

3. Update ECS services:
```bash
aws ecs update-service --cluster lead-gen --service api --force-new-deployment
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
name: CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: docker-compose run --rm test

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to staging
        run: |
          heroku container:push web --app lead-gen-staging
          heroku container:release web --app lead-gen-staging

  deploy-production:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to production
        run: |
          heroku container:push web --app lead-gen-production
          heroku container:release web --app lead-gen-production
```

## Monitoring and Logging

### Services Used
- New Relic for application monitoring
- Papertrail for log aggregation
- Sentry for error tracking

### Setup Monitoring
```bash
# New Relic
heroku addons:create newrelic:wayne --app lead-gen-api

# Papertrail
heroku addons:create papertrail:choklad --app lead-gen-api

# Sentry
heroku config:set SENTRY_DSN=<your-sentry-dsn> --app lead-gen-api
```

## Backup and Recovery

### Database Backups
```bash
# Manual backup
heroku pg:backups:capture --app lead-gen-api

# Schedule daily backups
heroku pg:backups:schedule --at '02:00 America/New_York' --app lead-gen-api

# Download latest backup
heroku pg:backups:download --app lead-gen-api
```

### Recovery Procedures
1. Restore from backup:
```bash
heroku pg:backups:restore b101 DATABASE_URL --app lead-gen-api
```

2. Verify data integrity:
```bash
heroku run python manage.py check --app lead-gen-api
```

## Security Considerations

1. SSL/TLS Configuration
2. Regular security updates
3. Access control and authentication
4. Data encryption
5. Regular security audits
6. Compliance requirements (GDPR, CCPA)

## Rollback Procedures

### Heroku Rollback
```bash
# Roll back to previous release
heroku rollback --app lead-gen-api

# Roll back to specific release
heroku rollback v102 --app lead-gen-api
```

### Database Rollback
```bash
# Roll back last migration
heroku run python manage.py db downgrade --app lead-gen-api
``` 