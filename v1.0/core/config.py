from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "portafolio_iniciativas_anc"
    db_user: str = ""
    db_password: str = ""
    db_driver: str = "ODBC Driver 17 for SQL Server"

    claude_stub_mode: bool = True
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    port: int = 8000

    @property
    def database_url(self) -> str:
        driver_encoded = self.db_driver.replace(" ", "+")
        return (
            f"mssql+pyodbc://{self.db_user}:{self.db_password}"
            f"@{self.db_server}:{self.db_port}/{self.db_name}"
            f"?driver={driver_encoded}"
        )


settings = Settings()
