import os
import sys
import time
import docker
from docker.errors import DockerException, NotFound
import gzip
from mysqldb_backup.environment import Environment
from mysqldb_backup.logger import Logger
from mysqldb_backup.oss import OSS


class MySQLBackup:
    def __init__(self, env: Environment, logger: Logger):
        self.env = env
        self.logger = logger

        try:
            if sys.platform == "win32":
                self.client = docker.DockerClient(
                    base_url="npipe:////./pipe/docker_engine"
                )
            else:
                self.client = docker.from_env()  # noqa
        except Exception as e:
            print(f"无法连接到 Docker 服务，请确认 Docker 是否已启动! 错误: {e}")

    def _generate_target_path(self) -> tuple[str, str]:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.env.DB_NAME}_backup_{timestamp}.sql.gz"

        temp_file = os.path.join(self.env.BACKUP_DIR,  f"{self.env.DB_NAME}.temp.sql") 
        final_file  = os.path.join(self.env.BACKUP_DIR, filename)
        return final_file, temp_file

    def backup(self):
        self.logger.log(
            f"开始备份 Docker 容器 [{self.env.CONTAINER_NAME}] 中的数据库 [{self.env.DB_NAME}]..."
        )
        target_file_path, temp_file_path = self._generate_target_path()

        try:
            container = self.client.containers.get(self.env.CONTAINER_NAME)
            if container.status != "running":
                self.logger.log(
                    f"错误: 容器 {self.env.CONTAINER_NAME} 当前未运行 (状态: {container.status})"
                )
                return

            dump_cmd = (
                f"mysqldump -u{self.env.DB_USER} -p{self.env.DB_PASS} "
                f"--single-transaction --routines --events --triggers {self.env.DB_NAME}"
            )

            exec_id = self.client.api.exec_create(
                container.id, dump_cmd, stdout=True, stderr=True
            )
            exec_stream = self.client.api.exec_start(exec_id, stream=True)

            with open(temp_file_path, "wb") as temp_file:
                for chunk in exec_stream:
                    temp_file.write(chunk)

            with open(temp_file_path, "rb") as temp_file, gzip.open(target_file_path, "wb") as f_out:
                for line in temp_file:
                    if line.startswith(b"mysqldump: "):
                        continue  # 跳过 mysqldump 的警告信息
                    f_out.write(line)

            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            exec_inspect = self.client.api.exec_inspect(exec_id)
            exit_code = exec_inspect.get("ExitCode", 0)
            if exit_code == 0 and os.path.getsize(target_file_path) > 20:
                self.logger.log(f"备份成功! 文件已保存至: {target_file_path}")
                try:
                    oss: OSS = OSS.newInstance(self.env, self.logger)
                    oss.upload_file(target_file_path)
                except Exception as e:
                    print(e)

            else:
                self.logger.log(
                    f"备份失败!!! 容器内命令退出码: {exit_code}. "
                )
                if os.path.exists(target_file_path):
                    os.remove(target_file_path)

        except NotFound:
            self.logger.log(f"错误: 未找到名为 [{self.env.CONTAINER_NAME}] 的容器。")
        except DockerException as de:
            self.logger.log(f"Docker SDK 异常: {str(de)}")
        except Exception as e:
            self.logger.log(f"未知异常: {str(e)}")

    def clean(self):
        self.logger.log(f"开始清理 {self.env.KEEP_DAYS} 天前的过期备份...")
        now = time.time()
        cutoff = now - (self.env.KEEP_DAYS * 86400)

        if not os.path.exists(self.env.BACKUP_DIR):
            return

        for file in os.listdir(self.env.BACKUP_DIR):
            if file.startswith(f"{self.env.DB_NAME}_backup_") and file.endswith(
                ".sql.gz"
            ):
                file_path = os.path.join(self.env.BACKUP_DIR, file)
                if os.path.getmtime(file_path) < cutoff:
                    try:
                        os.remove(file_path)
                        self.logger.log(f"已删除过期备份文件: {file}")
                    except Exception as e:
                        self.logger.log(f"删除文件 {file} 失败: {str(e)}")

        self.logger.log("清理完成。")
