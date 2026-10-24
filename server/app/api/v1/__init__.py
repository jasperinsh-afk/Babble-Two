"""API v1 路由汇总（运营侧）。

小程序端业务 API 已全部迁移至微信云开发云函数，本服务仅保留
墨麟书院输出层（脱敏导出）。输入层（爬虫）由定时任务驱动，经
adminIngest 云函数写入云数据库，不对外暴露 HTTP 端点。
"""
from fastapi import APIRouter

from app.api.v1 import export, web

router = APIRouter()

router.include_router(export.router, tags=["墨麟书院·导出"])
router.include_router(web.router)

__all__ = ["router"]
