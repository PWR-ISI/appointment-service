# appointment-service

Django microservice that owns the appointment aggregate for the ISI medical system.

## Responsibilities

- Create, retrieve, list, and cancel appointments.
- Coordinate with `schedule-service` (REST) to reserve a slot during creation.
- Publish `appointment.created`, `appointment.cancelled`, `appointment.completed` events to SNS.
- Consume `payment.succeeded`, `payment.failed`, `slot.released` events from SQS.

## Local run (standalone)

```powershell
Copy-Item .env.example .env
docker compose up --build
# http://localhost:8001/health/
# http://localhost:8001/api/docs/
```

## Local run (integrated with the rest of the system)

```powershell
cd ..\prod-config
docker compose up --build
# appointment-service published on http://localhost:8002
```

## Tests

```powershell
docker compose run --rm app pip install -r requirements-dev.txt
docker compose run --rm app pytest
```

## Environment variables

See `.env.example`. Notable variables:

- `AWS_ENDPOINT_URL` — point at LocalStack locally (`http://localstack:4566`), leave empty in real AWS.
- `APPOINTMENT_SNS_TOPIC_ARN` — where domain events are published.
- `EVENTS_SQS_QUEUE_URL` — queue the consumer worker drains.
- `SCHEDULE_SERVICE_URL` — base URL of schedule-service for inter-service REST.
- `INTERNAL_SHARED_TOKEN` — shared bearer token used in `X-Internal-Token` for service-to-service calls.

## AWS deployment

See `prod-config/terraform/modules/appointment-service/` for the Terraform module (ECS Fargate, ALB, RDS Postgres, SNS, SQS).
