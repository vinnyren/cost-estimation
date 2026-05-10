from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COST_", env_file=".env")

    data_dir: Path = Path.home() / ".claude" / "projects" / "cost-estimation"
    db_path: Path = data_dir / "db" / "cost.sqlite"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8788
    auth_token: str = ""  # 启动时注入
    csbmk_seed_path: Path = Path(__file__).parent / "data" / "csbmk_202510.json"


settings = Settings()
