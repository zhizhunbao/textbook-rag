"""平台基类 — 所有平台模块的公共接口。"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger("publish")


class PlatformBase:
    """平台发布基类。

    子类需实现:
        - login()
        - check()
        - upload()
    """

    name: str = ""          # 中文名: 小红书
    key: str = ""           # 英文 key: xiaohongshu
    emoji: str = ""         # 图标

    def __init__(self, project_root: Path, publish_dir: Path, account: str = "creator"):
        self.project_root = project_root
        self.publish_dir = publish_dir
        self.account = account
        self.sau_dir = project_root / ".github" / "social-auto-upload"
        self.sau_cookies_dir = self.sau_dir / "cookies"

    # ── SAU CLI helpers ──────────────────────────────────────

    def _sau_cmd(self, args: list[str], timeout: int = 300,
                 interactive: bool = False) -> subprocess.CompletedProcess:
        """运行 SAU CLI 命令。"""
        cmd = ["uv", "run", "sau"] + args
        log.info(f"   $ {' '.join(cmd)}")

        if interactive:
            return subprocess.run(cmd, cwd=str(self.sau_dir), timeout=timeout)

        result = subprocess.run(
            cmd, cwd=str(self.sau_dir),
            capture_output=True, text=True, timeout=timeout,
        )
        if result.stdout.strip():
            log.info(f"   stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            log.warning(f"   stderr: {result.stderr.strip()}")
        return result

    @property
    def cookie_path(self) -> Path:
        """该平台的 cookie 文件路径。"""
        return self.sau_cookies_dir / f"{self.key}_{self.account}.json"

    # ── 接口方法 ─────────────────────────────────────────────

    def login(self) -> bool:
        """登录平台（扫码/浏览器）。"""
        raise NotImplementedError

    def check(self) -> bool:
        """检查登录状态。"""
        raise NotImplementedError

    def upload(self, video: Path, title: str, desc: str, tags: str,
               dry_run: bool = False) -> bool:
        """上传视频。"""
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__} key={self.key} account={self.account}>"
