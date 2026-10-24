# 叭啦 Babble

> 面向个人学习与兴趣社区的「表达型」**微信小程序**
> 项目代号 Project Y · V2.0（微信小程序 + 微信云开发）
>
> **品牌说明：** 原「七德通 GoQD」已于 2026-10-18 升级更名为 **「叭啦 Babble」**（见《叭啦-品牌形象文档》V2.0），产品与技术体系不变。

---

## 一、这是什么

叭啦 Babble 把**投票互动、社团信息、活动日历、生活圈、扫码打卡**聚合在一个小程序里。

本项目由 Flutter App + FastAPI 架构整体改造为**微信原生小程序 + 微信云开发（云函数 + 云数据库）**，改造范围与映射关系见 [`docs/MIGRATION-TO-WECHAT.md`](docs/MIGRATION-TO-WECHAT.md)。

**与上一版的三个根本变化：**

1. **无登录**：彻底移除注册/登录/学号/邮箱/JWT，用户静默以 `wx.login` 换取的 openid 作为身份标识，仅用于投票去重、接龙去重、打卡与勋章归属。
2. **无 UGC**：移除评论、用户创建投票、社团发帖与入驻申请。**接龙保留**。所有内容由数据库注入（种子脚本）或运营侧发布。
3. **NFC 降级为扫码**：不使用 `wx.getNFCAdapter`，OMEGA 卡片/打卡/勋章全部走 `wx.scanCode` 扫海报小程序码。

---

## 二、目录结构

```
bala-miniapp/
├── miniprogram/            微信原生小程序（WXML / WXSS / JS）
│   ├── pages/              launch · index · campus · message · vote · club · calendar · living · scan · profile
│   ├── components/         poll-card / club-card / event-card / section-header / empty-view / result-chart
│   ├── custom-tab-bar/     自定义 TabBar（今日/校园/消息/我的，消息未读角标）
│   └── utils/              api.js（云调用封装）· format.js · storage.js · config.js
├── cloudfunctions/         微信云开发云函数（Node.js 18）
│   ├── identity/           静默换取 openid
│   ├── home/               feed 聚合
│   ├── vote/               list / detail / results / cast / joinChain / leaveChain
│   ├── club/               list / detail / posts / join / leave
│   ├── event/              list / calendar / detail / join / myCas
│   ├── living/             channels / channelPosts / lostFound / secondHand
│   ├── scan/               cardByCode / checkin（含勋章解锁）
│   ├── me/                 overview 本地足迹 + messages 消息中心
│   ├── analytics/          端上埋点上报（track）
│   └── adminIngest/        运营侧写入网关（INGEST_TOKEN 鉴权）
├── scripts/seed/           云数据库种子注入（seed.js + seed_data.json）
├── server/                 运营侧 FastAPI 服务（墨麟书院输入/输出层 + 运营后台）
│   └── app/
│       ├── crawler/        输入层：5 源爬虫 + 三层过滤 + 草稿生成
│       ├── prompts/        LLM Prompt 模板
│       ├── services/        crawler_service · export_service · llm_service · moderation_service
│       ├── api/v1/export.py  输出层：脱敏导出
│       ├── admin_web.py   运营后台（Jinja2 服务端渲染）
│       └── cloudbase_client.py  访问云开发数据库的 HTTP API 客户端
├── archive/                归档（不参与运行）
│   ├── flutter/            原 Flutter 客户端
│   └── fastapi/            原 FastAPI C 端业务层（路由/服务/模型）
└── docs/
```

---

## 三、技术栈

| 层次 | 选型 |
|---|---|
| 小程序端 | 微信原生小程序（WXML / WXSS / JS / JSON），自定义 TabBar |
| 端上基建 | `wx.login` · `wx.cloud.callFunction` · `wx.scanCode` · `wx.setStorageSync` |
| 图表 | 自研 `result-chart` 组件（CSS 动画条形 / PK 对战条） |
| 后端 | 微信云开发云函数（Node.js 18）+ 云数据库（文档型） |
| 身份 | 云函数内 `cloud.getWXContext().OPENID`，端上不可伪造 |
| 运营侧服务 | FastAPI + Playwright/httpx + 通义千问 |
| 运营侧写库 | 微信云开发 HTTP API / `adminIngest` 云函数 |

---

