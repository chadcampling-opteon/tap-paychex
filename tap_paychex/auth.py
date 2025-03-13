"""Paychex Authentication."""

from __future__ import annotations

from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta


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
