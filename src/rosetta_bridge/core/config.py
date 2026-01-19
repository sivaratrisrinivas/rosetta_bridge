import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    connection_string: str


class LLMConfig(BaseModel):
    model: str = "gemini-1.5-flash"
    temperature: float = 0.0


class PrivacyConfig(BaseModel):
    sample_rows: bool = False
    scrub_pii: bool = True


class RosettaMap(BaseModel):
    project_name: str
    database: DatabaseConfig
    whitelist_tables: list[str] = Field(default_factory=list)
    llm_config: LLMConfig = Field(default_factory=LLMConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


class Settings(BaseSettings):
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


def _expand_env_value(value: str, settings: Settings) -> str:
    match = _ENV_PATTERN.match(value)
    if not match:
        return value
    env_name = match.group(1)
    if env_name == "DATABASE_URL" and settings.database_url:
        return settings.database_url
    if env_name == "GEMINI_API_KEY" and settings.gemini_api_key:
        return settings.gemini_api_key
    return os.getenv(env_name, value)


def load_rosetta_map(path: Path, settings: Settings | None = None) -> RosettaMap:
    settings = settings or Settings()
    payload = yaml.safe_load(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("rosetta_map.yaml must be a mapping at the top level")

    database = payload.get("database", {})
    connection = database.get("connection_string")
    if isinstance(connection, str):
        database["connection_string"] = _expand_env_value(connection, settings)
    payload["database"] = database

    return RosettaMap.model_validate(payload)


def default_rosetta_map(project_name: str = "rosetta-bridge") -> RosettaMap:
    return RosettaMap(
        project_name=project_name,
        database=DatabaseConfig(connection_string="${DATABASE_URL}"),
        whitelist_tables=[],
        llm_config=LLMConfig(),
        privacy=PrivacyConfig(),
    )


def write_default_rosetta_map(path: Path, project_name: str = "rosetta-bridge") -> None:
    payload = default_rosetta_map(project_name).model_dump()
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
    )
