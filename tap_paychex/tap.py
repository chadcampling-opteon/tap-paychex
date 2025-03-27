"""Paychex tap class."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th  # JSON schema typing helpers

# TODO: Import your custom stream types here:
from tap_paychex import streams


class TapPaychex(Tap):
    """Paychex tap class."""

    name = "tap-paychex"

    # TODO: Update this section with the actual config values you expect:
    config_jsonschema = th.PropertiesList(
        th.Property(
            "client_id",
            th.StringType,
            required=True,
            secret=False,  # Flag config as protected.
            title="oAuth client id",
            description="The oAuth client id",
        ),
        th.Property(
            "client_secret",
            th.StringType,
            required=True,
            secret=True,  # Flag config as protected.
            title="oAuth client secret",
            description="The oAuth client secret",
        ),
    ).to_dict()

    def discover_streams(self) -> list[streams.PaychexStream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [
            streams.CompaniesStream(self),
            streams.WorkersStream(self),
            streams.WorkersCommunicationStream(self),
        ]


if __name__ == "__main__":
    TapPaychex.cli()
