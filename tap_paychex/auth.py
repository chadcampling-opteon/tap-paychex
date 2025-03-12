"""Paychex Authentication."""

from __future__ import annotations

from singer_sdk.authenticators import OAuthJWTAuthenticator


class PaychexAuthenticator(OAuthJWTAuthenticator):
    """Authenticator class for Paychex."""

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
            auth_endpoint="TODO: OAuth Endpoint URL",
            oauth_scopes="TODO: OAuth Scopes",
        )
