# 个人记账接口补充功能

## 初始化和验证

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
```

新增迁移涉及重复提交凭证、周期模板/执行记录，以及预算提醒阈值允许为空。原有预算阈值保持原数值；原有账单不变。测试使用独立内存SQLite和缓存，不连接开发MySQL或Redis。

## 1. 重复提交保护

新增账单、修改/删除账单、恢复账单、新增账户、余额校准、创建/撤销转账、存钱罐存入/取出、创建/修改周期模板支持请求头：

```text
Authorization: Bearer <access_token>
Idempotency-Key: <本次操作生成的UUID>
Content-Type: application/json
```

- 一次操作一个键，网络重试沿用原键；新操作必须生成新键。
- 同一用户、同一键、同一接口方法及JSON内容：返回首次成功结果，余额只变更一次。
- 同一键用于其他接口、方法或内容：HTTP 409。
- 请求键只允许1~128位字母、数字、点、下划线、冒号、短横线。
- 失败请求不保存凭证；请求修复后可以继续使用该键。
- `Idempotency-Replayed: true` 表示响应来自历史成功结果。
- 原有客户端不传该请求头时保留原行为；要获得重试保护，调用方必须传键。
- 凭证长期保留。重试返回的是当时的响应，查询最新数据应使用详情接口。

周期执行另按“模板+计划日期”进行数据库去重，不缓存失败的执行结果。

## 2. 偏好设置实际生效

`PUT /api/v1/preferences/` 示例：

```json
{
  "page_size": 30,
  "budget_reminder_enabled": true,
  "budget_reminder_threshold": 80,
  "default_account": 1,
  "currency": "CNY"
}
```

- 分页：请求`page_size`优先，其次用户偏好，最后系统默认20。偏好范围5~100；显式查询范围1~100。
- 默认账户：只能设置本人启用、未删除账户；同步账户`is_default`。传null清除默认账户。
- 在账户接口切换/删除默认账户后，偏好中的默认账户同步更新；停用账户不能继续作为默认账户。
- 新增普通账单或周期模板省略`account_id`时采用有效默认账户；没有有效默认账户时返回400。
- 预算提醒开关关闭时，进度和概览不产生提醒，但超支状态仍按实际支出计算。
- 预算自己的`alert_threshold`非null时优先；null时动态跟随全局阈值。新建预算省略该值默认继承；修改时传null恢复继承。
- 默认货币同步用户资料和偏好，格式为三位大写字母；用于展示和导出，不进行汇率转换，也不重算历史金额。
- 主题仍由前端读取偏好后应用；后端不改变界面样式。个人时区字段保持原有行为，周期日期统一使用系统Asia/Shanghai时区。

## 3. 按标签筛选账单

```text
GET /api/v1/transactions/?tag_id=1&start_date=2026-10-01&end_date=2026-10-31
```

与账户、分类、类型、日期、关键字筛选叠加。tag_id必须为本人未删除标签；不存在、已删除或他人标签统一返回400“标签不存在”。回收站和导出使用同一组筛选参数。

## 4. 账单导出

```text
GET /api/v1/transactions/export/?tag_id=1&start_date=2026-10-01
```

返回UTF-8 BOM编码CSV文件，可直接用Excel打开。字段包括账单ID、类型、账户、分类、金额、展示货币、交易时间、商户、备注、标签。仅导出当前用户正常账单，使用列表相同筛选条件，导出全部匹配数据，不受分页限制；用户输入进行公式转义。文件下载成功返回CSV，参数失败仍返回统一JSON错误。

## 5. 回收站和账单恢复

```text
GET /api/v1/transactions/recycle-bin/
POST /api/v1/transactions/123/restore/
```

默认请求体`{}`。原账户或分类已删除/停用时，可以指定有效替代项：

```json
{
  "account_id": 2,
  "category_id": 3
}
```

仅恢复本人已删除账单。重新验证账户启用状态、分类归属和类型；普通账户恢复支出需要足够余额，信用卡可负余额。恢复收入增加余额，恢复支出扣减余额；所有操作在事务中执行。保留原ID、交易时间、金额、图片和标签关系，已删除标签仍不展示。正常统计和预算进度自动重新纳入恢复账单。再次恢复正常账单返回400；携带相同请求键的重试直接返回首次结果。

## 6. 周期账单

| 方法 | 地址 | 功能 |
|---|---|---|
| GET / POST | `/api/v1/transactions/recurring/` | 分页列表 / 创建模板 |
| GET / PUT / DELETE | `/api/v1/transactions/recurring/{id}/` | 详情 / 修改 / 逻辑删除模板 |
| POST | `/api/v1/transactions/recurring/{id}/run/` | 手动补记截至今天的到期周期 |
| GET | `/api/v1/transactions/recurring/{id}/executions/` | 分页查询历史执行记录 |

创建模板示例：

```json
{
  "name": "每月房租",
  "account_id": 1,
  "category_id": 2,
  "transaction_type": "expense",
  "amount": "1500.00",
  "tag_ids": [],
  "merchant": "房租",
  "note": "每月固定支出",
  "frequency": "monthly",
  "interval": 1,
  "start_date": "2026-11-01",
  "end_date": null,
  "is_active": true
}
```

- 支持daily、weekly、monthly、yearly；interval范围1~365。模板创建不直接记账。
- 首次执行日期为start_date，结束日期包含当天；未设end_date表示持续执行。
- 月末按起始日计算：每月31日依次取1月31日、2月最后一天、3月31日。闰日同理。
- 每条账单交易时间为计划日期系统时区00:00，金额变更复用普通账单服务。
- next_date、last_error、执行记录由服务维护，调用方不能改写。
- 未启用或逻辑删除模板不执行；已生成账单不受之后修改/删除模板影响。
- 模板已有执行记录后不能修改start_date、frequency、interval，需要新计划时创建新模板。其他字段修改只影响以后生成的账单。
- 余额不足、关联账户/分类/标签不可用时，失败周期不生成账单、不推进日期；错误保存至last_error。修复条件后重新执行。
- 单模板单次最多补记100个周期，结果`more_due=true`表示仍有积压。`error`非空时需要处理后重试；该接口返回执行报告，可以包含已经成功的周期。
- 删除周期生成的账单不会再次生成该周期；可以通过回收站恢复原账单。

定时执行命令：

```powershell
.\.venv\Scripts\python.exe manage.py process_recurring_transactions
```

由部署环境的Windows任务计划程序或Linux计划任务每天调用。代码已提供执行命令，不会自行安装系统计划任务。`--limit`控制单次处理的模板数量，默认1000，范围1~10000；`--date YYYY-MM-DD`可指定过去日期，不允许提前执行未来周期。业务失败返回非零退出码并保留模板错误。重复或重叠调用由模板行锁、执行记录唯一约束保护。
