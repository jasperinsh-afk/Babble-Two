# Flutter → 微信小程序 改造记录

> 本文记录 V1.0（Flutter + FastAPI/PostgreSQL）到 V2.0（微信原生小程序 + 微信云开发）的迁移映射。
> 上一轮「叭啦 → Flutter」的记录见 [`MIGRATION.md`](MIGRATION.md)。

---

## 一、改造决策

| 维度 | 决策 | 原因 |
|---|---|---|
| 客户端 | 微信原生小程序（WXML/WXSS/JS + 自定义 TabBar） | 无编译层，云开发集成最顺 |
| 后端 | 云函数重写 + 云开发云数据库（文档型） | 全量原生云开发，ORM 重做 |
| 登录 | **彻底移除** | 校园入口场景下注册转化是最大流失点 |
| UGC | **彻底移除**（评论/创建投票/社团发帖/入驻申请）；接龙保留 | 数据全部由数据库注入 |
| 身份 | 静默 openid（`wx.login` 无感换取） | 仅用于去重与归属，不算登录 |
| NFC | **砍掉硬件**，改为 `wx.scanCode` 扫小程序码 | `wx.getNFCAdapter` 仅 Android 可用 |
| 遗留 FastAPI | 保留为运营侧服务（crawler + export + admin-web） | 墨麟书院输入/输出层保留 |

---

## 二、目录变更

```
client/                → archive/flutter/        （Flutter 归档，构建产物已清理）
server/app/api/v1/*    → archive/fastapi/api_v1/ （11 个业务路由模块）
server/app/services/*  → archive/fastapi/services/（8 个业务服务）
server/app/models/*    → archive/fastapi/models/ （6 组业务模型）
server/scripts/seed_data.py → archive/fastapi/scripts/
（新增）miniprogram/   微信原生小程序
（新增）cloudfunctions/ 9 个云函数
（新增）scripts/seed/  云数据库种子
（新增）server/app/cloudbase_client.py  运营侧 → 云数据库桥接
```

> 项目无 Git 仓库，归档采用目录搬迁而非删除，便于逐字段比对。

---

## 三、页面映射（dart → 小程序）

| Flutter 页面 | 小程序页面 | 变化 |
|---|---|---|
| `features/home/home_page.dart` | `pages/index/index` | 保留 Banner/今日投票/热门/活动/社团，新增扫码入口 |
| `features/vote/vote_page.dart` | `pages/vote/list/list` | 标签筛选 + 分页 |
| `features/vote/vote_detail_page.dart` | `pages/vote/detail/detail` | 移除评论，结果图表改为自研 `result-chart`，接龙保留 |
| `features/club/club_page.dart` | `pages/club/list/list` | 新增搜索，移除入驻申请入口 |
| `features/club/club_detail_page.dart` | `pages/club/detail/detail` | 移除评论与发帖，仅官方内容流 |
| `features/calendar/calendar_page.dart` | `pages/calendar/index/index` | `table_calendar` → 自研 WXML 月视图 |
| `features/living/living_page.dart` | `pages/living/index/index` | 三 Tab 保留，移除回复 |
| `features/nfc/nfc_page.dart` | `pages/scan/index/index` | **NFC 碰一碰 → 扫码落地页** |
| `features/profile/profile_page.dart` | `pages/profile/index/index` | 「我的」→ 本地足迹（投票/勋章/打卡） |
| `features/auth/login_page.dart` | — | **删除** |
| `features/auth/register_page.dart` | — | **删除** |
| `app/shell.dart`（底部导航） | `custom-tab-bar/` | 自定义 TabBar（5 Tab） |

---

## 四、端点映射（FastAPI → 云函数 action）

| 原端点 | 云函数 action |
|---|---|
| `GET /home/feed` | `home.feed` |
| `GET /votes`、`GET /votes/{id}` | `vote.list`、`vote.detail` |
| `POST/PUT /votes/{id}/cast` | `vote.cast`（含改票） |
| `GET /votes/{id}/results` | `vote.results` |
| `POST/DELETE /votes/{id}/join` | `vote.joinChain` / `vote.leaveChain` |
| `GET /clubs`、`GET /clubs/{id}` | `club.list`、`club.detail` |
| `GET /clubs/{id}/posts` | `club.posts` |
| `POST/DELETE /clubs/{id}/join` | `club.join` / `club.leave` |
| `GET /events`、`GET /events/calendar` | `event.list`、`event.calendar` |
| `POST /events/{id}/join` | `event.join` |
| `GET /events/me/cas` | `event.myCas` |
| `GET /living/channels`、`/living/channels/{id}/posts` | `living.channels`、`living.channelPosts` |
| `GET /living/lost-found`、`/living/second-hand` | `living.lostFound`、`living.secondHand` |
| `GET /nfc/{card_id}`、`POST /nfc/tap` | `scan.cardByCode`、`scan.checkin` |
| `GET /badges`、`GET /users/me` | `me.overview` |
| `POST /admin/...` | `adminIngest.*` + `/admin/web/api/*` |

**已删除**：`/auth/*`、`/votes/{id}/comments`、`POST /votes`、`POST /clubs`、`POST /clubs/{id}/posts`、`/living/**/replies`、`/push/devices`、`/users/me/settings`。

---

## 五、数据映射（23 张表 → 云数据库集合）

