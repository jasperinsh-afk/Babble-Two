# 云数据库种子注入

把 `seed_data.json` 中的演示数据灌入微信云开发数据库。

## 使用

```bash
cd bala-miniapp/scripts/seed
npm install
node seed.js <云开发环境ID>
```

环境 ID 形如 `goqd-prod-1x2y3z`，在微信开发者工具「云开发 → 环境」中查看。

脚本行为：对 `banners / polls / clubs / club_posts / events / dorm_channels / dorm_posts / lost_found / second_hand / nfc_cards / badges` 这些集合**先清空再写入**，请勿在生产环境直接运行。

## 方式二：云函数导入（推荐，不需要本地 Node 与腾讯云密钥）

`cloudfunctions/seedImport/` 是一个一次性导入函数，`seed_data.json` 已随函数打包。

1. 开发者工具右键 `cloudfunctions/seedImport` →「上传并部署：云端安装依赖」
2. 云开发控制台 → 云函数 → `seedImport` → 配置 → 把**超时时间改为 60 秒**
3. 右键 `seedImport` →「云端测试」，参数：

```json
{}
```

返回 `{"ok":true,"data":{"polls":"5/5",...}}` 即成功。若超时，按集合分批：

```json
{ "only": "polls" }
{ "only": "clubs" }
{ "only": "events" }
```

只清空不写入：`{ "clean": true }`。

导入完成后可删除该函数。

## 必须手动创建的索引

云开发控制台 → 数据库 → 对应集合 → 索引管理，创建以下索引（防重复投票/接龙的关键）：

| 集合 | 索引字段 | 类型 | 说明 |
|---|---|---|---|
| `ballots` | `_openid`(升序) + `pollId`(升序) | 唯一 | 一人一票 |
| `chain_members` | `_openid` + `pollId` + `optionId` | 唯一 | 接龙去重 |
| `club_members` | `_openid` + `clubId` | 唯一 | 加入社团去重 |
| `nfc_checkins` | `_openid` + `cardId` | 唯一 | 同一点位只计一次 |
| `user_badges` | `_openid` + `badgeId` | 唯一 | 勋章不重复发放 |
| `polls` | `status`(升序) + `endAt`(降序) | 普通 | 列表分页 |
| `events` | `startAt`(升序) | 普通 | 日历查询 |
| `club_posts` | `clubId`(升序) + `publishedAt`(降序) | 普通 | 社团动态 |

运行时集合 `ballots / chain_members / club_members / nfc_checkins / user_badges / cas_records` 无需预置数据，由云函数在用户操作时自动创建。

## 权限建议

云数据库集合权限统一设为「**所有用户可读，仅创建者可读写**」不适用于本项目（无登录态），建议设为「**所有用户可读，仅管理端可写**」，写入全部经云函数完成。
