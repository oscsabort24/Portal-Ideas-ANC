from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "portafolio_iniciativas_anc"
    db_user: str = ""
    db_password: str = ""
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_trust_server_certificate: str = "yes"

    claude_stub_mode: bool = True
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    port: int = 8000

    # App registrada en Azure AD para validar tokens de Microsoft (core/auth.py).
    azure_tenant_id: str = "d65ee34b-c754-4f66-8183-35ac0ba333e9"
    azure_api_audience: str = "api://3a7ec4f9-f75a-46dd-ab57-1b0005e6c56b"

    @property
    def database_url(self) -> str:
        driver_encoded = self.db_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://{self.db_user}:{self.db_password}"
            f"@{self.db_server}:{self.db_port}/{self.db_name}"
            f"?driver={driver_encoded}"
            f"&TrustServerCertificate={self.db_trust_server_certificate}"
        )


settings = Settings()
