"""
Long-poll the configured SQS queue and dispatch messages to registered handlers.

Each message is the SNS envelope (JSON) wrapped by SNS-to-SQS delivery, which
nests the actual payload under "Message". This command parses that, looks up
the handler in apps.appointments.handlers.HANDLERS, and only deletes the
message on success — failures leave it for SQS redelivery.

Runs as a separate container alongside the web app in prod-config and as an
ECS task in AWS.
"""
import json
import logging
import signal
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from common.aws import aws_client

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume domain events from SQS and dispatch to handlers."

    def add_arguments(self, parser):
        parser.add_argument("--max-messages", type=int, default=10)
        parser.add_argument("--wait-time", type=int, default=20)
        parser.add_argument("--visibility-timeout", type=int, default=60)
        parser.add_argument("--once", action="store_true", help="Drain once and exit.")

    def handle(self, *args, **opts):
        # Import handlers lazily so this command also works in services that
        # don't ship the appointments app (e.g. schedule-service has its own
        # handlers module).
        from apps.appointments.handlers import HANDLERS

        queue_url = settings.EVENTS_SQS_QUEUE_URL
        if not queue_url:
            self.stderr.write("EVENTS_SQS_QUEUE_URL is not configured; exiting.")
            return

        sqs = aws_client("sqs")
        running = {"flag": True}

        def _stop(signum, frame):
            self.stdout.write("Stop signal received; finishing in-flight batch.")
            running["flag"] = False

        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)

        self.stdout.write(f"Consuming from {queue_url} (handlers: {sorted(HANDLERS)})")

        while running["flag"]:
            resp = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=opts["max_messages"],
                WaitTimeSeconds=opts["wait_time"],
                VisibilityTimeout=opts["visibility_timeout"],
                MessageAttributeNames=["All"],
            )
            messages = resp.get("Messages", [])
            for msg in messages:
                if not self._process(msg, HANDLERS):
                    continue  # leave for redelivery
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])

            if opts["once"]:
                break
            if not messages:
                time.sleep(0.1)

    def _process(self, msg, handlers) -> bool:
        try:
            body = json.loads(msg["Body"])
        except (json.JSONDecodeError, KeyError):
            logger.exception("Invalid SQS message body; dropping.")
            return True  # delete malformed messages

        # SNS-to-SQS wraps payload under "Message"; raw SQS publishes don't.
        if isinstance(body, dict) and "Message" in body:
            try:
                envelope = json.loads(body["Message"])
            except json.JSONDecodeError:
                logger.exception("Invalid SNS Message envelope; dropping.")
                return True
        else:
            envelope = body

        event_type = envelope.get("event_type")
        handler = handlers.get(event_type)
        if not handler:
            logger.info("No handler for event_type=%s; ignoring.", event_type)
            return True

        try:
            handler(envelope.get("payload") or {}, envelope=envelope)
            return True
        except Exception:
            logger.exception("Handler for %s raised; leaving message for redelivery.", event_type)
            return False
