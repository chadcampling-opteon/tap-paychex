"""REST client handling, including PaychexStream base class."""

from __future__ import annotations

from abc import ABCMeta
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import json
import typing as t
from functools import cached_property
from importlib import resources

from singer_sdk.pagination import BaseAPIPaginator, SimpleHeaderPaginator  # noqa: TC002
from singer_sdk.streams import RESTStream
from singer_sdk.helpers.jsonpath import extract_jsonpath

from tap_paychex.auth import PaychexAuthenticator, PaychexTimeAuthenticator

if t.TYPE_CHECKING:
    import requests
    from singer_sdk.helpers.types import Auth, Context


# TODO: Delete this is if not using json files for schema definition
SCHEMAS_DIR = resources.files(__package__) / "schemas"


class PaychexStream(RESTStream):
    """Paychex stream class."""
    # Set to true for endpoints that support pagination
    pagination_support = False
    
    # Paychex recommend a max 100 page size
    _page_size = 100
    
    # Used in Paychex pagination
    _etag = None

    # Update this value if necessary or override `parse_response`.
    records_jsonpath = "$.content[*]"

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return "https://api.paychex.com"

    @cached_property
    def authenticator(self) -> Auth:
        """Return a new authenticator object.

        Returns:
            An authenticator instance.
        """
        return PaychexAuthenticator.create_for_stream(self)

    @property
    def http_headers(self) -> dict:
        """Return headers dict to be used for HTTP requests.

        If an authenticator is also specified, the authenticator's headers will be
        combined with `http_headers` when making HTTP requests.

        Returns:
            Dictionary of HTTP headers to use as a base for every request.
        """
        if self.pagination_support and self._etag:
            return self._http_headers | {"ETag": self._etag}
        return self._http_headers

    def get_new_paginator(self) -> BaseAPIPaginator:
        """Create a new pagination helper instance.

        If the source API can make use of the `next_page_token_jsonpath`
        attribute, or it contains a `X-Next-Page` header in the response
        then you can remove this method.

        If you need custom pagination that uses page numbers, "next" links, or
        other approaches, please read the guide: https://sdk.meltano.com/en/v0.25.0/guides/pagination-classes.html.

        Returns:
            A pagination helper instance.
        """
        if self.pagination_support:
            return PaychexPaginator(page_size=self._page_size)
        
        return SimpleHeaderPaginator("X-Next-Page")

    def get_url_params(
        self,
        context: Context | None,  # noqa: ARG002
        next_page_token: t.Any | None,  # noqa: ANN401
    ) -> dict[str, t.Any]:
        """Return a dictionary of values to be used in URL parameterization.

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary of URL query parameters.
        """
        params: dict = {}
        if self.pagination_support:
            params["limit"] = self._page_size

            if(next_page_token):
                params["offset"] = next_page_token["offset"]
                
            else:
                params["offset"] = self._start_offset

        return params

    def prepare_request_payload(
        self,
        context: Context | None,  # noqa: ARG002
        next_page_token: t.Any | None,  # noqa: ARG002, ANN401
    ) -> dict | None:
        """Prepare the data payload for the REST API request.

        By default, no payload will be sent (return None).

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary with the JSON body for a POST requests.
        """
        if self.pagination_support and next_page_token and "etag" in next_page_token:
                self._etag= f"""{next_page_token["etag"]}"""
        return None

class PaychexPaginator(BaseAPIPaginator[dict], metaclass=ABCMeta):
    """Paginator class for APIs that use page offset."""

    def __init__(
        self,
        page_size: int,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        """Create a new paginator.

        Args:
            start_value: Initial value.
            page_size: Constant page size.
            args: Paginator positional arguments.
            kwargs: Paginator keyword arguments.
        """
        super().__init__({"offset": 0}, *args, **kwargs)
        self._page_size = page_size

   
    def get_next(self, response: requests.Response) -> dict | None:
        """Get the next page offset.

        Args:
            response: API response object.

        Returns:
            The next page offset.
        """
        offset = self._value["offset"] + self._page_size
        etag = response.headers["etag"]
        result = {
            "offset": offset,
            "etag": etag
        }
        return result
    
class PaychexTimeStream(RESTStream):
    """Paychex stream class."""
    # Set to true for endpoints that support pagination
    pagination_support = False
    
    # Paychex recommend a max 100 page size
    #_page_size = 60
    
    http_method = "POST"
    
    # Used in Paychex pagination
    #_etag = None

    # Update this value if necessary or override `parse_response`.
    records_jsonpath = "$.Results[*]"

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return "https://paychex.centralservers.com/service/ws-json/2.0"

    @cached_property
    def authenticator(self) -> Auth:
        """Return a new authenticator object.

        Returns:
            An authenticator instance.
        """
        return PaychexTimeAuthenticator.create_for_stream(self)

    def get_new_paginator(self):        
        return SimpleHeaderPaginator("X-Next-Page")

class PaychexTimePaginator(BaseAPIPaginator[dict], metaclass=ABCMeta):
    """Paginator class for APIs that use date range pagination. Will page by months"""

    def __init__(
        self,
        day_count_window: int,
        day_count_future: int,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        """Create a new paginator.

        Args:
            start_value: Initial value.
            page_size: Constant page size.
            args: Paginator positional arguments.
            kwargs: Paginator keyword arguments.
        """
        self.end_date_signpost = ((datetime.now(timezone.utc)) + relativedelta(days=day_count_future)).replace(hour=0, minute=0, second=0, microsecond=0)
        self.day_count_window = day_count_window
        super().__init__({}, *args, **kwargs)
        self._jsonpath = "$.EndDate"
        
    def continue_if_empty(self, response):
        return True
   
    def get_next(self, response: requests.Response) -> dict | None:
        """Get the next page offset.

        Args:
            response: API response object.

        Returns:
            The next page offset.
        """
        request_json = json.loads(response.request.body)
        all_matches = extract_jsonpath(self._jsonpath, request_json)
        last_end_date = next(all_matches, None)
        
        start_date = datetime.fromtimestamp(int(last_end_date[6:16]), tz=timezone.utc)
        end_date = start_date + relativedelta(days=self.day_count_window)
        
        if start_date >= self.end_date_signpost:
            return None
        
        if end_date > self.end_date_signpost:
            end_date = self.end_date_signpost
            
        result = {
            "start_date": start_date,
            "end_date": end_date
        }
        return result