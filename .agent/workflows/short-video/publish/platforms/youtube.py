"""
youtube.py — YouTube 平台发布模块
==================================

使用 Google YouTube Data API v3 上传视频。
首次使用需要 OAuth 2.0 授权，之后 token 自动刷新。

前置准备:
    1. 访问 https://console.cloud.google.com
    2. 创建项目 → 启用 YouTube Data API v3
    3. 创建 OAuth 2.0 客户端 ID（桌面应用）
    4. 下载 client_secrets.json 放到 publish/credentials/youtube/

凭证路径:
    client_secrets.json → publish/credentials/youtube/client_secrets.json
    oauth token         → publish/credentials/youtube/youtube_token.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE = "youtube"
YOUTUBE_API_VERSION = "v3"

# 视频分类 ID: 22 = People & Blogs, 27 = Education, 28 = Science & Tech
DEFAULT_CATEGORY_ID = "22"


class YouTubePlatform:
    """YouTube 平台（Google API）。"""

    key = "youtube"
    name = "YouTube"
    emoji = "🎬"

    def __init__(self, project_root: Path, publish_dir: Path,
                 account: str = "creator", **kwargs):
        self.project_root = project_root
        self.publish_dir = publish_dir
        self.account = account
        self.credentials_dir = publish_dir / "credentials" / "youtube"
        self.client_secrets_file = self.credentials_dir / "client_secrets.json"
        self.token_file = self.credentials_dir / "youtube_token.json"
        self.category_id = kwargs.get("category_id", DEFAULT_CATEGORY_ID)

    # ------------------------------------------------------------------
    # Login (OAuth 2.0)
    # ------------------------------------------------------------------
    def login(self) -> bool:
        """OAuth 2.0 授权流程，首次需要浏览器确认。"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            log.error("❌ 需要安装: pip install google-auth-oauthlib google-api-python-client")
            log.info("   或: uv pip install google-auth-oauthlib google-api-python-client")
            return False

        if not self.client_secrets_file.exists():
            log.error(f"❌ 找不到 client_secrets.json")
            log.info(f"   请从 Google Cloud Console 下载 OAuth 凭证放到:")
            log.info(f"   {self.credentials_dir}/client_secrets.json")
            log.info(f"")
            log.info(f"   步骤:")
            log.info(f"   1. 访问 https://console.cloud.google.com")
            log.info(f"   2. 创建项目 → API 和服务 → 启用 YouTube Data API v3")
            log.info(f"   3. 凭据 → 创建 OAuth 客户端 ID → 桌面应用")
            log.info(f"   4. 下载 JSON → 重命名为 client_secrets.json")
            return False

        self.credentials_dir.mkdir(parents=True, exist_ok=True)

        log.info("🌐 启动 YouTube OAuth 授权...")
        log.info("   浏览器会打开 Google 登录页面，请授权 YouTube 上传权限")

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_file),
                scopes=[YOUTUBE_UPLOAD_SCOPE],
            )
            credentials = flow.run_local_server(
                port=8080,
                prompt="consent",
                authorization_prompt_message="Please complete Google authorization in your browser...",
            )

            # 保存 token
            token_data = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": list(credentials.scopes),
            }
            self.token_file.write_text(
                json.dumps(token_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log.info(f"✅ YouTube 授权成功!")
            log.info(f"📁 Token 已保存: {self.token_file}")
            return True

        except Exception as e:
            log.error(f"❌ YouTube 授权失败: {e}")
            return False

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------
    def check(self) -> bool:
        """检查 YouTube token 是否存在。"""
        if not self.token_file.exists():
            return False

        try:
            data = json.loads(self.token_file.read_text(encoding="utf-8"))
            return bool(data.get("refresh_token"))
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    def upload(self, video_path: str, title: str, tags: list[str] | None = None,
               description: str = "", privacy: str = "public", **kwargs) -> bool:
        """上传视频到 YouTube。

        Args:
            video_path: 视频文件路径
            title: 视频标题
            tags: 标签列表
            description: 视频描述
            privacy: public / unlisted / private
        """
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            log.error("❌ 需要安装: pip install google-auth google-api-python-client")
            return False

        if not self.token_file.exists():
            log.error("❌ 请先运行 login 授权 YouTube")
            return False

        tags = tags or []

        # 加载并刷新 token
        token_data = json.loads(self.token_file.read_text(encoding="utf-8"))
        credentials = Credentials(
            token=token_data["token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data.get("scopes", [YOUTUBE_UPLOAD_SCOPE]),
        )

        if credentials.expired:
            log.info("🔄 刷新 YouTube token...")
            credentials.refresh(Request())
            # 更新保存
            token_data["token"] = credentials.token
            self.token_file.write_text(
                json.dumps(token_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        log.info(f"🎬 上传到 YouTube: {title}")

        try:
            youtube = build(YOUTUBE_API_SERVICE, YOUTUBE_API_VERSION,
                           credentials=credentials)

            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": self.category_id,
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                },
            }

            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                resumable=True,
                chunksize=10 * 1024 * 1024,  # 10MB chunks
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            # 分块上传
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    log.info(f"   📤 上传进度: {progress}%")

            video_id = response.get("id", "unknown")
            log.info(f"✅ YouTube 发布成功!")
            log.info(f"   🔗 https://youtu.be/{video_id}")
            return True

        except Exception as e:
            log.error(f"❌ YouTube 上传失败: {e}")
            return False
