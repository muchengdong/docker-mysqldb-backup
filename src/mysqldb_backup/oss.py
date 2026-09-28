from abc import ABC, abstractmethod
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mysqldb_backup.environment import Environment
    from mysqldb_backup.logger import Logger


class OSS(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def upload_file(self, local_file_path: str) -> bool: ...

    @classmethod
    def newInstance(cls, env: "Environment", logger: "Logger") -> "OSS":
        store_type = env.STORE_TYPE.lower().strip()
        if store_type == "github":
            return _GHOSSImpl(env, logger)
        else:
            raise ValueError(f"未知的 STORE_TYPE 存储类型: {env.STORE_TYPE}")


class _GHOSSImpl(OSS):
    def __init__(self, env: "Environment", logger: "Logger"):
        self.env = env
        self.logger = logger
        if not self.env.GITHUB_TOKEN or not self.env.GITHUB_REPO:
            raise ValueError("未配置 GITHUB_TOKEN 或 GITHUB_REPO")

        try:
            from github import Github
        except ImportError:
            raise ImportError("未检测到 GitHub SDK，请先执行 'pip install PyGithub'")

        self.gh = Github(self.env.GITHUB_TOKEN)

    @property
    def name(self):
        return "GitHub"

    def upload_file(self, local_file_path: str) -> bool:
        if not os.path.exists(local_file_path):
            self.logger.log(f"GitHub上传失败: 本地文件不存在 {local_file_path}")
            return False

        file_name = os.path.basename(local_file_path)
        remote_path = f"{self.env.GITHUB_PATH.strip('/')}/{file_name}"

        self.logger.log(f"开始将备份文件同步至 GitHub 仓库 [{self.env.GITHUB_REPO}]...")

        from github import GithubException

        try:
            repo = self.gh.get_repo(self.env.GITHUB_REPO)

            # 读取二进制文件内容
            with open(local_file_path, "rb") as f:
                content = f.read()

            # 使用 PyGithub 直接向远程仓库创建文件 (API 支持最大 100MB 级别文件)
            repo.create_file(
                path=remote_path,
                message=f"Automated DB Backup: {file_name}",
                content=content,
                branch="main",
            )

            self.logger.log(f"GitHub同步成功! 远程路径: {remote_path}")
            return True

        except GithubException as ge:
            self.logger.log(
                f"GitHub SDK 异常: 状态码 {ge.status}, 详情: {ge.data.get('message', str(ge))}"
            )
            return False
        except Exception as e:
            self.logger.log(f"GitHub上传时发生未知异常: {str(e)}")
            return False
