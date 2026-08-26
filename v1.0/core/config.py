from pydantic import field_validator
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
    # Debe reflejar el modelo real en uso: si CLAUDE_MODEL falta en el .env,
    # este default se aplica en silencio y el único aviso es el log de
    # arranque, que nadie mira. Un default desactualizado hace que un
    # despliegue mal configurado corra contra otro modelo sin que se note.
    claude_model: str = "claude-sonnet-5"

    port: int = 8000

    # Gate de los accesos rápidos de desarrollo (/auth/dev-login). Default
    # "production" a propósito: para activarlos hay que setear ENTORNO=development
    # explícitamente en .env — un .env faltante o mal copiado nunca los activa por error.
    entorno: str = "production"

    # Orígenes permitidos por CORS, separados por coma — ver main.py.
    # Cubre ambos puertos de Vite porque el 5173 puede estar ocupado
    # (ej. otra instancia corriendo) y Vite sube automáticamente al 5174,
    # sin avisar con un error obvio: la request simplemente falla por CORS.
    # En producción, IT/despliegue debe sobreescribir esta variable con el
    # dominio real del frontend — nunca dejar los puertos de localhost.
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:5174"

    @field_validator("cors_allowed_origins")
    @classmethod
    def _rechazar_comodin_cors(cls, valor: str) -> str:
        """Falla el arranque si CORS_ALLOWED_ORIGINS trae "*".

        main.py monta CORSMiddleware con allow_credentials=True. Combinado con
        un comodín, Starlette refleja CUALQUIER origen y le permite mandar
        cookies y el header Authorization: cualquier sitio web podría hacer
        requests autenticadas contra la API en nombre de un usuario logueado.

        Se aborta el arranque en vez de loguear un warning a propósito: un
        warning en un despliegue desatendido no lo lee nadie, y la app
        quedaría corriendo abierta. Mejor no levantar.
        """
        if any(origen.strip() == "*" for origen in valor.split(",")):
            raise ValueError(
                'CORS_ALLOWED_ORIGINS no puede incluir "*": la app usa '
                "allow_credentials=True (main.py), y esa combinación permite a "
                "cualquier sitio hacer requests autenticadas contra la API. "
                "Listá los dominios explícitamente, separados por coma."
            )
        return valor

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origen.strip() for origen in self.cors_allowed_origins.split(",") if origen.strip()]

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
