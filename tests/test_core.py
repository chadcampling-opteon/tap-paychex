"""Tests standard tap features using the built-in SDK tests library."""

import datetime

from singer_sdk.testing import get_tap_test_class

from tap_paychex.tap import TapPaychex

SAMPLE_CONFIG = {
    "client_id": "1234",
    "client_secret": "shhhh-secret"
}


# Run standard built-in tap tests from the SDK:
TestTapPaychex = get_tap_test_class(
    tap_class=TapPaychex,
    config=SAMPLE_CONFIG,
)


# TODO: Create additional tests as appropriate for your tap.