## 四、快速开始

### 1. 小程序

1. 微信开发者工具 → 导入项目，目录选 `miniprogram/`
2. 「云开发」开通环境，记录环境 ID
3. `project.config.json` 填入你的 AppID
4. 右键 `cloudfunctions/` 下每个函数 →「上传并部署：云端安装依赖」
5. 编译预览

### 2. 灌入演示数据（推荐走云函数，无需本地 Node）

1. 上传 `cloudfunctions/seedImport`（右键 → 上传并部署：云端安装依赖）
2. 云开发控制台把 `seedImport` 的**超时时间改为 60 秒**
3. 右键 `seedImport` →「云端测试」，参数 `{}`

也可用本地脚本（需 Node 18 与腾讯云密钥）：

```bash
cd scripts/seed
npm install
node seed.js <云开发环境ID>
```

> 首次执行前请按 `scripts/seed/README.md` 创建防重复投票所需的唯一索引。

### 3. 运营侧服务（墨麟书院）

```bash
cd server
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # 填入 WECHAT_APPID / WECHAT_SECRET / WECHAT_CLOUD_ENV / INGEST_TOKEN / ADMIN_WEB_TOKEN
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```

- 运营后台：http://localhost:8000/admin/web （首次用 `ADMIN_WEB_TOKEN` 登录）
- 接口文档：http://localhost:8000/docs

---

## 五、功能模块

| 模块 | 说明 | 变化 |
|---|---|---|
| 今日首页 | Banner + **今日行动**（活动变更/投票结果提醒）+ 今日安排 + 热门投票 + 推荐活动 | 改版：四 Tab 之首 |
| 投票中心 | 单选/多选/PK/排序 + 改票 + 结果图表 + **接龙** | 保留，移除评论与用户创建 |
| 社团广场 | 分类筛选 + 社团详情 + 官方内容流 | 移除入驻申请与发帖 |
| 活动日历 | 月视图 + 近期活动 + 报名 + CAS | 保留 |
| 生活圈 | 生活圈 / 失物招领 / 二手交换 | 移除回复功能 |
| 扫码打卡 | 扫码落地页 + 打卡 + 勋章解锁 | **NFC 硬件降级为扫码** |
| 本地足迹 | 我的投票 / 勋章墙 / 打卡进度 | 「我的」改版，无账号 |
| 墨麟书院·输入层 | 5 源爬虫 + 敏感词 + LLM 三层过滤 | 保留在运营侧 |
| 墨麟书院·输出层 | 投票数据脱敏 CSV/Excel 导出 | 保留在运营侧，数据源改为云数据库 |

---

## 六、四个一级 Tab

```
今日 │ 校园 │ 消息 │ 我的（本地足迹）
```

投票 / 社团 / 日历 / 生活圈 / 扫码打卡为二级页，从「校园」进入，旧深链保留。

---

## 七、合规红线

- 政治、宗教、性别对立话题**一票否决**，人工复核不可省略
- 爬虫抓取的是「话题」而非「原文」，投票题干由 AI 原创
- 每日必须有值班运营确认发布，**禁止全自动无人审核上线**
- 数据导出前必须脱敏，**移除 `_openid` 等一切可关联到个人的字段**
- 运营侧密钥（`WECHAT_SECRET` / `INGEST_TOKEN` / `ADMIN_WEB_TOKEN`）只存在于服务端，绝不下发小程序端

---

## 八、文档索引

| 文档 | 位置 |
|---|---|
| 云函数接口契约 | `docs/API.md` |
| Flutter → 小程序改造记录 | `docs/MIGRATION-TO-WECHAT.md` |
| 旧「叭啦」→ 七德通 GoQD 记录（历史） | `docs/MIGRATION.md` |
| 产品策划方案 | `../叭啦-产品策划方案.md` |
| PRD 产品需求文档 | `../叭啦-PRD产品需求文档.md` |
| 技术架构文档（V2.0 整合版） | `../叭啦-技术架构总览文档.md` |
| OMEGA 技术实现文档 | `../叭啦-墨麟OMEGA技术实现文档.md` |
| Prompt 工程文档 | `../叭啦-Prompt工程文档.md` |
| 品牌形象文档 | `../叭啦-品牌形象文档.md` |

---

*叭啦 Babble · Project Y*
