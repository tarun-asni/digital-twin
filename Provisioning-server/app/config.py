# app/config.py
import urllib.parse
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DEVICE_ID: str = Field(..., env="PROV_DEVICE_ID")

     # Certificate & CRL paths can come from .env or defaults
    CERT_DIR: str = Field("certs", env="CERT_DIR")
    ROOT_CA_CERT: str = Field("certs/rootCA.pem", env="ROOT_CA_CERT")
    ROOT_CA_KEY: str = Field("certs/rootCA.key", env="ROOT_CA_KEY")
    CRL_PATH: str = Field("crl/combined.crl.pem", env="CRL_PATH")
    NGINX: str = Field("nginx", env="NGINX")
    
    class Config:
        env_file = ".env" if Path(".env").exists() else None

    @property
    def DATABASE_URL(self) -> str:
        encoded = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"postgresql://{self.DB_USER}:{encoded}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
