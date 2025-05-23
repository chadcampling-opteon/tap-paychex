"""Stream type classes for tap-paychex."""

from __future__ import annotations

from datetime import datetime, timezone
import typing as t
from importlib import resources
from urllib.parse import urlparse
from dateutil.relativedelta import relativedelta
from singer_sdk.helpers.jsonpath import extract_jsonpath

from tap_paychex.client import PaychexStream, PaychexTimePaginator, PaychexTimeStream


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
    """Define Workers stream."""
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

    @property
    def http_headers(self) -> dict:
        """Return headers for HTTP requests."""
        headers = super().http_headers
        headers["Accept"] = "application/vnd.paychex.workers_communications.v1+json"
        return headers

    def get_child_context(self, record: dict, context: t.Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        communications = record.get("communications")
        return {
           "communications": communications,
           "workerId": record["workerId"]
        }
    
class WorkersCommunicationStream(PaychexStream):
    """Define Workers Communication stream."""
    _LOG_REQUEST_METRIC_URLS = True
    pagination_support = False
    
    name = "workers_communication"
    parent_stream_type = WorkersStream
    path = None
    primary_keys: t.ClassVar[list[str]] = ["communicationId"]
    replication_key = None
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    schema_filepath = SCHEMAS_DIR / "workers_communication.json"  # noqa: ERA001
    
    ignore_parent_replication_key = False
    state_partitioning_keys = []
    
    def get_records(self, context):
        """Yield communication records with a valid communicationId."""
        communications = context.get("communications", [])
        for record in communications:
            if not record.get("communicationId"):
                continue
            transformed = self.post_process(record, context)
            if transformed is not None:
                yield transformed
    
    def post_process(self, row, context = None):
        row["workerId"] = context["workerId"]
        return row
    
class WorkersStatusHistoryStream(PaychexStream):
    """Define Workers Status History stream."""
    _LOG_REQUEST_METRIC_URLS = True
    pagination_support = False
    
    name = "workers_status_history"
    parent_stream_type = WorkersStream
    path = "/workers/{workerId}/status"
    primary_keys: t.ClassVar[list[str]] = ["workerId", "order"]
    replication_key = None
    # Optionally, you may also use `schema_filepath` in place of `schema`:
    schema_filepath = SCHEMAS_DIR / "workers_status_history.json"  # noqa: ERA001
    
    ignore_parent_replication_key = False
    state_partitioning_keys = []
    
    def post_process(self, row, context = None):
        row["workerId"] = context["workerId"]
        return row

class TimeOffRequest(PaychexTimeStream):

    name = "time_off_requests"
    path = "/GetUserTimeOffRequest"
    pagination_support = True
    
    schema_filepath = SCHEMAS_DIR / "time_off_requests.json"
    
    primary_keys: t.ClassVar[list[str]] = ["ID"]
    replication_key = "ExtractedDateTime"
    
    def prepare_request_payload(self, context, next_page_token):
        if not next_page_token:
            bookmark = self.get_starting_timestamp(context)
            if not bookmark:
                bookmark = (datetime.now(timezone.utc))
            
            start_date = (bookmark - relativedelta(days=59)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = bookmark.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date= next_page_token["start_date"]
            end_date= next_page_token["end_date"]
            
        return {
            "StartDate":f"/Date({int(start_date.timestamp()) * 1000}+0000)/",
            "EndDate":f"/Date({int(end_date.timestamp()) * 1000}+0000)/",
            "DateTimeSchema":0,
            "IgnoreDeletedRequests":False,
            "IgnoreDetails":True,
            "DataAction":{
                "Name":"SELECT-ALL"
            }
        }
        
    def get_new_paginator(self):
            return PaychexTimePaginator(day_count_window=59, day_count_future=180)
            
    def post_process(self, row, context = None):
        row['ExtractedDateTime'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        row['EndDateTime'] = row['EndDateTimeSchema']
        del row['EndDateTimeSchema']
        row['StartDateTime'] = row['StartDateTimeSchema']
        del row['StartDateTimeSchema']
        row['DateTimeSubmitted'] = datetime.fromtimestamp(int(row['DateTimeSubmitted'][6:16]), tz=timezone.utc)
        return row
        
class TimeUsers(PaychexTimeStream):

    name = "time_system_users"
    path = "/GetUserBasic"
    pagination_support = False
    
    schema_filepath = SCHEMAS_DIR / "time_users.json"
    
    primary_keys: t.ClassVar[list[str]] = ["EmpIdentifier","CustomerAlias"]
    
    def prepare_request_payload(self, context, next_page_token):
        return {
            "EffectiveDate":f"/Date({int(datetime.now(timezone.utc).timestamp()) * 1000}+0000)/",
            "DataAction":{
                "Name":"SELECT-ALL"
            }
        }
        
    def post_process(self, row, context = None):
        row['Email'] = None if row.get('Email') == '' else row.get('Email')
        row['CustomerAlias'] = self.config["time_customer_alias"]
        return row