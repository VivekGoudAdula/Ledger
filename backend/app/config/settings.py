"""Application Configuration Settings.

Defines environment-based configuration parameters for Ledger using Pydantic Settings.
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or defaults."""

    # Project Information
    PROJECT_NAME: str = "Ledger"
    VERSION: str = "0.8.0"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database & Storage
    DATABASE_URL: str = "sqlite+aiosqlite:///./ledger.db"
    SQLITE_WAL_MODE: bool = True

    # Ingestion API Keys
    GITHUB_TOKEN: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # Phase 2: Coalescing Configuration
    COALESCING_ENABLED: bool = True
    COALESCING_WINDOW_SECONDS: int = 300  # 5-minute time window for candidate matching
    SEMANTIC_SIMILARITY_ENABLED: bool = False
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.85

    # Phase 3: Valuation Configuration
    VALUE_ESTIMATOR_MODE: Literal["rule_based", "llm", "llm_with_fallback"] = "rule_based"
    VALUE_POLICY_VERSION: str = "v1.0"
    DEFAULT_COMPUTE_COST: float = 1.0
    AI_ESTIMATOR_TIMEOUT_SECONDS: float = 0.3
    AI_ESTIMATOR_CIRCUIT_BREAKER_FAILURES: int = 3
    AI_ESTIMATOR_API_KEY: str = ""

    # Phase 4 & 5: Queue & Broker Configuration
    QUEUE_BACKEND: Literal["redis", "memory"] = "memory"
    REDIS_URL: str = "redis://localhost:6379/0"
    LEDGER_STREAM_NAME: str = "ledger:work_stream"
    LEDGER_CONSUMER_GROUP: str = "ledger_workers"
    MAX_QUEUE_CAPACITY: int = 1000
    DEFAULT_LEASE_TIMEOUT_SECONDS: int = 30
    DEFAULT_MAX_RETRIES: int = 3

    # Phase 6: Worker Execution & Retry Configuration
    WORKER_COUNT: int = 3
    WORKER_MAX_CONCURRENCY: int = 4
    TASK_TIMEOUT_SECONDS: float = 30.0
    MAX_ATTEMPTS: int = 3
    RETRY_BASE_DELAY_SECONDS: float = 1.0
    RETRY_MAX_DELAY_SECONDS: float = 10.0

    # Phase 8: Failure Recovery & Fault Injection Configuration
    RECOVERY_ENABLED: bool = True
    RECOVERY_INTERVAL_SECONDS: float = 5.0
    RECOVERY_BATCH_SIZE: int = 10
    PENDING_STALE_AFTER_SECONDS: float = 10.0
    LEDGER_FAULT_INJECTION_ENABLED: bool = False

    # Admission Thresholds
    BASE_ADMISSION_THRESHOLD: float = 0.4
    HIGH_VALUE_THRESHOLD: float = 0.8
    DEFAULT_FRESHNESS_WINDOW_SECONDS: int = 3600

    # Tenant Controls
    DEFAULT_TENANT_QUOTA: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global settings instance singleton
settings = Settings()
