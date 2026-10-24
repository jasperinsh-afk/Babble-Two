# 云开发数据库设计（MongoDB 文档型）

> 由原 PostgreSQL 23 张表迁移而来。本文件是**云函数与种子脚本的唯一数据契约**，改动需同步两侧。
> 设计原则：读多写少的子表内嵌、高写入流水独立、所有计数冗余到父文档用 `$inc` 原子更新。

---

## 零、与关系模型的差异（迁移必读）

| 关系模型 | 云开发做法 |
|---|---|
| `user_id` 外键 | 一律替换为 `_openid`（`wx.login` 静默换取，云函数内 `cloud.getWXContext().OPENID`，端上不可伪造） |
| 整型自增主键 `id` | 改用字符串业务 `_id`（如 `p001` / `c001` / `QD-CT-01-A01`），便于种子注入与深链 |
| Redis 计数器 | 冗余到父文档字段，`db.command.inc(n)` 原子更新 |
| `UNIQUE(poll_id, user_id)` | 集合唯一索引 `{_openid:1, pollId:1}` |
| 软删除 `is_deleted` | 云函数查询统一带 `isDeleted: false` 条件 |
| 敏感词 / 爬虫原始条目 | **不进云数据库**，留在运营侧 FastAPI 自己的库 |

---

## 一、集合总览

| # | 集合 | 来源表 | 读写方 |
|---|---|---|---|
| 1 | `polls` | `polls` + `poll_options`（内嵌） | 端上读 / 运营侧写 |
| 2 | `ballots` | `ballots` | 端上读写 |
| 3 | `clubs` | `clubs` + `club_members`（内嵌 openid 数组） | 端上读 + 加入退出 |
| 4 | `club_posts` | `posts` | 端上读 / 运营侧写 |
| 5 | `events` | `events` + `event_registrations`（内嵌 openid 数组） | 端上读 + 报名 |
| 6 | `cas_records` | `cas_records` | 端上读 |
| 7 | `dorm_channels` | 同名 | 端上读 |
| 8 | `dorm_posts` | `dorm_posts` | 端上读 |
| 9 | `lost_found` | 同名 | 端上读 |
| 10 | `second_hand` | 同名 | 端上读 |
| 11 | `nfc_cards` | `nfc_cards` | 端上读 / 运营侧写 |
| 12 | `nfc_checkins` | `nfc_checkins` + `nfc_taps`（合并） | 端上读写 |
| 13 | `badges` | `badges` | 端上读 |
| 14 | `user_badges` | `user_badges` | 云函数写 / 端上读 |
| 15 | `banners` | 原 `home/feed` 聚合源拆分 | 端上读 / 运营侧写 |
| 16 | `poll_drafts` | 爬虫草稿（新） | 运营侧写 / 后台读 |

**不迁移（已删除）**：`users`、`notifications`、`push_devices`、`comments`、`post_comments`、`dorm_replies`、`nfc_campaigns`、`sensitive_words`、`crawler_items`。

---

## 二、集合字段定义

### 1. `polls` — 投票

| 字段 | 类型 | 说明 |
|---|---|---|
| `_id` | string | 业务 ID，如 `p001` |
| `title` | string | 题干 |
| `description` | string | 引导语 |
| `pollType` | string | `single` / `multi` / `pk` / `ranking` / `groupbuy` |
| `status` | string | `draft` / `scheduled` / `active` / `closed` / `archived` / `withdrawn` |
| `category` | string | `current_affairs` / `campus` / `culture` / `values` / `lifestyle` |
| `tag` | string | `news` / `campus` / `meme` / `group` |
| `topicTags` | string[] | 话题串，如 `["校园生活","热梗"]` |
| `startAt` / `endAt` | date | 起止时间 |
| `allowChange` | boolean | 是否允许改票一次 |
| `anonymous` | boolean | 结果脱敏 |
| `maxChoices` | number\|null | 多选最多可选数 |
| `maxParticipants` | number\|null | 接龙人数上限 |
| `coverUrl` | string | 封面 |
| `sourceType` | string | `crawler` / `manual` |
| `reviewStatus` | string | `pending` / `approved` / `rejected` / `needs_manual` |
| `options` | object[] | **内嵌** `{optionId, label, sortOrder, count}` |
| `totalVotes` | number | 冗余总票数 |
| `participantCount` | number | 接龙已报名数 |
| `isDeleted` | boolean | 软删除 |
| `createdAt` / `updatedAt` | date | |

