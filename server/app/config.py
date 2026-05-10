from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COST_", env_file=".env")

    data_dir: Path = Path.home() / ".claude" / "projects" / "cost-estimation"
    # 派生路径：默认值为 None，由 _derive_paths model_validator 在实例化后基于
    # 最终的 data_dir 派生。这样 COST_DATA_DIR 改变时，所有派生路径都会跟随。
    # 显式设置 COST_DB_PATH / COST_UPLOAD_DIR / COST_EXPORT_DIR 时，validator
    # 会保留显式值，不会覆盖。
    db_path: Path | None = None
    upload_dir: Path | None = None
    parsed_dir: Path | None = None
    export_dir: Path | None = None
    bind_host: str = "127.0.0.1"
    bind_port: int = 8788
    auth_token: str = ""  # 启动时注入
    csbmk_seed_path: Path = Path(__file__).parent / "data" / "csbmk_202510.json"
    # 生产模式：web/dist 目录的绝对路径；为 None 时不挂载静态资源（开发模式走 vite proxy）。
    web_dist_dir: str | None = None

    @model_validator(mode="after")
    def _derive_paths(self) -> "Settings":
        """从 data_dir 派生 db_path / upload_dir / parsed_dir / export_dir。

        - 仅在字段为 None 时派生（保留显式 COST_* 环境变量的覆盖能力）。
        - 使用 object.__setattr__ 绕过 pydantic 的 frozen-style 字段守护
          (BaseSettings 默认 mutable，但派生赋值仍走该路径以保险)。
        """
        if self.db_path is None:
            object.__setattr__(self, "db_path", self.data_dir / "db" / "cost.sqlite")
        if self.upload_dir is None:
            object.__setattr__(self, "upload_dir", self.data_dir / "uploads")
        if self.parsed_dir is None:
            object.__setattr__(self, "parsed_dir", self.data_dir / "parsed")
        if self.export_dir is None:
            object.__setattr__(self, "export_dir", self.data_dir / "exports")
        return self


settings = Settings()
