import os
import time


class Logger:
    def __init__(self, backup_dir: str):
        self.backup_dir = backup_dir
        self.log_file_path = os.path.join(backup_dir, "backup.log")
        os.makedirs(self.backup_dir, exist_ok=True)

    def log(self, message: str):
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{current_time}] {message}\n"
        print(log_msg.strip())
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(log_msg)

    def log_divider(self):
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write("--------------------------------------------------------\n")
