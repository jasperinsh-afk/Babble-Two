# 七德通 GoQD · 接口索引

在线文档：启动后端后访问 http://localhost:8000/docs（OpenAPI 自动生成）

统一响应格式：

```json
{"code": 0, "message": "success", "data": {...}, "timestamp": 1791673631}
```

错误码分段：`1xxx` 通用 / `2xxx` 认证 / `3xxx` 投票 / `4xxx` 社团 / `5xxx` 活动 /
`6xxx` 住宿 / `7xxx` NFC / `8xxx` 爬虫审核导出

---

## 认证 `/auth`

| 方法 | 路径 | 说明 | PRD |
|---|---|---|---|
| POST | `/auth/send-code` | 发送邮箱验证码（开发期返回 dev_code） | U-001 |
| POST | `/auth/register` | 学号 + 学校邮箱注册 | U-001 |
| POST | `/auth/login` | 学号 + 密码登录 | U-002 |
| POST | `/auth/refresh` | 刷新 Token（access 15min / refresh 30d） | — |
| POST | `/auth/logout` | 登出，Token 进黑名单 | — |

## 个人中心 `/users`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/PUT | `/users/me` | 个人信息 / 更新资料 |
| PUT | `/users/me/push` | 推送偏好 |
| GET | `/users/me/votes` | 我的投票 |
| GET | `/users/me/clubs` | 我的社团 |
| GET | `/users/me/events` | 我的活动 |
| GET | `/users/me/cas` | CAS 履历（E-201） |
| GET | `/users/me/notifications` | 站内消息 |
| DELETE | `/users/me` | 注销账号（清除个人数据，保留匿名统计）U-009 |

## 首页 `/home`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/home/feed` | Banner + 今日头条 + 热门投票 + 推荐活动 + 社团精选 |

## 投票中心 `/votes`

| 方法 | 路径 | 说明 | PRD |
|---|---|---|---|
| GET | `/votes` | 列表（tag / status / 分页） | V-201 |
| GET | `/votes/today` | 今日头条 | H-002 |
| GET | `/votes/{id}` | 详情 | V-001 |
| POST | `/votes/{id}/cast` | 投票（幂等） | V-001 |
| PUT | `/votes/{id}/cast` | 改票（限一次） | V-003 |
| GET | `/votes/{id}/results` | 结果 + 年级/住宿脱敏分组 | V-002 / V-006 |
| GET/POST | `/votes/{id}/comments` | 立场短评（≤200 字，投票后可写） | V-005 |
| POST/DELETE | `/votes/{id}/join` | 接龙报名 / 取消 | V-101 |

## 社团 `/clubs`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/clubs` | 列表（分类 / 搜索 / 热度排序） |
| GET | `/clubs/rank` | 热度榜 C-202 |
| POST | `/clubs` | 入驻申请 C-001 |
| GET | `/clubs/{id}` | 详情 |
| POST/DELETE | `/clubs/{id}/join` | 加入 / 退出 |
| GET | `/clubs/{id}/posts` | 内容流 |
| POST | `/clubs/{id}/posts` | 发布（管理员，双层审核） |
| POST | `/clubs/posts/{id}/like` | 点赞 |

## 活动 `/events`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/events` | 列表 |
| GET | `/events/calendar?year=&month=` | 日历（月视图）E-001 |
| POST | `/events` | 发布（社团管理员 / 运营） |
| POST/DELETE | `/events/{id}/join` | 报名（含候补）/ 取消 |
| GET | `/events/me/cas` | CAS 履历 |

## 住宿生活 `/living`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/living/channels` | 频道列表（按可见性过滤）L-001~003 |
| GET/POST | `/living/channels/{id}/posts` | 频道帖子 |
| POST | `/living/posts/{id}/reply` | 回复 |
| POST | `/living/posts/{id}/report` | 举报（≥3 次转人工） |
| GET/POST | `/living/lost-found` | 失物招领 L-101 |
| GET/POST | `/living/second-hand` | 二手交换 L-102 |

## OMEGA / NFC `/nfc`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/nfc/{card_id}` | 卡片信息（后端决定跳转目标）N-002 |
| POST | `/nfc/tap` | 碰触埋点 + 打卡 + 勋章 N-103 |
| GET | `/nfc/me/checkins` | 我的打卡进度 N-201 |

**网页端（非 API）**

- `GET /nfc/{card_id}` → 智能中间页（未装 App 时引导下载）
- `GET /.well-known/apple-app-site-association` → iOS Universal Links
- `GET /.well-known/assetlinks.json` → Android App Links
- `GET /api/v1/nfc-write/{card_id}` → NFC 写入工具载荷

## 勋章 `/badges`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/badges` | 勋章墙（已获得 + 待解锁）U-006 |

## 推送 `/push`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/push/devices` | 绑定极光 RegistrationID |
| GET | `/push/settings` | 推送偏好 |

## 管理后台 `/admin`（需 operator / admin）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/admin/polls` | 投票列表 / 创建 |
| POST | `/admin/polls/{id}/approve \| reject \| publish \| archive` | 人工终审与发布 |
| GET | `/admin/candidates` | 爬虫候选池 |
| POST | `/admin/candidates/{id}/review` | 候选话题人工终审 |
| POST | `/admin/candidates/{id}/draft` | LLM 生成投票草稿 |
| POST | `/admin/crawler/run` | 手动触发抓取 |
| GET | `/admin/crawler/status` | 爬虫状态 |
| GET | `/admin/review` | 内容审核队列 |
| POST | `/admin/review/club/{id}` \| `event/{id}` | 审核社团 / 活动 |
| GET/POST/DELETE | `/admin/sensitive-words` | 敏感词库（热更新） |
| GET/POST/PUT/DELETE | `/admin/nfc/cards` | NFC 卡片管理 |
| GET | `/admin/nfc/stats` | 碰触统计 |
| GET | `/admin/dashboard` | 数据看板 |
| POST | `/admin/export/votes` | 脱敏导出 CSV / Excel（ML-O-001） |
| GET | `/admin/export/preview` | 导出预览 |

## 网页后台

- `GET /admin/web` 数据看板
- `GET /admin/web/candidates` 爬虫候选池
- `GET /admin/web/polls` 投票管理
- `GET /admin/web/review` 内容审核
- `GET /admin/web/nfc` NFC 卡片
- `GET /admin/web/export` 数据导出
