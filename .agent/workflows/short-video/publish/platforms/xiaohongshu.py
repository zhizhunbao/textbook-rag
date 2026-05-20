"""小红书发布模块 — 通过 SAU CLI 上传。"""

from __future__ import annotations

import logging
from pathlib import Path

from .base import PlatformBase

log = logging.getLogger("publish.xiaohongshu")


class XiaohongshuPlatform(PlatformBase):
    name = "小红书"
    key = "xiaohongshu"
    emoji = "📕"

    def login(self) -> bool:
        """Headed 模式扫码登录。"""
        log.info(f"\n{'='*60}")
        log.info(f"{self.emoji} 登录 {self.name} (account={self.account})")
        log.info(f"{'='*60}")
        result = self._sau_cmd(
            [self.key, "login", "--account", self.account, "--headed"],
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
        """上传视频到小红书。"""
        log.info(f"\n{self.emoji} 发布到 {self.name}...")

        if dry_run:
            log.info(f"   [DRY RUN] 跳过实际上传")
            log.info(f"   title: {title}")
            log.info(f"   desc:  {desc[:60]}...")
            log.info(f"   tags:  {tags}")
            return True

        result = self._sau_cmd([
            self.key, "upload-video",
            "--account", self.account,
            "--file", str(video.resolve()),
            "--title", title,
            "--desc", desc,
            "--tags", tags,
        ], timeout=600)
        return result.returncode == 0
