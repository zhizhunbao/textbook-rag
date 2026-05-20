"""B站发布模块 — 通过 SAU CLI 上传。"""

from __future__ import annotations

import logging
from pathlib import Path

from .base import PlatformBase

log = logging.getLogger("publish.bilibili")

# B站分区 ID
# 生活 > 日常 = 249
DEFAULT_TID = 249


class BilibiliPlatform(PlatformBase):
    name = "B站"
    key = "bilibili"
    emoji = "📺"

    def __init__(self, *args, tid: int = DEFAULT_TID, **kwargs):
        super().__init__(*args, **kwargs)
        self.tid = tid

    def login(self) -> bool:
        """终端扫码登录（B站不支持 headed 模式）。"""
        log.info(f"\n{'='*60}")
        log.info(f"{self.emoji} 登录 {self.name} (account={self.account})")
        log.info(f"{'='*60}")
        log.info("   B站登录使用终端二维码，请在终端中扫码")
        result = self._sau_cmd(
            [self.key, "login", "--account", self.account],
            interactive=True,
        )
        return result.returncode == 0

    def check(self) -> bool:
        """检查 cookie 是否有效。"""
        if not self.cookie_path.exists():
            return False
        result = self._sau_cmd(
            [self.key, "check", "--account", self.account],
            timeout=30,
        )
        return result.returncode == 0

    def upload(self, video: Path, title: str, desc: str, tags: str,
               dry_run: bool = False) -> bool:
        """上传视频到B站。"""
        log.info(f"\n{self.emoji} 发布到 {self.name}...")

        if dry_run:
            log.info(f"   [DRY RUN] 跳过实际上传")
            log.info(f"   title: {title}")
            log.info(f"   desc:  {desc[:60]}...")
            log.info(f"   tags:  {tags}")
            log.info(f"   tid:   {self.tid}")
            return True

        result = self._sau_cmd([
            self.key, "upload-video",
            "--account", self.account,
            "--file", str(video.resolve()),
            "--title", title,
            "--desc", desc,
            "--tid", str(self.tid),
            "--tags", tags,
        ], timeout=600)
        return result.returncode == 0
