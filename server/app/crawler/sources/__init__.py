from app.crawler.sources.base import BaseSource, RawTopic  # noqa: F401
from app.crawler.sources.weibo import WeiboSource  # noqa: F401
from app.crawler.sources.zhihu import ZhihuSource  # noqa: F401
from app.crawler.sources.bilibili import BilibiliSource  # noqa: F401
from app.crawler.sources.baidu import BaiduSource  # noqa: F401
from app.crawler.sources.cctv import CctvSource  # noqa: F401

SOURCE_REGISTRY = {
    "weibo": WeiboSource,
    "zhihu": ZhihuSource,
    "bilibili": BilibiliSource,
    "baidu": BaiduSource,
    "cctv": CctvSource,
}


def build_sources(names) -> list:
    return [SOURCE_REGISTRY[n]() for n in names if n in SOURCE_REGISTRY]
