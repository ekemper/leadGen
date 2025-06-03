from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
import json

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI K8s Worker Prototype"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Should be from environment
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                # Parse JSON array string
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    # Fallback to treating as comma-separated
                    return [i.strip() for i in v.split(",")]
            else:
                # Comma-separated string
                return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_connection(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        postgres_server = values.data.get("POSTGRES_SERVER")
        postgres_user = values.data.get("POSTGRES_USER")
        postgres_password = values.data.get("POSTGRES_PASSWORD")
        postgres_db = values.data.get("POSTGRES_DB")
        return f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}/{postgres_db}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    @field_validator("REDIS_URL", mode="before")
    def assemble_redis_connection(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        redis_host = values.data.get("REDIS_HOST")
        redis_port = values.data.get("REDIS_PORT")
        redis_db = values.data.get("REDIS_DB")
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @field_validator("CELERY_BROKER_URL", mode="before")
    def set_celery_broker(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return values.data.get("REDIS_URL", "")

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    def set_celery_backend(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            return v
        return values.data.get("REDIS_URL", "")

    # Rate Limiter Configuration
    # MillionVerifier API Rate Limits
    MILLIONVERIFIER_RATE_LIMIT_REQUESTS: int = 60
    MILLIONVERIFIER_RATE_LIMIT_PERIOD: int = 60
    
    # Apollo API Rate Limits
    APOLLO_RATE_LIMIT_REQUESTS: int = 30
    APOLLO_RATE_LIMIT_PERIOD: int = 60
    
    # Instantly API Rate Limits
    INSTANTLY_RATE_LIMIT_REQUESTS: int = 100
    INSTANTLY_RATE_LIMIT_PERIOD: int = 60
    
    # OpenAI API Rate Limits
    # Reduced from 60 to 15 requests per minute to stay within OpenAI's 10,000 TPM limit
    # With average ~500 tokens per request, 15 requests ≈ 7,500 tokens, leaving safety margin
    OPENAI_RATE_LIMIT_REQUESTS: int = 15
    OPENAI_RATE_LIMIT_PERIOD: int = 60
    
    # Perplexity API Rate Limits
    PERPLEXITY_RATE_LIMIT_REQUESTS: int = 50
    PERPLEXITY_RATE_LIMIT_PERIOD: int = 60

    # External API Tokens
    # Added to fix critical configuration management failure where ApolloService
    # was refactored to use settings object but this field was never added
    APIFY_API_TOKEN: str
    APOLLO_ACTOR_ID: str = "code_crafter/apollo-io-scraper"

    @field_validator(
        "MILLIONVERIFIER_RATE_LIMIT_REQUESTS", "MILLIONVERIFIER_RATE_LIMIT_PERIOD",
        "APOLLO_RATE_LIMIT_REQUESTS", "APOLLO_RATE_LIMIT_PERIOD",
        "INSTANTLY_RATE_LIMIT_REQUESTS", "INSTANTLY_RATE_LIMIT_PERIOD",
        "OPENAI_RATE_LIMIT_REQUESTS", "OPENAI_RATE_LIMIT_PERIOD",
        "PERPLEXITY_RATE_LIMIT_REQUESTS", "PERPLEXITY_RATE_LIMIT_PERIOD",
        mode="before"
    )
    def validate_rate_limit_integers(cls, v):
        """Validate rate limit configuration values as positive integers."""
        if isinstance(v, str):
            # Handle comments in env values (e.g., "60  # requests per minute")
            value = v.split('#')[0].strip()
            parsed = int(value)
        else:
            parsed = int(v)
        
        if parsed <= 0:
            raise ValueError(f"Rate limit values must be positive integers, got: {parsed}")
        return parsed

    # Logging Configuration
    LOG_DIR: str = "./logs"
    LOG_LEVEL: str = "INFO"
    LOG_ROTATION_SIZE: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_SERVICE_HOST: str = "localhost"
    LOG_SERVICE_PORT: int = 8765
    LOG_BUFFER_SIZE: int = 1000

    @field_validator("LOG_ROTATION_SIZE", "LOG_BACKUP_COUNT", "LOG_SERVICE_PORT", "LOG_BUFFER_SIZE", mode="before")
    def validate_integers(cls, v):
        if isinstance(v, str):
            # Handle comments in env values (e.g., "10485760  # 10MB")
            value = v.split('#')[0].strip()
            return int(value)
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"

def get_redis_connection():
    """
    Create and return a Redis connection for rate limiting.
    
    This function creates a Redis connection using the application settings
    and is designed to be used by the rate limiter functionality.
    
    Returns:
        Redis: A Redis client instance configured from application settings
        
    Raises:
        ConnectionError: If Redis connection cannot be established
    """
    from redis import Redis
    
    try:
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,  # Ensures string responses instead of bytes
            socket_connect_timeout=5,  # 5 second connection timeout
            socket_timeout=5,  # 5 second socket timeout
            retry_on_timeout=True,
            health_check_interval=30  # Check connection health every 30 seconds
        )
        
        # Test the connection
        redis_client.ping()
        return redis_client
        
    except Exception as e:
        from app.core.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise ConnectionError(f"Could not connect to Redis: {str(e)}")

settings = Settings() 