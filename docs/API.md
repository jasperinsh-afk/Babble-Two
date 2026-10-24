# 叭啦 Babble · 云函数接口契约

小程序端所有数据读写均通过 `wx.cloud.callFunction`，统一入出参如下。

## 通用约定

**入参**

```js
wx.cloud.callFunction({
  name: '<函数名>',   // identity / home / vote / club / event / living / scan / me / adminIngest
  data: { action: '<动作>', payload: { ... } },
})
```

**出参**

```js
{ ok: true,  data: <任意>, message: 'ok' }
{ ok: false, data: null,   message: '错误原因', code: 'ERR_CODE' }
```

端上统一封装见 `miniprogram/utils/api.js`：

```js
const data = await call('vote', 'cast', { pollId, optionIds })
// 内部：loading 遮罩 + 失败 toast + 超时重试 1 次 + {ok,data,message} 解包
```

**身份**：云函数内 `cloud.getWXContext().OPENID` 取 openid，服务端可信，端上无法伪造。全站无登录态，openid 仅用于投票去重、接龙去重、打卡与勋章归属。

---

## identity

| action | payload | data | 说明 |
|---|---|---|---|
| （无） | `{}` | `{ openid }` | 静默换取 openid，不落用户表 |

## home

| action | payload | data |
|---|---|---|
| `feed` | `{}` | `{ banners[], todayPoll, hotPolls[], events[], clubs[] }` |

单次聚合 5 个集合（`Promise.all` 并行），各集合强制 limit：Banner ≤5、今日 ≤1、热投 ≤5、活动 ≤3、社团 ≤6。

## vote

| action | payload | data | 说明 |
|---|---|---|---|
| `list` | `{ tag, page }` | `{ list[], hasMore }` | tag：`all / news / campus / meme / group` |
| `detail` | `{ pollId }` | `{ _id, title, description, pollType, status, tag, startAt, endAt, options[], totalVotes, participantCount, maxParticipants, maxChoices, hasVoted, myChoice[], joined, isFull }` | 附带当前用户投票状态 |
| `results` | `{ pollId }` | `{ pollId, total, options[{ optionId, label, count }] }` | 仅聚合计数，无个人信息 |
| `cast` | `{ pollId, optionIds[] }` | `{ voted, optionIds[] }` | 已投则先撤回旧票再记新票（需 `allowChange`） |
| `joinChain` | `{ pollId, optionId }` | `{ joined, optionId }` | 接龙，仅 `groupbuy` 类型 |
| `leaveChain` | `{ pollId }` | `{ joined: false }` | 取消接龙 |

投票类型与可选数量约束（服务端校验，端上不可绕过）：

| pollType | 含义 | 可选数量 |
|---|---|---|
| `single` | 单选 | 1 |
| `multi` | 多选 | 1 ~ `maxChoices` |
| `pk` | PK 二选一 | 1 |
| `ranking` | 排序（按点选顺序） | 1 ~ `maxChoices` |
| `groupbuy` | 接龙组团 | 1 |

票数用 `db.command.inc` 原子自增（`totalVotes`、`options.N.count`、`participantCount`），不读全文档回写。

## club

| action | payload | data |
|---|---|---|
| `list` | `{ category, keyword, page }` | `{ list[], hasMore }` |
| `rank` | `{}` | `{ list[] }` 热度前 10 |
| `detail` | `{ clubId }` | `{ _id, name, category, description, coverUrl, isVerified, memberCount, heatScore, joined }` |
| `posts` | `{ clubId, page }` | `{ list[] }` 仅运营注入内容，无评论/无发帖入口 |
| `join` | `{ clubId }` | `{ joined: true }` `memberCount` 原子自增 |
| `leave` | `{ clubId }` | `{ joined: false }` |

category：`all / academic / sports / art / charity / interest`

## event

| action | payload | data | 说明 |
|---|---|---|---|
| `list` | `{ page }` | `{ list[], hasMore }` | 仅 `active / full` |
| `calendar` | `{ year, month }` | `{ events[] }` | 返回整月活动，端上按日期分组 |
| `detail` | `{ eventId }` | `{ _id, title, description, coverUrl, startAt, endAt, location, maxParticipants, participantCount, joined, waitlisted }` |
| `join` | `{ eventId }` | `{ joined, waitlisted, already }` | 满员自动进候补 |
| `myCas` | `{}` | `{ records[], hours }` | CAS 履历 |

## living

| action | payload | data |
|---|---|---|
| `channels` | `{}` | `{ list[] }` 宿舍频道（scope：ALL / FLOOR / ROOM） |
| `channelPosts` | `{ channelId, page }` | `{ list[] }` |
| `lostFound` | `{ kind, page }` | `{ list[] }` kind：`all / lost / found` |
| `secondHand` | `{ page }` | `{ list[] }` |

## scan（OMEGA 扫码）

| action | payload | data | 说明 |
|---|---|---|---|
| `cardByCode` | `{ key }` | `{ cardId, locationDesc, locationType, targetType, targetId, checked, tapCount, uniqueCards, rules[] }` | `key` 可为卡编号或小程序码 scene |
| `checkin` | `{ key }` | `{ checked, firstTime, cardId, uniqueCards, newBadges[], target{type,id} }` | 同点位只计一次，重复打卡累加 `tapCount` |

点位类型：`canteen 食堂 / library 图书馆 / dormitory 宿舍 / bulletin 公告栏 / classroom 教室 / clubroom 社团 / sports 体育 / gateway 校门`

## me

| action | payload | data |
|---|---|---|
| `overview` | `{}` | `{ stats{ voteCount, checkinCount, badgeCount }, badges[], recentVotes[], recentCheckins[] }` |

## adminIngest（运营侧写入网关）

不面向小程序端，仅由 FastAPI 运营侧服务调用（HTTP API `invokecloudfunction`）。

| action | payload | 说明 |
|---|---|---|
| `upsertDraft` | `{ token, draft }` | 爬虫草稿写入（含指纹去重），`reviewStatus: pending` |
| `publishPoll` | `{ token, poll }` | 运营终审通过后发布 |
| `write` | `{ token, collection, doc }` | 通用写入（受白名单集合限制） |
| `ping` | `{}` | 连通性自检 |

`token` 必须等于云函数环境变量 `INGEST_TOKEN`，不一致直接拒绝。密钥只存在于服务端。

---

## 已移除的接口（不再存在）

| 原端点 | 处理 |
|---|---|
| `POST /auth/send-code` `/auth/register` `/auth/login` `/auth/refresh` | 登录体系整体删除 |
| `GET/POST /votes/{id}/comments` | 评论（UGC）删除 |
| `POST /votes`（创建投票） | 用户创建投票删除 |
| `POST /clubs`（入驻申请）、`POST /clubs/{id}/posts` | UGC 删除 |
| `POST /living/.../replies` | 宿舍回复删除 |
| `POST /nfc/tap`（NFC 硬件上报） | 改为 `scan.checkin` |
| `GET /users/me` 及设置项 | 「我的」改为本地足迹 `me.overview` |
| `POST /push/devices` | 推送设备注册删除 |

## 错误码

| code | 含义 |
|---|---|
| `PARAM_MISSING` | 缺少必填参数 |
| `NOT_FOUND` / `CARD_NOT_FOUND` | 资源不存在 |
| `CARD_INACTIVE` | 点位已停用 |
| `POLL_CLOSED` | 投票已截止（服务端时间判定，端上传值不可信） |
| `ALREADY_VOTED` | 已投票且不允许改票 |
| `FULL` | 接龙/活动已满员 |
| `NO_AUTH` | adminIngest 令牌校验失败 |
