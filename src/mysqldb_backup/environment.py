import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(BaseSettings):
    CONTAINER_NAME: str = Field(
        default="mysql-server", description="Docker 容器名称或 ID"
    )
    DB_USER: str = Field(default="root", description="数据库用户名")
    DB_PASS: str = Field(..., description="数据库密码")
    DB_NAME: str = Field(..., description="需要备份的特定数据库名")
    BACKUP_DIR: str = Field(default="/data/backup/mysql", description="宿主机备份路径")
    KEEP_DAYS: int = Field(default=30, description="备份文件保留天数")

    STORE_TYPE: str = Field(default="github", description="存储类型: github, oss, cos 等")
    GITHUB_TOKEN: Optional[str] = Field(None)
    GITHUB_REPO: Optional[str] = Field(None)
    GITHUB_PATH: str = Field(default="backups")

    model_config = SettingsConfigDict(
        env_file=os.getenv("CUSTOM_ENV_FILE", ".env"), 
        env_file_encoding="utf-8",
        extra="ignore",
    )


try:
    environment = Environment()
except Exception as e:
    print(f"配置加载失败，请检查环境变量或 .env 文件: {e}")
    exit(1)