| 集合 | 来源表 | 变化 |
|---|---|---|
| `polls` | `polls` + `poll_options` | 选项内嵌为 `options[]`，票数用 `inc` 原子自增 |
| `ballots` | `ballots` | 唯一索引 `_openid + pollId`，一人一票 |
| `chain_members` | `ballots`（接龙型） | 唯一索引 `_openid + pollId + optionId` |
| `clubs` | `clubs` + `club_members` | 成员用 `memberOpenids[]` 数组 + `memberCount` 计数 |
| `club_posts` | `posts` | 仅运营注入 |
| `events` | `events` + `event_registrations` | `registeredOpenids[]` / `waitlistOpenids[]` |
| `cas_records` | `cas_records` | 保留 |
| `dorm_channels` / `dorm_posts` | 同名表 | 无 `dorm_replies` |
| `lost_found` / `second_hand` | 同名表 | 保留 |
| `nfc_cards` | `nfc_cards` | 新增 `code` 字段承载小程序码 scene |
| `nfc_checkins` | `nfc_checkins` + `nfc_taps` | 合并，同点位只计一次 |
| `badges` / `user_badges` | 同名表 | 保留 |
| `banners` | `home` 聚合源拆分 | 独立集合 |

**不再迁移**：`users`（运营账号仍在本地 PostgreSQL）、`notifications`、`push_devices`、`comments`、`post_comments`、`dorm_replies`、`nfc_campaigns`、`sensitive_words`（运营侧自有库）。

---

## 六、OMEGA：NFC → 扫码

| V1.0（Flutter） | V2.0（小程序） |
|---|---|
| `nfc_manager` 读 NDEF URI `https://goqd.com/nfc/{card_id}` | `wx.scanCode` 扫海报小程序码 |
| 卡片 ID 正则 `^[A-Z]{2}-[A-Z]{2}-\d{2}-[A-Z0-9]+$` | 沿用同一规则，`scan.cardByCode` 支持 `_id` 或 `code` 两种查法 |
| 8 类点位（CT/LB/DM/BB/CR/CL/SP/GW） | 保留，规则说明放在扫码页 |
| 离线补报（`goqd_pending_nfc_taps`） | 去掉（无本地补报入口），改为联网即打卡 |
| NFC Writer 写卡端点 `/api/v1/nfc-write/{id}` | 删除 |

小程序码 scene 建议直接用卡编号（如 `QD-CT-01-A01`），冷启动走 `onLoad(options.scene)`，热启动走 `wx.scanCode` 的 `result`。

---

## 七、设计令牌映射（theme.dart → app.wxss）

> 产品已于 2026-10-18 品牌升级为「叭啦 Babble」（原七德通 GoQD），下表同步为 V2.0 品牌令牌（主紫 #8B5CF6 / 辅橙 #F97316）。

| Flutter | 小程序 CSS 变量（品牌 V2.0） |
|---|---|
| `GoQDColors.primary` | `--primary: #8B5CF6`（叭啦紫） |
| primary 渐变 | `--gradient-primary`（`#8B5CF6 → #F97316`，紫 → 星芒橙） |
| 背景 | `--bg-page: #FAF8FF` / `--bg-tint: #F3EDFD` |
| 卡片白 | `--bg-card: #FFFFFF` |
| 主文字 / 次文字 / 弱文字 | `--text-strong #1E1B2E` / `--text-normal #5C5775` / `--text-weak #9D96B8` |
| 成功 / 危险 / 警告 | `--success #22C55E` / `--danger #EF4444` / `--warning #F59E0B` |
| 圆角 | `--radius-s/m/l/pill` |
| 阴影 | `--shadow-s/m/l` |

---

## 八、运营侧改造

- `crawler/`（输入层）保留，新增 `job_push_candidates`：候选话题经 `cloudbase_client.upsert_draft` 写入云数据库（草稿态）
- `export_service.py`（输出层）改为读取云数据库 `polls`，导出**不含 `_openid`**
- `admin_web.py` 改为读写云数据库，本地库仅保留 `crawler_items` / `sensitive_words` / 运营账号
- 运营后台改用 `ADMIN_WEB_TOKEN` 口令登录（C 端无登录，后台独立保护）
- 投票生命周期（到点上线 / 到期关闭）由运营侧定时任务维护云数据库，服务端时间为准

---

## 九、旧缺陷规避（对照 MIGRATION.md）

| 旧「叭啦」缺陷 | 本次规避方式 |
|---|---|
| K 码明文硬编码 | 运营密钥只在云函数环境变量与服务端 env |
| 信任前端 `visitorKey` | 一律用 `cloud.getWXContext().OPENID` |
| 字段漂移 | 集合字段在本文与 `scripts/seed/README.md` 定稿，种子脚本统一补默认值 |
| 全表扫描 | 所有查询强制 `limit`，首页单次聚合并行查询 |
| 读全文档回写导致丢票 | 票数用 `db.command.inc` 原子自增 |

---

## 十、遗留项

- 投票结果图表使用自研 `result-chart`（CSS 动画），未引入 `ec-canvas`/ECharts，如需更复杂图表可替换
- 社团/活动的运营审核入口保留在 admin-web，云数据库侧用 `reviewStatus` / `status` 字段配合
- 活动签到（CAS 确认）需运营侧在活动结束后注入 `cas_records`
