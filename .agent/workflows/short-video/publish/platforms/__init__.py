"""平台模块注册表 — 按 key 获取平台实例。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import PlatformBase

# 平台注册表: key → class
# 延迟导入，避免未安装 playwright 时报错
_REGISTRY: dict[str, type] = {}


def _ensure_registry():
    """首次调用时注册所有平台。"""
    if _REGISTRY:
        return

    from .xiaohongshu import XiaohongshuPlatform
    from .douyin import DouyinPlatform
    from .bilibili import BilibiliPlatform
    from .kuaishou import KuaishouPlatform

    for cls in [XiaohongshuPlatform, DouyinPlatform, BilibiliPlatform, KuaishouPlatform]:
        _REGISTRY[cls.key] = cls

    # 视频号单独处理（需要 playwright，可能未安装）
    try:
        from .weixin import WeixinChannelsPublisher  # noqa: F401
        _REGISTRY["weixin"] = None  # 特殊标记，走独立流程
    except ImportError:
        pass


def get_platform(key: str, project_root: Path, publish_dir: Path,
                 account: str = "creator", **kwargs) -> "PlatformBase":
    """根据 key 获取平台实例。

    Args:
        key: 平台标识 (xiaohongshu, douyin, bilibili, kuaishou)
        project_root: 项目根目录
        publish_dir: publish/ 目录
        account: 账号名称
        **kwargs: 平台特定参数（如 bilibili 的 tid）
    """
    _ensure_registry()

    cls = _REGISTRY.get(key)
    if cls is None:
        raise ValueError(f"不支持的平台或特殊平台: {key}")

    return cls(project_root=project_root, publish_dir=publish_dir,
               account=account, **kwargs)


def list_platforms() -> list[str]:
    """列出所有已注册的平台 key。"""
    _ensure_registry()
    return list(_REGISTRY.keys())


__all__ = ["get_platform", "list_platforms"]
