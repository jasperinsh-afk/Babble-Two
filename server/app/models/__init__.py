"""ORM 模型汇总（导入本包即注册全部表）。

瘦身后仅保留：
- common.py：枚举与基类
- crawler.py：crawler_items / sensitive_words（墨麟书院输入层）
- user.py：运营后台管理员账号（仅 operators，C 端已无登录）

其余业务表（polls / clubs / events / living / nfc / badges）数据已迁至
微信云开发数据库，原模型归档于 archive/fastapi/models/。
"""
from app.models.common import Base  # noqa: F401
from app.models.admin_account import AdminAccount  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.crawler import (  # noqa: F401
    DEFAULT_SENSITIVE_WORDS,
    CrawlerItem,
    SensitiveWord,
)

__all__ = [
    "Base",
    "AdminAccount",
    "User",
    "CrawlerItem",
    "SensitiveWord",
    "DEFAULT_SENSITIVE_WORDS",
]