**索引**：`status`（普通）、`tag + status`（联合）、`endAt`（普通）、`createdAt`（降序）

### 2. `ballots` — 投票记录（一人一票）

| 字段 | 类型 | 说明 |
|---|---|---|
| `_openid` | string | 投票人 |
| `pollId` | string | 投票 |
| `optionId` | string\|null | 单选/PK/接龙 |
| `optionIds` | string[]\|null | 多选/排序 |
| `isChanged` | boolean | 是否已用过改票机会 |
| `createdAt` / `updatedAt` | date | |

**索引**：`{_openid:1, pollId:1}` **唯一**（防重复投票）、`{pollId:1}` 普通

### 3. `clubs` — 社团

| 字段 | 类型 | 说明 |
|---|---|---|
| `_id` | string | 如 `c001` |
| `name` / `description` | string | |
| `logoUrl` / `coverUrl` | string | |
| `category` | string | `academic` / `sports` / `art` / `charity` / `interest` / `other` |
| `isVerified` | boolean | 官方认证徽章 |
| `memberCount` / `followerCount` / `heatScore` | number | 冗余计数 |
| `memberOpenids` | string[] | **内嵌**成员 openid（替代 `club_members`） |
| `isDeleted` | boolean | |
| `createdAt` / `updatedAt` | date | |

**索引**：`category`、`heatScore`（降序）

### 4. `club_posts` — 社团动态（仅运营注入）

| 字段 | 类型 | 说明 |
|---|---|---|
| `_id` / `clubId` | string | |
| `title` / `content` | string | |
| `images` | string[] | |
| `isPinned` / `likeCount` | boolean / number | |
| `publishedAt` | date | |

**索引**：`{clubId:1, publishedAt:-1}`、`isPinned`

### 5. `events` — 活动

| 字段 | 类型 | 说明 |
|---|---|---|
| `_id` / `title` / `description` / `coverUrl` / `location` | string | |
| `organizerType` | string | `club` / `class` / `school` |
| `organizerId` | string\|null | 主办社团 |
| `startAt` / `endAt` / `signupDeadline` | date | |
| `maxParticipants` | number\|null | |
| `status` | string | `active` / `full` / `closed` / `cancelled` |
| `casType` | string\|null | `C` / `A` / `S` |
| `participantCount` | number | 冗余 |
| `registeredOpenids` | string[] | **内嵌**报名人 |
| `waitlistOpenids` | string[] | **内嵌**候补 |
| `isDeleted` / `createdAt` / `updatedAt` | | |

**索引**：`startAt`、`status`、`organizerType`

### 6. `cas_records` — CAS 履历

| 字段 | 类型 | 说明 |
|---|---|---|
| `_openid` / `title` | string | |
| `eventId` | string\|null | |
| `casType` | string | `C` / `A` / `S` |
| `role` | string | `participant` / `leader` / `organizer` |
| `happenedAt` / `createdAt` | date | |

**索引**：`{_openid:1, happenedAt:-1}`

### 7. `dorm_channels` — 宿舍频道

`{_id, name, scope: room|floor|all, building, floor, room, isActive, createdAt}`

### 8. `dorm_posts` — 宿舍帖子（无回复）

`{_id, channelId, content, images[], likeCount, reviewStatus, isDeleted, createdAt}`
**索引**：`{channelId:1, createdAt:-1}`

### 9. `lost_found` — 失物招领

`{_id, kind: lost|found, title, description, location, contact, images[], isResolved, isDeleted, createdAt}`
**索引**：`{kind:1, createdAt:-1}`

### 10. `second_hand` — 二手交换

`{_id, title, description, price: number|null（单位：分）, images[], contact, isSold, isDeleted, createdAt}`
**索引**：`{isSold:1, createdAt:-1}`

### 11. `nfc_cards` — OMEGA 点位卡（扫码用）

| 字段 | 类型 | 说明 |
|---|---|---|
| `_id` | string | 即 `cardId`，如 `QD-CT-01-A01` |
| `cardId` | string | 业务编码，**唯一** |
| `code` | string | 小程序码 scene 值，**唯一** |
| `locationDesc` | string | 点位文字描述 |
| `locationType` | string | `canteen` / `library` / `dormitory` / `bulletin` / `classroom` / `clubroom` / `sports` / `gateway` |
| `targetType` | string | `vote` / `club` / `event` / `download` |
| `targetId` | string\|null | 目标业务 ID |
| `isActive` / `posterBatch` / `deployedAt` / `createdAt` | | |

