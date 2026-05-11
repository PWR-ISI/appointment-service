import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def _no_sns_publish(settings):
    """Tests should not require a configured SNS topic ARN."""
    settings.APPOINTMENT_SNS_TOPIC_ARN = ""
    yield
