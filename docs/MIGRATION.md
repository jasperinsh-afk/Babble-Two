# 从「叭啦」小程序到「七德通 GoQD」—— 改造记录

> 本文档说明旧代码为什么要废弃、哪些工程经验被保留、以及旧→新的模块映射关系。

---

## 一、为什么废弃而不是改造

旧项目 `bala-miniapp`（叭啦 / 匿语 / 魔丸计划）与 5 份文档定义的「七德通 GoQD」是**两套完全不同的产品**：

| 维度 | 叭啦（旧） | 七德通 GoQD（新） |
|---|---|---|
| 平台 | 微信小程序原生（WXML/WXSS/JS） | Flutter（iOS + Android + Web） |
| 后端 | 微信云开发云函数 + Flask/SQLite | FastAPI + PostgreSQL + Redis |
| 身份 | 微信 OPENID 免登 | 学号 + 学校邮箱验证码 + JWT |
| 品牌 | 主「叭啦」/ 母「匿语」/ 活动「魔丸计划 S1」 | 统一「七德通 GoQD」 |
| 模块 | 投票 / 小纸条 / 叭TA / 积分会员 / 热榜 | 投票 / 社团 / 日历 / 住宿 / OMEGA / 墨麟书院 |
| 内容源 | 人工 | 自动爬虫 + LLM（墨麟书院输入层） |
| 引流 | 无 | NFC 海报碰一碰（OMEGA） |
| 数据价值 | 无 | 脱敏导出 → 青少年社会学报告（输出层） |

结论：除「网络层容错思路」与「部署经验」外无复用价值，按决策全量废弃。

---

## 二、旧代码的已知缺陷（改造时必须消除）

改造前勘察发现的主要问题，新架构已逐一规避：

### P0 — 安全

1. **K 码明文硬编码**：`0923145X` 同时写在前端 `campaign.js`、云端 `handlers/campaign.js`、`handlers/member.js` 三处。小程序包可被反编译，任何人都能解锁无限投票。
   → 新架构：无任何客户端可读取的兑换码逻辑；所有权限判定在服务端，JWT + RBAC。

2. **身份可伪造**：`handlers/auth.js` 信任前端传入的 `event.visitorKey`。
   → 新架构：服务端签发 JWT，客户端无法伪造。

### P1 — 数据一致性

3. **字段漂移**：代码写 `persona_tag`，`backend/data/bala.db` 实际列名是 `topic_tag`。
4. **幽灵字段**：`handlers/member.js` 按 `season_code` 查询，但库里没有这一列。
5. **类型不匹配**：`campaign.js` 读取 `p.options`（实为 `options_json` 字符串），导致统计恒为 0。
   → 新架构：SQLAlchemy ORM 单一数据源 + Alembic 迁移，字段名由模型定义，杜绝漂移。

### P2 — 性能

6. **全表扫描**：`member.js:getSeasonPollStats` 每次拉 1000 条 polls 在内存里过滤。
7. **日志噪音**：6 处 `console.log` 在循环内逐条打印。
   → 新架构：SQL 聚合 + 索引（技术架构文档 §4.3），Redis 计数缓存。

### P3 — 工程债

8. **孤儿代码**：7 个页面中 `campaign`、`notification` 无任何入口；45 条云函数接口中 30+ 条无调用方。
9. **文档脱节**：旧 README 描述的 forum / werewolf / me / message-board 全部不存在；两份 plan 规划的 13 个页面只落地 1 个。
10. **图表缺失**：投票结果只有 CSS `.bar-fill` 宽度百分比，无真正的图表。
    → 新架构：每个模块 API + 页面一一对应，30 项冒烟测试兜底；Flutter 端用 `fl_chart` 画饼图。

---

## 三、保留下来的工程经验

以下设计思路被确认有价值，已在新架构中复刻：

| 旧实现 | 新位置 |
|---|---|
| 请求失败指数退避重试 | `app/crawler/sources/base.py::safe_fetch`（3 次重试，delay ×2） |
| 并发去重锁 | `ballots` 表 `UNIQUE(poll_id, user_id)` + Redis 计数 |
| 内容安全检测 fail-open（检测服务挂了不能阻塞发布） | `app/services/llm_service.py::safe_llm_call` 降级返回 fallback |
| 投票结果本地缓存 | `app/core/redis.py`（Redis 优先，缺失时降级为进程内 LRU） |
| README 中的部署踩坑记录 | 本文件 + `README.md` 快速开始章节 |
| 网络中断本地暂存 | `client/lib/core/storage/local_cache.dart`（投票 / NFC 打卡补报） |

---

## 四、旧 → 新模块映射

| 旧模块 | 处置 | 新模块 |
|---|---|---|
| `pages/home` | 重写 | `client/lib/features/home/home_page.dart` + `api/v1/home.py` |
| `pages/polls`、`pages/poll-detail` | 重写 | `features/vote/` + `api/v1/votes.py` |
| `pages/season`（赛季/积分） | **删除** | — |
| `pages/campaign`（魔丸计划 K 码） | **删除** | — |
| `pages/launch` | **删除** | — |
| `pages/notification` | 重写 | `api/v1/push.py` + `Notification` |
| `cloudfunctions/bala-api` 45 条路由 | **删除** | `api/v1/*` 11 个模块 |
| `backend/` Flask + SQLite | **删除** | `server/app/` FastAPI |
| `backend/data/bala.db`（144KB 真实数据） | **不迁移** | `scripts/seed_data.py` 重建演示数据 |
| 小纸条 / 叭TA / 积分会员 / 热榜 | **删除** | — |
| 无 | 新增 | 社团广场 `features/club/` |
| 无 | 新增 | 活动日历 + CAS `features/calendar/` |
| 无 | 新增 | 住宿生活 `features/living/` |
| 无 | 新增 | OMEGA NFC `features/nfc/` |
| 无 | 新增 | 墨麟书院爬虫 + 4 个 Prompt `app/crawler/`、`app/prompts/` |
| 无 | 新增 | 勋章系统 `app/services/badge_service.py` |
| 无 | 新增 | 运营后台 `server/admin-web/`（Jinja2） |

---

## 五、新架构的验证清单

- [x] `uvicorn app.main:app` 启动，101 条路由
- [x] `python scripts/seed_data.py --reset` 灌入演示数据
- [x] 30 项冒烟测试通过（注册登录 / 投票幂等 / 改票一次 / 审核 / NFC / 导出脱敏）
- [x] `flutter analyze` 零 error
- [x] `flutter pub get` 成功

---

## 六、注意事项

- **时间统一**：内部时间一律为**朴素 UTC**（`app/core/timeutil.py`）。SQLite 的 `DateTime` 往返会丢失时区，若混用 aware/naive 会在比较时抛异常。
- **限流**：开发与测试环境请保持 `RATE_LIMIT_ENABLED=false`，否则批量注册会被 429 拦截。
- **爬虫**：默认 `CRAWLER_ENABLED=false`。开启前需配置通义千问 Key，且**必须由运营人工终审**，禁止全自动无人审核上线。
- **Deep Link**：Android `assetlinks.json` 与 iOS AASA 中的 TEAM_ID / SHA256 指纹需在正式发包前替换。
