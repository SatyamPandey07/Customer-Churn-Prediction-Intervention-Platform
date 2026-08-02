import os
from abc import ABC, abstractmethod
import hvac

class SecretsManager(ABC):
    @abstractmethod
    def get_secret(self, key: str) -> str:
        pass

class EnvSecretsManager(SecretsManager):
    """Fallback manager that reads from local environment variables."""
    def get_secret(self, key: str) -> str:
        return os.environ.get(key)

class VaultSecretsManager(SecretsManager):
    """HashiCorp Vault implementation."""
    def __init__(self):
        # In production, use VAULT_ADDR and VAULT_TOKEN / k8s auth
        self.client = hvac.Client(url=os.environ.get("VAULT_ADDR", "http://localhost:8200"))
        
        # Simple token auth for demonstration; in k8s, use kubernetes auth method
        token = os.environ.get("VAULT_TOKEN")
        if token:
            self.client.token = token
            
    def get_secret(self, key: str) -> str:
        try:
            # Assumes a kv-v2 engine mounted at 'secret' and a document named 'churn-platform'
            response = self.client.secrets.kv.v2.read_secret_version(path='churn-platform')
            return response['data']['data'].get(key)
        except Exception:
            return None

def get_secrets_manager() -> SecretsManager:
    """Factory to get the configured secrets manager."""
    provider = os.environ.get("SECRETS_PROVIDER", "env").lower()
    if provider == "vault":
        return VaultSecretsManager()
    return EnvSecretsManager()

# Global instance
secrets_manager = get_secrets_manager()
