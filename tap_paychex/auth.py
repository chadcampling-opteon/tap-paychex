"""Paychex Authentication."""

from __future__ import annotations
import json
import typing as t
import requests
from singer_sdk.authenticators import OAuthAuthenticator, APIAuthenticatorBase, SingletonMeta

if t.TYPE_CHECKING:
    import logging

    from singer_sdk.streams.rest import _HTTPStream

class PaychexAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for Paychex."""
    
    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the AutomaticTestTap API.

        Returns:
            A dict with the request body
        """
        return {
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "grant_type": "client_credentials",
        }
    
    @classmethod
    def create_for_stream(
        cls,
        stream,  # noqa: ANN001
    ) -> PaychexAuthenticator:
        """Instantiate an authenticator for a specific Singer stream.

        Args:
            stream: The Singer stream instance.

        Returns:
            A new authenticator.
        """
        return cls(
            stream=stream,
            auth_endpoint="https://api.paychex.com/auth/oauth/v2/token",
            oauth_scopes="",
        )

class PaychexTimeAuthenticator(APIAuthenticatorBase):
    """Implements API key authentication for REST Streams.

    This authenticator will merge a key-value pair with either the
    HTTP headers or query parameters specified on the stream. Common
    examples of key names are "x-api-key" and "Authorization" but
    any key-value pair may be used for this authenticator.
    """
    _BODY_KEY = "AuthToken"
    auth_credentials = {}
    
    def __init__(
        self,
        stream: _HTTPStream
    ) -> None:
        """Create a new authenticator.

        Args:
            stream: The stream instance to use with this authenticator.
            key: API key parameter name.
            value: API key value.
            location: Where the API key is to be added. Either 'header' or 'params'.

        Raises:
            ValueError: If the location value is not 'header' or 'params'.
        """
        super().__init__(stream=stream)
        self.auth_credentials = {self._BODY_KEY: None}
        
    @classmethod
    def create_for_stream(
        cls: type[PaychexTimeAuthenticator],
        stream: _HTTPStream,
    ) -> PaychexTimeAuthenticator:
        """Create an Authenticator object specific to the Stream class.

        Args:
            stream: The stream instance to use with this authenticator.
            key: API key parameter name.
            value: API key value.
            location: Where the API key is to be added. Either 'header' or 'params'.

        Returns:
            APIKeyAuthenticator: A new
                :class:`singer_sdk.authenticators.APIKeyAuthenticator` instance.
        """
        return cls(stream=stream)
    
    def authenticate_request(self, request):
        if not self.auth_credentials.get(self._BODY_KEY):
            self.create_token()
            
        body_dict = json.loads(request.body)
        body_dict.update(self.auth_credentials)
        request.body = json.dumps(body_dict)
        return super().authenticate_request(request)
    
    def create_token(self):
        auth_request_payload = {
            "CustomerAlias": self.config["time_customer_alias"],
            "SharedKey": self.config["time_shared_key"],
            "UserName": "wsuser",
            "UserPass": self.config["time_password"],
        }
        token_response = requests.post(
            "https://paychex.centralservers.com/service/ws-json/2.0/CreateToken",
            json=auth_request_payload,
            timeout=60
        )
        
        try:
            token_response.raise_for_status()
        except requests.HTTPError as ex:
            msg = f"Failed OAuth login, response was '{token_response.json()}'. {ex}"
            raise RuntimeError(msg) from ex

        self.logger.info("Authorization attempt was successful.")

        token = token_response.json()
        self.auth_credentials[self._BODY_KEY] = token