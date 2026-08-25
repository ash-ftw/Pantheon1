"""Secrets Extraction Engine — PRD Module 4 Item 4.

Scans service environment variables for sensitive patterns (*_KEY, *_SECRET, *_PASSWORD, etc.).
Extracts matching key-value pairs into Kubernetes V1Secret objects.
"""

import re

from kubernetes import client

SENSITIVE_PATTERNS = [
    re.compile(r".*KEY.*", re.IGNORECASE),
    re.compile(r".*SECRET.*", re.IGNORECASE),
    re.compile(r".*PASSWORD.*", re.IGNORECASE),
    re.compile(r".*TOKEN.*", re.IGNORECASE),
    re.compile(r".*AUTH.*", re.IGNORECASE),
    re.compile(r".*PRIVATE.*", re.IGNORECASE),
]


class SecretExtractor:
    """Extracts sensitive environment variables into Kubernetes Secrets."""

    def is_sensitive_key(self, key: str) -> bool:
        """Check if environment key matches any sensitive pattern."""
        return any(pattern.match(key) for pattern in SENSITIVE_PATTERNS)

    def extract_secrets(
        self, service_name: str, environment: dict[str, str], namespace: str
    ) -> tuple[dict[str, str], dict[str, str], client.V1Secret | None]:
        """Separate standard env vars from sensitive secrets and create a Kubernetes V1Secret.

        Returns:
            (plain_env, secret_env, k8s_secret_manifest)
        """
        plain_env: dict[str, str] = {}
        secret_env: dict[str, str] = {}

        for key, val in environment.items():
            if self.is_sensitive_key(key):
                secret_env[key] = val
            else:
                plain_env[key] = val

        k8s_secret: client.V1Secret | None = None
        if secret_env:
            secret_name = f"secret-{service_name}"
            # Kubernetes secrets store stringData for automatically base64-encoded secrets
            k8s_secret = client.V1Secret(
                api_version="v1",
                kind="Secret",
                metadata=client.V1ObjectMeta(
                    name=secret_name,
                    namespace=namespace,
                    labels={
                        "pantheon.io/service": service_name,
                        "pantheon.io/managed": "true",
                    },
                ),
                string_data=secret_env,
                type="Opaque",
            )

        return plain_env, secret_env, k8s_secret


secret_extractor = SecretExtractor()