> 编码规则：`{学校}-{区域}-{楼层}-{序号}`，格式校验 `^[A-Z]{2}-[A-Z]{2}-\d{2}-[A-Z0-9]+$`

**索引**：`cardId` 唯一、`code` 唯一、`isActive`

### 12. `nfc_checkins` — 扫码打卡

| 字段 | 类型 | 说明 |
|---|---|---|
| `_openid` / `cardId` | string | |
| `firstTapAt` | date | 首次打卡 |
| `tapCount` | number | 累计次数 |
| `lastTapAt` | date | 最近一次 |

**索引**：`{_openid:1, cardId:1}` **唯一**（同一卡片不重复计数）

### 13. `badges` — 勋章定义

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | **唯一** |
| `name` / `description` / `iconUrl` | string | |
| `rarity` | string | `normal` / `rare` / `legendary` |
| `rule` | object | `{type, count}` 解锁规则 |

**保留勋章**（原 9 枚中剔除 3 枚）：

| code | 名称 | 稀有度 | 判定 |
|---|---|---|---|
| `first_vote` | 首投 | normal | 投票数 ≥ 1 |
| `ten_votes` | 十连投 | rare | 投票数 ≥ 10 |
| `club_pioneer` | 社团先锋 | normal | 加入社团数 ≥ 3 |
| `event_master` | 活动达人 | rare | 报名活动数 ≥ 10 |
| `scan_explorer` | 扫码探索者 | rare | 打卡不同点位 ≥ 5（原 `nfc_explorer`） |
| `perfect_attendance` | 全勤 | legendary | 连续投票天数 ≥ 30 |

**剔除**：`first_step`（依赖注册）、`opinion_leader`（依赖 comments 表）、`founder`（依赖 users 自增 id）。

### 14. `user_badges` — 已获勋章

`{_openid, badgeCode, earnedAt}` — **索引**：`{_openid:1, badgeCode:1}` **唯一**（幂等发放）

### 15. `banners` — 首页轮播

`{_id, title, imageUrl, targetRoute, sort, isActive, createdAt}` — **索引**：`{isActive:1, sort:1}`

### 16. `poll_drafts` — 墨麟书院草稿（运营侧写入）

| 字段 | 类型 | 说明 |
|---|---|---|
| `_id` / `title` / `description` | string | LLM 生成的投票草稿 |
| `options` | object[] | `{optionId, label, sortOrder}` |
| `category` / `tag` / `pollType` | string | |
| `source` | string | `weibo` / `zhihu` / `bilibili` / `baidu` / `cctv` |
| `sourceUrl` / `summary` / `heatScore` | | 原始素材 |
| `riskLevel` | string | `none` / `low` / `medium` / `high` |
| `status` | string | `pending` / `approved`（转 `polls`） / `rejected` |
| `createdAt` | date | |

**索引**：`{status:1, createdAt:-1}`

---

## 三、关键约束复刻

| 原约束 | 云开发实现 |
|---|---|
| `UNIQUE(poll_id, user_id)` 一人一票 | `ballots` 唯一索引 `{_openid, pollId}`，云函数内先查判重再写（双重保险） |
| `UNIQUE(user_id, card_id)` 打卡去重 | `nfc_checkins` 唯一索引 `{_openid, cardId}` |
| 接龙人数上限 `max_participants` | `polls.participantCount` 用 `db.command.inc(1)`，云函数内与 `maxParticipants` 比对 |
| 活动报名容量 | `events.registeredOpenids` 数组 `push`，超员转 `waitlistOpenids` |
| 改票一次 `allow_change` | `ballots.isChanged` 标记，二次修改直接拒绝 |
| 时间校验 | 截止/报名判定一律用**云函数服务端时间**，端上传值不可信 |

---

## 四、权限建议（云开发控制台集合权限）

| 集合 | 建议权限 | 理由 |
|---|---|---|
| `polls` `clubs` `club_posts` `events` `dorm_*` `lost_found` `second_hand` `nfc_cards` `badges` `banners` | **所有用户可读，仅管理端可写** | 端上只读，写操作走云函数 |
| `ballots` `nfc_checkins` `user_badges` `cas_records` | **仅创建者可读写** | 含 `_openid` 隐私数据 |
| `poll_drafts` | **所有用户不可读写**（仅云函数） | 运营草稿，含未审核内容 |

> 云函数在服务端运行时不受此权限限制，可自由读写全部集合。
