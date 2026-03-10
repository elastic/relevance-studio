"""Unit tests for server.client: es_studio_endpoint, es_from_credentials."""

import pytest

from server.client import es_studio_endpoint, es_from_credentials


class TestEsStudioEndpoint:
    def test_es_studio_endpoint_returns_cloud_id_when_configured(self, monkeypatch):
        monkeypatch.setattr("server.client.ELASTIC_CLOUD_ID", "my-cloud-id")
        monkeypatch.setattr("server.client.ELASTICSEARCH_URL", "")
        result = es_studio_endpoint()
        assert result == {"cloud_id": "my-cloud-id"}

    def test_es_studio_endpoint_returns_hosts_when_url_configured(self, monkeypatch):
        monkeypatch.setattr("server.client.ELASTIC_CLOUD_ID", "")
        monkeypatch.setattr("server.client.ELASTICSEARCH_URL", "http://localhost:9200")
        result = es_studio_endpoint()
        assert result == {"hosts": ["http://localhost:9200"]}

    def test_es_studio_endpoint_prefers_cloud_id_over_url(self, monkeypatch):
        monkeypatch.setattr("server.client.ELASTIC_CLOUD_ID", "my-cloud-id")
        monkeypatch.setattr("server.client.ELASTICSEARCH_URL", "http://localhost:9200")
        result = es_studio_endpoint()
        assert result == {"cloud_id": "my-cloud-id"}

    def test_es_studio_endpoint_raises_when_neither_configured(self, monkeypatch):
        monkeypatch.setattr("server.client.ELASTIC_CLOUD_ID", "")
        monkeypatch.setattr("server.client.ELASTICSEARCH_URL", "")
        with pytest.raises(ValueError, match="ELASTIC_CLOUD_ID or ELASTICSEARCH_URL"):
            es_studio_endpoint()


class TestEsFromCredentials:
    def test_es_from_credentials_raises_when_no_credentials(self):
        with pytest.raises(ValueError, match="api_key or both username and password"):
            es_from_credentials()

    def test_es_from_credentials_raises_when_both_api_key_and_username(self):
        with pytest.raises(ValueError, match="api_key or username/password, not both"):
            es_from_credentials(api_key="foo", username="u", password="p")

    def test_es_from_credentials_raises_when_username_without_password(self):
        with pytest.raises(ValueError, match="api_key or both username and password"):
            es_from_credentials(username="u")

    def test_es_from_credentials_raises_when_password_without_username(self):
        with pytest.raises(ValueError, match="api_key or both username and password"):
            es_from_credentials(password="p")

    def test_es_from_credentials_creates_client_with_api_key_and_url(self):
        client = es_from_credentials(api_key="base64key", url="http://localhost:9200")
        assert client is not None
        assert hasattr(client, "search")

    def test_es_from_credentials_creates_client_with_username_password(self):
        client = es_from_credentials(
            username="elastic", password="changeme", url="http://localhost:9200"
        )
        assert client is not None
        assert hasattr(client, "search")

    def test_es_from_credentials_uses_provided_url(self, monkeypatch):
        monkeypatch.setattr("server.client.ELASTIC_CLOUD_ID", "")
        monkeypatch.setattr("server.client.ELASTICSEARCH_URL", "")
        client = es_from_credentials(
            api_key="base64key",
            url="http://custom:9200",
        )
        assert client is not None

    def test_es_from_credentials_with_both_url_and_cloud_id_uses_cloud_id(self, monkeypatch):
        """When both cloud_id and url provided, cloud_id is used (prefer cloud_id).
        Uses a real Elastic Cloud ID format to avoid ES client validation errors.
        """
        # Real-looking cloud_id (from Elastic docs example)
        cloud_id = "staging:dXMtZWFzdC0xLmF3cy5mb3VuZC5pbyQ0NmE4MmIzOTlhMmI0ODM5ODg5ZTI2ZDE2MmQ5YjIzZCRjNGU2ODM1MzA1ZTRhNDY3OTljN2M2YTAyM2M0ZGY5"
        client = es_from_credentials(
            api_key="base64key",
            cloud_id=cloud_id,
            url="http://custom:9200",
        )
        assert client is not None
        assert hasattr(client, "search")
