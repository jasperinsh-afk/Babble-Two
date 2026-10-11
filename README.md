# 七德通 GoQD

> 面向七宝德怀特高中在校生的「校园生活入口型 App」
> 项目代号 Project Y · V1.0

---

## 一、这是什么

七德通把**投票互动、社团信息、活动日历、住宿生活**聚合在一部手机里，目标是成为校园数字生活的第一入口。

本目录由原「叭啦」微信小程序**彻底改造**而来，旧业务（叭啦/匿语/魔丸计划/积分会员/小纸条/叭TA/热榜）全部废弃，详见 [`docs/MIGRATION.md`](docs/MIGRATION.md)。

---

## 二、目录结构

```
bala-miniapp/
├── server/          FastAPI 后端 + 爬虫 + 运营后台
│   └── app/
│       ├── core/        配置 / 安全 / 数据库 / Redis / 限流 / 异常
│       ├── models/      23 张表 SQLAlchemy 2.0 ORM
│       ├── schemas/     Pydantic v2 请求响应模型
│       ├── api/v1/      11 个路由模块（技术架构文档 §3.2）
│       ├── services/    业务逻辑层
│       ├── crawler/     墨麟书院·输入层（5 源爬虫 + 三层过滤）
│       ├── prompts/     4 个 LLM Prompt（Prompt 工程文档）
│       └── tasks/       Celery 定时任务
├── client/          Flutter App（Android / iOS / Web）
│   └── lib/
│       ├── app/         MaterialApp / 路由 / 主题
│       ├── core/        Dio 网络层 / 安全存储 / Deep Link
│       └── features/    auth home vote club calendar living nfc profile admin
├── admin-web/       运营后台（FastAPI + Jinja2 服务端渲染）
└── docs/            迁移记录与接口文档
```

---

## 三、技术栈

| 层次 | 选型 |
|---|---|
| 客户端 | Flutter 3.x（Android / iOS / Web） |
| 客户端 NFC | `nfc_manager` |
| Deep Link | `app_links` |
| 状态管理 | Riverpod |
| 网络 | Dio（401 无感刷新 Token） |
| 后端 | FastAPI + SQLAlchemy 2.0（异步） |
| 数据库 | PostgreSQL 15+（开发期可用 SQLite 兜底） |
| 缓存 | Redis 7+（缺失时自动降级为进程内 LRU） |
| 定时/队列 | APScheduler + Celery（可降级为线程调度） |
| 爬虫 | Playwright + httpx + BeautifulSoup |
| LLM | 通义千问 qwen-plus / qwen-max |
| 推送 | 极光推送（无 Key 时降级为仅站内信） |

---

## 四、快速开始

### 后端

```bash
cd server

python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

cp .env.example .env            # 按需修改

# 初始化数据库并灌入演示数据
python scripts/init_db.py
python scripts/seed_data.py

# 启动
uvicorn app.main:app --reload --port 8000
```

启动后访问：

- 接口文档：http://localhost:8000/docs
- 运营后台：http://localhost:8000/admin
- NFC 中间页示例：http://localhost:8000/nfc/QD-CT-01-A01

### 客户端

```bash
cd client
flutter pub get
flutter run
```

---

## 五、功能模块

| 模块 | 说明 | PRD 编号 |
|---|---|---|
| 首页（发现） | Banner + 今日头条 + 热门投票 + 推荐活动 + 社团精选 | H-001~008 |
| 投票中心 | 单选/多选/PK/排序、改票、立场短评、接龙组团、脱敏分组统计 | V-001~204 |
| 社团广场 | 入驻审核、认证徽章、图文发布、热度榜、关注流 | C-001~204 |
| 活动日历 | 月/周/日视图、报名候补、CAS 履历沉淀 | E-001~203 |
| 住宿生活 | 宿舍/楼层/全校频道、失物招领、二手交换、生活投票 | L-001~103 |
| OMEGA | NFC 海报碰一碰跳转、卡片管理、打卡解锁勋章 | N-001~203 |
| 墨麟书院·输入层 | 5 源爬虫 + 敏感词 + LLM 三层过滤 + 草稿生成 | ML-I-001~007 |
| 墨麟书院·输出层 | 投票数据永久沉淀 + 脱敏 CSV/Excel 导出 | ML-O-001~005 |
| 个人中心 | 学号+邮箱注册、我的投票/社团/活动、勋章墙、注销 | U-001~009 |

---

## 六、五个一级 Tab

```
首页(发现) │ 投票 │ 社团 │ 日历 │ 我的
```

---

## 七、合规红线

- 政治、宗教、性别对立话题**一票否决**，人工复核不可省略
- 爬虫抓取的是「话题」而非「原文」，投票题干由 AI 原创
- 每日必须有值班运营确认发布，**禁止全自动无人审核上线**
- 所有 UGC 必须过敏感词 + 人工复核双层审核
- 数据导出前必须脱敏，移除一切可关联到个人的信息

---

## 八、文档索引

| 文档 | 位置 |
|---|---|
| 产品策划方案 | `../七德通-产品策划方案.md` |
| PRD 产品需求文档 | `../七德通-PRD产品需求文档.md` |
| 技术架构文档 | `../七德通-技术架构文档.md` |
| OMEGA 技术实现文档 | `../七德通-OMEGA技术实现文档.md` |
| Prompt 工程文档 | `../七德通-Prompt工程文档.md` |
| 旧代码迁移记录 | `docs/MIGRATION.md` |

---

*七德通 GoQD · Project Y*
