import argparse
import os


def main() -> None:
    print("Hello from mysqldb-backup!")

    parser = argparse.ArgumentParser(description="MySQL Docker Backup Tool")
    parser.add_argument(
        "-e",
        "--env",
        type=str,
        default=".env",
        help="指定外部 .env 配置文件路径 (默认: 当前目录下的 .env)",
    )
    args = parser.parse_args()
    if args.env:
        if not os.path.exists(args.env):
            print(f"指定的 .env 文件不存在: {args.env}")
            return
        os.environ["CUSTOM_ENV_FILE"] = os.path.abspath(args.env)

    from mysqldb_backup.environment import environment
    from mysqldb_backup.logger import Logger
    from mysqldb_backup.backup import MySQLBackup

    backup = None

    try:
        logger = Logger(environment.BACKUP_DIR)
        backup = MySQLBackup(environment, logger)
        backup.backup()
    except Exception as e:
        print(e)
    finally:
        if backup is not None:
            backup.clean()


if __name__ == "__main__":
    main()  