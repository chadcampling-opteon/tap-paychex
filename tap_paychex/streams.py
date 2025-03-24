"""Stream type classes for tap-paychex."""

from __future__ import annotations

import typing as t
from importlib import resources
from urllib.parse import urlparse

from tap_paychex.client import PaychexStream


SCHEMAS_DIR = resources.files(__package__) / "schemas"

class CompaniesStream(PaychexStream):
    """Define Companies stream."""
    pagination_support = False
    
    name = "companies"
    path = "/companies"
    primary_keys: t.ClassVar[list[str]] = ["companyId"]
    replication_key = None
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    schema_filepath = SCHEMAS_DIR / "companies.json"  # noqa: ERA001

    def get_child_context(self, record: dict, context: t.Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        workers_link = next((link["href"] for link in record["links"] if link["rel"] == "workers"), None)
        return {
           "workers_url": workers_link,
           "companyId": record["companyId"]
        }

class WorkersStream(PaychexStream):
    """Define Companies stream."""
    _LOG_REQUEST_METRIC_URLS = True
    pagination_support = True
    
    name = "workers"
    parent_stream_type = CompaniesStream
    ignore_parent_replication_keys = True
    path = None
    primary_keys: t.ClassVar[list[str]] = ["workerId"]
    replication_key = None
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    schema_filepath = SCHEMAS_DIR / "workers.json"  # noqa: ERA001

    def get_url(self, context):
        return context["workers_url"]
