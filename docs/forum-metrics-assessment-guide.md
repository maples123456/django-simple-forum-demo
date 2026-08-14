# 论坛常见指标能力评估手册

## 1. 文档目标

这份文档用于检验一个明确目标：

> 是否能够在不使用互联网、只查看论坛项目的情况下，独立定义、计算、实现、核验并解释常见论坛指标。

“看懂 SQL 或 Django ORM”不等于掌握指标。每项考核都按五种能力评分：

| 能力 | 分值 | 合格表现 |
| :---: | :---: | :---: |
| 指标定义 | 20 | 明确用户范围、行为、时间、去重和数据完整性 |
| 手工计算 | 20 | 展示过滤、分组、去重、分子和分母的变化过程 |
| 查询实现 | 20 | 能写出正确 SQL、Django ORM 或清晰伪代码 |
| 结果核验 | 20 | 至少提出四项可执行检查 |
| 业务解释 | 20 | 说明指标能回答什么、不能回答什么以及下一步分析 |

单项达到 80 分且没有关键错误，才算可以在工作中使用。建议每次只选择一个指标，在 30～45 分钟内闭卷完成。

## 2. 项目统一口径

除题目另有说明外，使用以下项目口径：

- 时区：`Asia/Shanghai`。
- 正式结果只使用已经结束的自然日，时间范围使用左闭右开区间。
- 普通用户：`is_staff = FALSE` 且 `is_superuser = FALSE`。
- 有效活跃事件：`page_view`、`board_view`、`post_view`、`post_create`、`reply_create`、`post_like`。
- `login`、`sign_up`、`post_unlike` 不单独使用户成为活跃用户。
- 登录用户按 `user_id` 去重，匿名访问按非空 `anonymous_id` 去重。
- 行为次数和行为用户数是不同指标，不能混用。

项目内可查看：

- `analytics/models.py`
- `analytics/services.py`
- `analytics/views.py`
- `analytics/tests.py`

## 3. 通用作答模板

每道考核都应提交以下五项：

1. 指标合同：业务问题、用户范围、分子、分母、去重字段、时间窗口、排除条件。
2. 手工计算：展示操作前数据、过滤后数据、去重或分组结果和最终数值。
3. 查询实现：SQL、Django ORM 或清晰伪代码。
4. 结果核验：至少四项可以真正执行的检查。
5. 业务解释：解释给定变化，说明证据边界和下一步拆解方向。

## 4. 考核目录

| 编号 | 指标主题 | 核心难点 |
| :---: | :---: | :---: |
| 1 | WAU、MAU 与活跃频率 | 跨日用户去重与滚动窗口 |
| 2 | 新增激活率 | 保留未激活用户并稳定分母 |
| 3 | 发帖、回复和点赞参与 | 区分动作次数与参与用户数 |
| 4 | 匿名 UV 与注册转化 | 匿名身份回连与转化归因 |
| 5 | D1、D7 留存与 Cohort 成熟度 | Cohort 时间、观察期和加权汇总 |
| 6 | 帖子回应质量 | 帖子粒度、零回复和首次回复时间 |
| 7 | 板块级活跃与互动 | 分组去重、跨板块重叠与绝对贡献量 |

---

## 考核一：WAU、MAU 与活跃频率

> **考核重点：** 跨日窗口内按 `user_id` 重新去重，不能汇总每日 DAU。

### 业务场景

> 计算 08-10 的 DAU、WAU、MAU、DAU/WAU 和 DAU/MAU。

08-10 为完整自然日。下面只列出用户产生有效事件的日期：

| 用户 | 用户类型 | 07-12 | 08-03 | 08-04 | 08-05 | 08-08 | 08-10 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| U1 | 普通用户 | ✓ |  | ✓ | ✓ | ✓ | ✓ |
| U2 | 普通用户 |  | ✓ | ✓ |  |  | ✓ |
| U3 | 普通用户 |  |  |  | ✓ |  |  |
| U4 | staff | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| U5 | 普通用户 | ✓ |  |  |  |  |  |

### 评分任务

#### 1. 指标定义（20 分）

- 分别定义 08-10 的 DAU、WAU 和 MAU。
- 写明三个窗口的起止日期。
- 说明 `DAU/WAU` 为什么不是留存率。

#### 2. 手工计算（20 分）

- 分别列出进入 DAU、WAU、MAU 的用户集合。
- 计算五个最终指标。
- 展示为什么不能把最近 7 天 DAU 相加得到 WAU。

#### 3. 查询实现（20 分）

写出 WAU 查询。必须包含：

- `08-04 00:00:00 <= occurred_at < 08-11 00:00:00`；
- 普通登录用户过滤；
- 有效事件过滤；
- `COUNT(DISTINCT user_id)`。

#### 4. 结果核验（20 分）

至少给出四项检查，其中必须包含：

- `DAU <= WAU <= MAU`；
- WAU 不能大于窗口内合格普通登录用户数；
- 抽查跨多日活跃的 U1 只计算一次；
- 确认 staff 用户 U4 被排除。

#### 5. 业务解释（20 分）

假设本周 `DAU/WAU` 从 25% 降到 18%，但 WAU 上升 10%。解释可能发生了什么，以及还需要检查哪些信息。

### 一票否决错误

- 把 7 天 DAU 相加作为 WAU。
- WAU 每天分别去重后再求和。
- 把 `DAU/WAU` 称为 D1 或 D7 留存。
- 把 staff 用户计入活跃用户。

### 对应参考答案

> 以下 SQL 使用 PostgreSQL 写法。`:day_start` 表示 Asia/Shanghai 的 08-10 00:00，`:next_day_start` 表示 08-11 00:00；查询统一使用左闭右开时间区间。

#### A. 先固定指标口径

- DAU：08-10 当天产生至少一次有效事件的普通登录用户数。
- WAU：08-04 至 08-10 产生至少一次有效事件的普通登录用户数。
- MAU：07-12 至 08-10 产生至少一次有效事件的普通登录用户数。
- 有效事件只包括 `page_view`、`board_view`、`post_view`、`post_create`、`reply_create`、`post_like`。
- staff、superuser、匿名用户均不进入用户集合；每个窗口内按 `user_id` 去重。

#### B. 用 SQL 展示过滤与窗口去重

先产生一份“合格事件”，再分别从同一份数据中建立三个用户集合：

```sql
WITH eligible_events AS (
    SELECT e.user_id, e.occurred_at
    FROM analytics_analyticsevent AS e
    JOIN auth_user AS u ON u.id = e.user_id
    WHERE e.occurred_at >= :mau_start
      AND e.occurred_at <  :next_day_start
      AND u.is_staff = FALSE
      AND u.is_superuser = FALSE
      AND e.event_name IN (
          'page_view', 'board_view', 'post_view',
          'post_create', 'reply_create', 'post_like'
      )
),
dau_users AS (
    SELECT DISTINCT user_id
    FROM eligible_events
    WHERE occurred_at >= :day_start
),
wau_users AS (
    SELECT DISTINCT user_id
    FROM eligible_events
    WHERE occurred_at >= :wau_start
),
mau_users AS (
    SELECT DISTINCT user_id
    FROM eligible_events
)
SELECT
    (SELECT COUNT(*) FROM dau_users) AS dau,
    (SELECT COUNT(*) FROM wau_users) AS wau,
    (SELECT COUNT(*) FROM mau_users) AS mau;
```

`DISTINCT user_id` 发生在整个窗口，而不是每天分别去重后相加。根据题目数据，各窗口去重后的变化如下：

| 计算层级 | 保留的普通用户 | 排除或去重原因 | 行数 |
| :---: | :---: | :---: | :---: |
| 08-10 有效事件 | U1、U2 | U4 为 staff | 2 |
| 7 日窗口去重 | U1、U2、U3 | U1 虽多日活跃仍只保留一次 | 3 |
| 30 日窗口去重 | U1、U2、U3、U5 | U4 仍然排除 | 4 |

#### C. 计算最终指标

```sql
WITH metric AS (
    -- 此处放入上一段查询，返回 dau、wau、mau
    SELECT 2 AS dau, 3 AS wau, 4 AS mau
)
SELECT
    dau,
    wau,
    mau,
    ROUND(100.0 * dau / NULLIF(wau, 0), 2) AS dau_wau_pct,
    ROUND(100.0 * dau / NULLIF(mau, 0), 2) AS dau_mau_pct
FROM metric;
```

| 指标 | 分子 | 分母 | 结果 |
| :---: | :---: | :---: | :---: |
| DAU | 08-10 去重用户 | 无 | 2 |
| WAU | 7 日窗口去重用户 | 无 | 3 |
| MAU | 30 日窗口去重用户 | 无 | 4 |
| DAU/WAU | 2 | 3 | 66.67% |
| DAU/MAU | 2 | 4 | 50.00% |

#### D. 用 SQL 核验结果

```sql
WITH result AS (
    SELECT 2 AS dau, 3 AS wau, 4 AS mau
)
SELECT
    dau <= wau AS dau_not_greater_than_wau,
    wau <= mau AS wau_not_greater_than_mau
FROM result;
```

还应抽查 WAU 用户明细，确认 U1 只出现一次、U4 没有出现：

```sql
SELECT user_id, COUNT(*) AS effective_event_rows
FROM eligible_events
WHERE occurred_at >= :wau_start
GROUP BY user_id
ORDER BY user_id;
```

#### E. 业务解释

若 `DAU/WAU` 从 25% 降到 18%，但 WAU 上升 10%，较稳妥的结论是：周内触达的用户规模扩大了，但这些用户在任一单日出现的比例降低，使用频率可能下降。它不是“留存下降”的直接证据。下一步应继续拆解每日 DAU、新老用户贡献、星期效应、获客来源及埋点完整性。

---

## 考核二：新增激活率

> **考核重点：** 新增用户是稳定分母，零有效行为用户也必须保留。

### 业务场景

> 计算 08-10 新增用户的注册日激活率。

用户注册和当天行为如下：

| 用户 | 用户类型 | 注册时间 | 当天行为 |
| :---: | :---: | :---: | :---: |
| U1 | 普通用户 | 08-10 09:00 | `sign_up`、`page_view` |
| U2 | 普通用户 | 08-10 10:00 | `sign_up`、`login` |
| U3 | 普通用户 | 08-10 11:00 | `sign_up`、`reply_create` |
| U4 | 普通用户 | 08-10 12:00 | `sign_up`；08-11 才产生 `post_view` |
| U5 | staff | 08-10 13:00 | `sign_up`、`page_view` |

### 评分任务

#### 1. 指标定义（20 分）

完整定义“注册日激活率”，明确：

- 哪些用户进入新增分母；
- 什么行为算激活；
- 激活窗口是否允许跨到第二天；
- staff 是否进入分子或分母。

#### 2. 手工计算（20 分）

按以下顺序展示计算过程：

1. 过滤得到普通新增用户；
2. 判断每个新增用户是否在注册日产生有效行为；
3. 得到激活用户集合；
4. 写出分子、分母和激活率。

#### 3. 查询实现（20 分）

写 SQL、ORM 或伪代码。需要避免：

- 一个用户多个有效事件导致分子重复；
- 使用事件行数作为激活人数；
- 内连接事件表后把未激活新增用户从分母中丢失。

#### 4. 结果核验（20 分）

至少检查：

- `activated_new_users <= new_users`；
- 激活率在 0%～100%；
- U2 只有登录，不应激活；
- U4 次日才活跃，不属于注册日激活。

#### 5. 业务解释（20 分）

新增用户数上涨 50%，新增激活率从 60% 降至 35%。说明这两个指标组合可能代表什么，并提出至少三个下钻方向。

### 一票否决错误

- 只把激活用户放进分母。
- 把 `login` 或 `sign_up` 当成有效激活行为。
- 把次日活跃算入注册日激活。
- 从事件表内连接新增用户后丢失零事件用户。

### 对应参考答案

#### A. 先固定指标口径

分母是 08-10 注册的全部普通用户，即使用户注册后没有事件也必须保留。分子是这些用户中在 08-10 自然日内至少产生一次有效事件的人数。注册、登录不属于有效激活行为，次日行为也不能回填到注册日。

#### B. 先建立稳定分母，再左连接行为

```sql
WITH new_users AS (
    SELECT id AS user_id, date_joined
    FROM auth_user
    WHERE date_joined >= :day_start
      AND date_joined <  :next_day_start
      AND is_staff = FALSE
      AND is_superuser = FALSE
),
active_new_users AS (
    SELECT DISTINCT e.user_id
    FROM analytics_analyticsevent AS e
    JOIN new_users AS n ON n.user_id = e.user_id
    WHERE e.occurred_at >= :day_start
      AND e.occurred_at <  :next_day_start
      AND e.event_name IN (
          'page_view', 'board_view', 'post_view',
          'post_create', 'reply_create', 'post_like'
      )
)
SELECT
    n.user_id,
    CASE WHEN a.user_id IS NULL THEN 0 ELSE 1 END AS activated_on_signup_day
FROM new_users AS n
LEFT JOIN active_new_users AS a ON a.user_id = n.user_id
ORDER BY n.user_id;
```

左连接后的用户级结果为：

| 用户 | 是否进入新增分母 | 注册日有效行为 | 是否激活 | 原因 |
| :---: | :---: | :---: | :---: | :---: |
| U1 | 是 | `page_view` | 是 | 注册日产生有效浏览 |
| U2 | 是 | 无 | 否 | `login` 不属于有效事件 |
| U3 | 是 | `reply_create` | 是 | 注册日产生有效互动 |
| U4 | 是 | 无 | 否 | 有效行为发生在 08-11 |
| U5 | 否 | `page_view` | 不适用 | staff 不进入分子或分母 |

如果把 `new_users` 与事件表直接内连接，U2 和 U4 会整行消失，分母会错误地从 4 变成 2。

#### C. 计算分子、分母和激活率

```sql
WITH new_users AS (...),
active_new_users AS (...)
SELECT
    COUNT(DISTINCT n.user_id) AS new_users,
    COUNT(DISTINCT a.user_id) AS activated_new_users,
    ROUND(
        100.0 * COUNT(DISTINCT a.user_id)
        / NULLIF(COUNT(DISTINCT n.user_id), 0),
        2
    ) AS activation_rate_pct
FROM new_users AS n
LEFT JOIN active_new_users AS a ON a.user_id = n.user_id;
```

| 指标 | 用户集合 | 结果 |
| :---: | :---: | :---: |
| 新增用户 | U1、U2、U3、U4 | 4 |
| 激活新增用户 | U1、U3 | 2 |
| 注册日激活率 | 2 / 4 | 50.00% |

#### D. 用 SQL 核验分母是否丢失

```sql
SELECT
    activated_new_users <= new_users AS numerator_is_valid,
    activation_rate_pct BETWEEN 0 AND 100 AS rate_is_valid
FROM daily_activation_result;
```

另外要抽查未激活明细，确认 U2 只有 `login`，U4 的首个有效行为发生在次日，而不是查询时间边界写错。

#### E. 业务解释

新增用户上涨 50%，但激活率从 60% 降到 35%，说明新增规模扩大并未等比例转化为真实论坛使用。可能是低意向渠道占比提高、注册后引导变差，或有效事件埋点丢失。下一步应按来源渠道、设备/页面、注册到首个有效行为的耗时拆解，并核验客户端事件上报成功率。

---

## 考核三：发帖、回复和点赞参与

> **考核重点：** 同时区分事件动作量、独立参与用户和用户参与率。

### 业务场景

> 计算 08-10 的发帖用户数、回复用户数、点赞用户数、发帖率、回复率和人均发帖数。

08-10 的用户日数据：

| 用户 | 是否活跃 | 发帖数 | 回复数 | 点赞动作数 |
| :---: | :---: | :---: | :---: | :---: |
| U1 | 1 | 3 | 0 | 1 |
| U2 | 1 | 0 | 2 | 0 |
| U3 | 1 | 0 | 1 | 2 |
| U4 | 1 | 1 | 0 | 0 |
| U5 | 1 | 0 | 0 | 0 |

### 评分任务

#### 1. 指标定义（20 分）

分别定义：

- 发帖用户数与发帖动作数；
- 回复用户数与回复动作数；
- 点赞用户数与点赞动作数；
- 发帖率与人均发帖数。

#### 2. 手工计算（20 分）

计算：

- DAU；
- 发帖用户、回复用户、点赞用户集合；
- 发帖率、回复率；
- 人均发帖数。

要求明确每个指标的分子和分母。

#### 3. 查询实现（20 分）

写出按日生成以下字段的查询：

- `posts_created`；
- `posting_users`；
- `replying_users`；
- `liking_users`。

说明哪些字段使用 `COUNT(*)`，哪些字段使用 `COUNT(DISTINCT user_id)`。

#### 4. 结果核验（20 分）

至少检查：

- 三类参与用户数都不能大于 DAU；
- 发帖用户数不能大于发帖动作数；
- 用户 U1 发 3 帖仍只算 1 个发帖用户；
- 分日发帖用户数不能直接求和作为窗口发帖用户数。

#### 5. 业务解释（20 分）

某日发帖动作数上涨 40%，但发帖用户数没有变化。解释至少两种可能情况，以及下一步应该查看什么。

### 一票否决错误

- 使用帖子数除以 DAU 并命名为发帖率。
- 把每日发帖用户数求和当成 30 日发帖用户数。
- 认为发帖、回复、点赞用户三类互斥。

### 对应参考答案

#### A. 先区分动作量和用户量

- `posts_created` 是发帖事件行数；`posting_users` 是至少发过一次帖的独立用户数。
- 发帖率的分子是发帖用户数，分母是 DAU；帖子数除以 DAU 是“每活跃用户发帖数”，不是发帖率。
- 人均发帖数的分子是帖子数，分母是发帖用户数。

#### B. 把用户日计数转换为参与标记

```sql
WITH user_flags AS (
    SELECT
        user_id,
        CASE WHEN post_count  > 0 THEN 1 ELSE 0 END AS is_poster,
        CASE WHEN reply_count > 0 THEN 1 ELSE 0 END AS is_replier,
        CASE WHEN like_count  > 0 THEN 1 ELSE 0 END AS is_liker,
        post_count,
        reply_count,
        like_count
    FROM analytics_useractivitydaily
    WHERE activity_date = DATE '2026-08-10'
      AND (
          page_view_count + board_view_count + post_view_count
          + post_count + reply_count + like_count
      ) > 0
)
SELECT * FROM user_flags ORDER BY user_id;
```

| 用户 | 发帖标记 | 回复标记 | 点赞标记 | 发帖动作 | 回复动作 | 点赞动作 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| U1 | 1 | 0 | 1 | 3 | 0 | 1 |
| U2 | 0 | 1 | 0 | 0 | 2 | 0 |
| U3 | 0 | 1 | 1 | 0 | 1 | 2 |
| U4 | 1 | 0 | 0 | 1 | 0 | 0 |
| U5 | 0 | 0 | 0 | 0 | 0 | 0 |

#### C. 用条件聚合计算指标

```sql
WITH user_flags AS (...)
SELECT
    COUNT(*) AS dau,
    SUM(post_count) AS posts_created,
    SUM(reply_count) AS replies_created,
    SUM(like_count) AS likes_created,
    SUM(is_poster) AS posting_users,
    SUM(is_replier) AS replying_users,
    SUM(is_liker) AS liking_users,
    ROUND(100.0 * SUM(is_poster) / NULLIF(COUNT(*), 0), 2) AS posting_rate_pct,
    ROUND(100.0 * SUM(is_replier) / NULLIF(COUNT(*), 0), 2) AS replying_rate_pct,
    ROUND(1.0 * SUM(post_count) / NULLIF(SUM(is_poster), 0), 2) AS posts_per_poster
FROM user_flags;
```

| 指标 | 分子 | 分母 | 结果 |
| :---: | :---: | :---: | :---: |
| DAU | U1～U5 | 无 | 5 |
| 发帖用户数 | U1、U4 | 无 | 2 |
| 回复用户数 | U2、U3 | 无 | 2 |
| 点赞用户数 | U1、U3 | 无 | 2 |
| 发帖率 | 2 个发帖用户 | 5 DAU | 40.00% |
| 回复率 | 2 个回复用户 | 5 DAU | 40.00% |
| 人均发帖数 | 4 篇帖子 | 2 个发帖用户 | 2.00 |

若直接从事件表计算，动作量使用 `COUNT(*) FILTER (...)`，用户量必须使用 `COUNT(DISTINCT user_id) FILTER (...)`。

#### D. 用 SQL 核验

```sql
SELECT
    posting_users <= dau AS posters_valid,
    replying_users <= dau AS repliers_valid,
    liking_users <= dau AS likers_valid,
    posting_users <= posts_created AS poster_action_relation_valid
FROM daily_participation_result;
```

30 日发帖用户必须对 30 日内的 `user_id` 再做一次整体去重，不能把 30 个每日 `posting_users` 相加。

#### E. 业务解释

发帖动作上涨 40%，发帖用户数不变，首先说明增长来自既有创作者提高发帖频次，而不是更多用户成为创作者。也可能由少数高频用户、活动集中发帖或垃圾内容造成。应继续查看每位创作者的发帖分布、中位数与 P90、新增创作者数、帖子零回复率及违规内容占比。

---

## 考核四：匿名 UV 与注册转化

> **考核重点：** 只有能够通过同一 `anonymous_id` 回连且满足时间顺序的注册才能归因。

### 业务场景

> 计算 08-10 的匿名 UV、可归因匿名注册人数和匿名注册转化率。

事件按时间排序：

| 时间 | anonymous_id | user_id | 事件 |
| :---: | :---: | :---: | :---: |
| 09:00 | A1 | NULL | `page_view` |
| 09:10 | A1 | U1 | `sign_up` |
| 09:12 | A1 | U1 | `page_view` |
| 10:00 | A2 | NULL | `page_view` |
| 10:05 | A2 | NULL | `post_view` |
| 11:00 | A3 | NULL | `page_view` |
| 11:20 | A4 | U2 | `sign_up` |
| 11:25 | A4 | U2 | `page_view` |
| 12:00 | A5 | NULL | `page_view` |
| 12:30 | A5 | U3（staff） | `sign_up` |

### 评分任务

#### 1. 指标定义（20 分）

定义：

- 匿名 UV；
- 可归因匿名注册；
- 纯匿名访客；
- 匿名注册转化率。

说明为什么 `anonymous_id` 和 `user_id` 不能直接相加后称为全站独立人数。

#### 2. 手工计算（20 分）

必须展示：

1. 匿名 `page_view` 身份集合；
2. 注册普通用户集合；
3. 通过同一 `anonymous_id` 成功连接的记录；
4. 先浏览后注册的顺序检查；
5. 最终分子、分母和转化率。

#### 3. 查询实现（20 分）

写 SQL、ORM 或伪代码，实现匿名浏览与后续注册的身份连接。必须防止：

- A1 的多条事件造成注册人数重复；
- A3 与 U2 因 anonymous_id 不同而被错误归因；
- staff 注册进入转化分子。

#### 4. 结果核验（20 分）

至少检查：

- 可归因注册人数不能大于普通注册人数；
- 可归因注册人数不能大于匿名 UV；
- 每个注册用户最多计算一次；
- 抽查关联记录满足匿名浏览早于注册。

#### 5. 业务解释（20 分）

匿名 UV 上涨 30%，注册数持平，匿名注册转化率下降。解释可能原因，并说明埋点丢失或身份无法回连会怎样影响结果。

### 一票否决错误

- 用注册人数除以匿名 UV，却没有确认注册来自这些匿名身份。
- 只按 `session_id` 或事件时间接近就猜测身份关联。
- 同一个 `anonymous_id` 多次浏览被计算多次。
- 把无法归因的注册强行归入匿名转化。

### 对应参考答案

#### A. 先定义身份与归因规则

匿名 UV 是窗口内产生匿名 `page_view` 的非空 `anonymous_id` 数。可归因注册要求普通用户的同一个 `anonymous_id` 在注册时间之前出现过匿名 `page_view`。分母按匿名身份去重，分子按注册 `user_id` 去重。

#### B. 分别建立匿名访问和普通注册集合

```sql
WITH anonymous_views AS (
    SELECT
        anonymous_id,
        MIN(occurred_at) AS first_anonymous_view_at
    FROM analytics_analyticsevent
    WHERE occurred_at >= :day_start
      AND occurred_at <  :next_day_start
      AND event_name = 'page_view'
      AND user_id IS NULL
      AND anonymous_id <> ''
    GROUP BY anonymous_id
),
ordinary_signups AS (
    SELECT
        u.id AS user_id,
        u.date_joined,
        e.anonymous_id
    FROM auth_user AS u
    JOIN analytics_analyticsevent AS e
      ON e.user_id = u.id
     AND e.anonymous_id <> ''
     AND e.occurred_at >= :day_start
     AND e.occurred_at <  :next_day_start
    WHERE u.date_joined >= :day_start
      AND u.date_joined <  :next_day_start
      AND u.is_staff = FALSE
      AND u.is_superuser = FALSE
),
attributed_links AS (
    SELECT DISTINCT s.user_id, s.anonymous_id
    FROM ordinary_signups AS s
    JOIN anonymous_views AS v
      ON v.anonymous_id = s.anonymous_id
     AND v.first_anonymous_view_at <= s.date_joined
),
attributed_signups AS (
    SELECT DISTINCT user_id
    FROM attributed_links
)
SELECT
    (SELECT COUNT(*) FROM anonymous_views) AS anonymous_uv,
    (SELECT COUNT(*) FROM attributed_signups) AS attributed_registrations;
```

连接前后只保留关键字段，可看到归因是如何发生的：

| 匿名身份 | 是否匿名浏览 | 后续注册 | ID 是否相同 | 时间顺序正确 | 是否归因 |
| :---: | :---: | :---: | :---: | :---: | :---: |
| A1 | 是 | U1 | 是 | 是 | 是 |
| A2 | 是 | 无 | 不适用 | 不适用 | 否 |
| A3 | 是 | U2 使用 A4 | 否 | 不适用 | 否 |
| A5 | 是 | U3（staff） | 是 | 是 | 否 |

#### C. 计算转化率和纯匿名访客

```sql
WITH anonymous_views AS (...),
attributed_links AS (...),
attributed_signups AS (...)
SELECT
    COUNT(*) AS anonymous_uv,
    (SELECT COUNT(*) FROM attributed_signups) AS attributed_registrations,
    COUNT(*) FILTER (
        WHERE NOT EXISTS (
            SELECT 1
            FROM attributed_links AS l
            WHERE l.anonymous_id = anonymous_views.anonymous_id
        )
    ) AS pure_anonymous_visitors,
    ROUND(
        100.0 * (SELECT COUNT(*) FROM attributed_signups)
        / NULLIF(COUNT(*), 0),
        2
    ) AS anonymous_signup_conversion_pct
FROM anonymous_views;
```

| 指标 | 集合或计算 | 结果 |
| :---: | :---: | :---: |
| 匿名 UV | A1、A2、A3、A5 | 4 |
| 可归因普通注册 | U1 | 1 |
| 纯匿名访客 | A2、A3、A5 | 3 |
| 匿名注册转化率 | 1 / 4 | 25.00% |

“登录用户数 + anonymous_id 数”不能直接称为全站独立人数，因为同一个人可能在登录前后同时拥有两种身份，必须先做身份回连。

#### D. 用 SQL 核验归因边界

```sql
SELECT
    attributed_registrations <= ordinary_registrations AS within_signup_limit,
    attributed_registrations <= anonymous_uv AS within_uv_limit
FROM anonymous_conversion_result;
```

还要检查每个注册用户只出现一次、关联 ID 非空、浏览时间早于注册时间，并监测一个 `anonymous_id` 关联多个账号的异常情况。

#### E. 业务解释

匿名 UV 上涨 30%、注册数持平、可归因转化率下降，可能表示新增匿名流量意向较低或注册流程变差。但 `anonymous_id` 丢失、Cookie 重置或登录后没有继续上报同一 ID，也会使可归因分子偏低。因此还应对比总注册数、可归因注册覆盖率以及不同入口的 ID 延续率，不能直接断言真实注册意愿下降。

---

## 考核五：D1、D7 留存与 Cohort 成熟度

> **考核重点：** 注册日决定 Cohort，目标日决定留存，未成熟观察期不能记为 0%。

### 业务场景

> 截至 08-10 完整自然日，计算 08-01 注册 Cohort 的 D1 和 D7 exact-day 留存，并计算两个成熟 Cohort 的加权 D1 留存。

#### 用户行为

| 用户 | 注册日 | 08-02 有效活跃 | 08-08 有效活跃 |
| :---: | :---: | :---: | :---: |
| U1 | 08-01 | ✓ |  |
| U2 | 08-01 | ✓ | ✓ |
| U3 | 08-01 |  | ✓ |
| U4 | 08-01 |  |  |

#### 成熟 Cohort 汇总

| 注册日 | 新增用户 | D1 回来人数 | D1 留存率 |
| :---: | :---: | :---: | :---: |
| 08-01 | 4 | 2 | 50% |
| 08-02 | 1 | 1 | 100% |
| 08-10 | 5 | 未成熟 | 未成熟 |

### 评分任务

#### 1. 指标定义（20 分）

定义 exact-day D1、D7 留存，写明：

- Cohort 分组日期；
- 分子和分母；
- 目标行为；
- 观察期成熟条件。

#### 2. 手工计算（20 分）

计算：

- 08-01 Cohort 的 D1 和 D7；
- 08-01 与 08-02 两个成熟 Cohort 的加权 D1；
- 说明为什么不能直接平均 50% 和 100%。

#### 3. 查询实现（20 分）

写出查询或伪代码。要求先确定注册 Cohort 用户，再连接目标日期的有效事件，并保证目标日一个用户只计算一次。

#### 4. 结果核验（20 分）

至少检查：

- `retained_users <= cohort_size`；
- 留存率在 0%～100%；
- 未成熟 Cohort 返回空值或不展示，而不是 0%；
- D1 使用注册后第 1 个自然日，不是注册后任意时间回来。

#### 5. 业务解释（20 分）

首日创作者 D7 留存为 60%，只读用户为 20%，但创作者 Cohort 只有 5 人。写出合格的业务结论和下一步验证计划。

### 一票否决错误

- 把登录事件当成留存有效行为。
- 用目标日事件数代替留存用户数。
- 直接平均不同规模 Cohort 的留存率。
- 把尚未成熟的 D7 Cohort 当成 0% 留存。
- 把行为与留存的相关性解释为因果关系。

### 对应参考答案

#### A. 先固定 Cohort 和 exact-day 口径

- Cohort 由普通用户的注册自然日决定。
- D1 分子是注册后第 1 个自然日产生有效事件的 Cohort 用户数；D7 同理。
- 分母始终是该注册日的全部普通新增用户，不要求注册日已经激活。
- 每位用户在目标日无论产生多少事件都只计一次。
- 截止完整日尚未覆盖目标日期的 Cohort 不参与计算，也不记为 0%。

#### B. 先确定 Cohort，再连接目标日用户集合

```sql
WITH cohort_users AS (
    SELECT id AS user_id
    FROM auth_user
    WHERE date_joined >= TIMESTAMPTZ '2026-08-01 00:00:00+08'
      AND date_joined <  TIMESTAMPTZ '2026-08-02 00:00:00+08'
      AND is_staff = FALSE
      AND is_superuser = FALSE
),
d1_users AS (
    SELECT DISTINCT e.user_id
    FROM analytics_analyticsevent AS e
    JOIN auth_user AS u ON u.id = e.user_id
    WHERE e.occurred_at >= TIMESTAMPTZ '2026-08-02 00:00:00+08'
      AND e.occurred_at <  TIMESTAMPTZ '2026-08-03 00:00:00+08'
      AND u.is_staff = FALSE
      AND u.is_superuser = FALSE
      AND e.event_name IN (
          'page_view', 'board_view', 'post_view',
          'post_create', 'reply_create', 'post_like'
      )
),
d7_users AS (
    SELECT DISTINCT e.user_id
    FROM analytics_analyticsevent AS e
    JOIN auth_user AS u ON u.id = e.user_id
    WHERE e.occurred_at >= TIMESTAMPTZ '2026-08-08 00:00:00+08'
      AND e.occurred_at <  TIMESTAMPTZ '2026-08-09 00:00:00+08'
      AND u.is_staff = FALSE
      AND u.is_superuser = FALSE
      AND e.event_name IN (
          'page_view', 'board_view', 'post_view',
          'post_create', 'reply_create', 'post_like'
      )
)
SELECT
    c.user_id,
    CASE WHEN d1.user_id IS NULL THEN 0 ELSE 1 END AS retained_d1,
    CASE WHEN d7.user_id IS NULL THEN 0 ELSE 1 END AS retained_d7
FROM cohort_users AS c
LEFT JOIN d1_users AS d1 ON d1.user_id = c.user_id
LEFT JOIN d7_users AS d7 ON d7.user_id = c.user_id
ORDER BY c.user_id;
```

连接后的用户级结果如下，未回访用户仍留在分母中：

| Cohort 用户 | D1 目标日有效活跃 | D7 目标日有效活跃 |
| :---: | :---: | :---: |
| U1 | 1 | 0 |
| U2 | 1 | 1 |
| U3 | 0 | 1 |
| U4 | 0 | 0 |

#### C. 计算单个 Cohort 留存

```sql
WITH retention_flags AS (
    -- 此处使用上一段查询
    SELECT * FROM cohort_retention_flags
)
SELECT
    COUNT(*) AS cohort_size,
    SUM(retained_d1) AS d1_retained_users,
    ROUND(100.0 * SUM(retained_d1) / NULLIF(COUNT(*), 0), 2) AS d1_pct,
    SUM(retained_d7) AS d7_retained_users,
    ROUND(100.0 * SUM(retained_d7) / NULLIF(COUNT(*), 0), 2) AS d7_pct
FROM retention_flags;
```

| 指标 | 分子 | 分母 | 结果 |
| :---: | :---: | :---: | :---: |
| 08-01 D1 | U1、U2，共 2 人 | Cohort 4 人 | 50.00% |
| 08-01 D7 | U2、U3，共 2 人 | Cohort 4 人 | 50.00% |

#### D. 只汇总成熟 Cohort，并按人数加权

```sql
SELECT
    SUM(retained_users) AS retained_users,
    SUM(cohort_size) AS cohort_size,
    ROUND(
        100.0 * SUM(retained_users) / NULLIF(SUM(cohort_size), 0),
        2
    ) AS weighted_d1_pct
FROM analytics_retentioncohort
WHERE retention_day = 1
  AND cohort_date IN (DATE '2026-08-01', DATE '2026-08-02')
  AND cohort_date + 1 < DATE '2026-08-11';
```

加权结果是 `(2 + 1) / (4 + 1) = 60%`。直接平均 `(50% + 100%) / 2 = 75%`，等于让 1 人 Cohort 与 4 人 Cohort 拥有相同权重，会改变真实分母。

核验 SQL：

```sql
SELECT cohort_date, retention_day, cohort_size, retained_users
FROM analytics_retentioncohort
WHERE retained_users > cohort_size
   OR retention_rate < 0
   OR retention_rate > 100;
```

这条查询应返回 0 行。08-10 Cohort 的 D1 目标日是 08-11；若数据只完整到 08-10，它必须为空或不展示。

#### E. 业务解释

首日创作者 D7 为 60%、只读用户为 20%，只能说明“首日创作行为与后续回访呈正相关”。创作者只有 5 人，比例很容易因单个用户变化而大幅波动，不能据此宣称发帖导致留存提升。应同时展示 `retained_users/cohort_size`，合并更多成熟 Cohort，并按注册日期、来源和用户背景控制结构差异后再比较。

---

## 考核六：帖子回应质量

> **考核重点：** 先把回复汇总到每帖一行，再计算总体指标，零回复帖子不能从分母消失。

### 业务场景

> 以 08-10 新建帖子为 Cohort，观察截至 08-11 00:00，计算每帖回复数、零回复帖子率和首次回复时间中位数。

| 帖子 | 作者类型 | 发帖时间 | 合格回复时间 |
| :---: | :---: | :---: | :---: |
| P1 | 普通用户 | 08-10 09:00 | 11:00、14:00 |
| P2 | 普通用户 | 08-10 10:00 | 无 |
| P3 | 普通用户 | 08-10 11:00 | 08-11 13:00 |
| P4 | staff | 08-10 12:00 | 13:00 |

注意：P3 的回复发生在观察截止时间之后。

### 评分任务

#### 1. 指标定义（20 分）

分别定义：

- 每帖回复数；
- 零回复帖子率；
- 首次回复时间。

说明零回复帖子是否进入每帖回复数的分母，以及是否进入首次回复时间计算。

#### 2. 手工计算（20 分）

按顺序展示：

1. 过滤合格新帖；
2. 按观察截止时间过滤回复；
3. 将回复汇总到帖子粒度；
4. 计算三个指标。

#### 3. 查询实现（20 分）

写查询或伪代码，要求先将回复汇总为每帖一行，再计算最终指标。解释为什么直接把帖子表与回复表连接后 `COUNT(post_id)` 可能造成分母膨胀。

#### 4. 结果核验（20 分）

至少检查：

- 零回复帖子数不能大于帖子数；
- 每帖回复数不能为负；
- 首次回复时间不能早于发帖时间；
- P3 截止观察日仍应视为零回复。

#### 5. 业务解释（20 分）

零回复帖子率从 20% 上升至 45%，但每帖回复数保持不变。解释这种组合可能意味着什么，并提出至少三个下钻方向。

### 一票否决错误

- 只统计获得回复的帖子作为每帖回复数分母。
- 把观察窗口之后的回复计入结果。
- 对零回复帖强行设置首次回复时间为 0。
- 连接回复明细后直接数帖子行，造成一个帖子被重复计算。

### 对应参考答案

#### A. 先固定帖子 Cohort 和观察窗口

帖子 Cohort 是 08-10 由普通用户创建的帖子；回复只统计发帖之后、08-11 00:00 之前由普通用户创建的记录。每帖回复数和零回复帖子率的分母包含零回复帖；首次回复时间只对已获得回复的帖子计算，零回复帖保持 `NULL`。

#### B. 先过滤帖子，再把回复汇总到每帖一行

```sql
WITH eligible_posts AS (
    SELECT p.id AS post_id, p.created_at
    FROM forum_post AS p
    JOIN auth_user AS author ON author.id = p.author_id
    WHERE p.created_at >= TIMESTAMPTZ '2026-08-10 00:00:00+08'
      AND p.created_at <  TIMESTAMPTZ '2026-08-11 00:00:00+08'
      AND author.is_staff = FALSE
      AND author.is_superuser = FALSE
),
reply_by_post AS (
    SELECT
        p.post_id,
        p.created_at,
        COUNT(r.id) AS reply_count,
        MIN(r.created_at) AS first_reply_at
    FROM eligible_posts AS p
    LEFT JOIN forum_reply AS r
      ON r.post_id = p.post_id
     AND r.created_at >= p.created_at
     AND r.created_at < TIMESTAMPTZ '2026-08-11 00:00:00+08'
     AND EXISTS (
         SELECT 1
         FROM auth_user AS reply_author
         WHERE reply_author.id = r.author_id
           AND reply_author.is_staff = FALSE
           AND reply_author.is_superuser = FALSE
     )
    GROUP BY p.post_id, p.created_at
)
SELECT * FROM reply_by_post ORDER BY post_id;
```

关键点是把回复条件放在 `LEFT JOIN ... ON` 中。若写进外层 `WHERE`，P2、P3 这类零回复帖子会被过滤掉。

| 过滤阶段 | 保留内容 | 被排除内容 |
| :---: | :---: | :---: |
| 帖子 Cohort | P1、P2、P3 | P4：staff 发帖 |
| 截止时间内回复 | P1 的 2 条回复 | P3 的回复：发生在截止时间之后 |

每帖粒度汇总结果：

| 帖子 | 截止时回复数 | 首次回复时间 | 首次回复耗时 |
| :---: | :---: | :---: | :---: |
| P1 | 2 | 08-10 11:00 | 2 小时 |
| P2 | 0 | `NULL` | `NULL` |
| P3 | 0 | `NULL` | `NULL` |

#### C. 从帖子粒度计算最终指标

```sql
WITH reply_by_post AS (...)
SELECT
    COUNT(*) AS post_count,
    SUM(reply_count) AS reply_count,
    ROUND(1.0 * SUM(reply_count) / NULLIF(COUNT(*), 0), 2) AS replies_per_post,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE reply_count = 0)
        / NULLIF(COUNT(*), 0),
        2
    ) AS zero_reply_post_rate_pct,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (first_reply_at - created_at)) / 3600.0
    ) FILTER (WHERE first_reply_at IS NOT NULL) AS median_first_reply_hours,
    COUNT(*) FILTER (WHERE first_reply_at IS NOT NULL) AS first_reply_sample_size
FROM reply_by_post;
```

| 指标 | 分子 | 分母 | 结果 |
| :---: | :---: | :---: | :---: |
| 每帖回复数 | 2 条回复 | 3 篇合格帖子 | 0.67 |
| 零回复帖子率 | P2、P3，共 2 篇 | 3 篇合格帖子 | 66.67% |
| 首次回复时间中位数 | P1 的 2 小时 | 1 篇已回复帖子 | 2 小时 |

#### D. 用 SQL 检查不可能值

```sql
SELECT *
FROM reply_by_post
WHERE reply_count < 0
   OR first_reply_at < created_at;
```

该查询应返回 0 行。还应检查零回复帖数不大于帖子数、P3 在截止时仍是 0，以及首次回复样本量是否足以支持稳定结论。

#### E. 业务解释

零回复帖子率从 20% 升至 45%，但每帖回复数不变，可能表示回复集中到少数热门帖子：获得回复的帖子讨论更深，却有更多帖子完全没有回应。下一步应查看回复数分布、板块/主题、帖子曝光量、作者类型、发布时间和帖子观察时长，而不能仅凭平均数判断讨论质量不变。

---

## 考核七：板块级活跃与互动

> **考核重点：** 板块内独立去重；跨板块用户重叠，因此板块人数不能相加作为全站人数。

### 业务场景

> 比较技术交流和社区生活两个板块的活跃用户与互动情况。

窗口内用户行为：

| 用户 | 板块 | 行为 |
| :---: | :---: | :---: |
| U1 | 技术交流 | `post_view`、`reply_create` |
| U1 | 社区生活 | `post_view` |
| U2 | 技术交流 | `post_view`、`post_like` |
| U3 | 社区生活 | `post_view`、`reply_create` |
| U3 | 社区生活 | `post_like` |

### 评分任务

#### 1. 指标定义（20 分）

定义每个板块的：

- 活跃用户数；
- 浏览用户数；
- 互动用户数；
- 互动率；
- 回复和点赞动作数。

#### 2. 手工计算（20 分）

计算两个板块的全部指标，并计算全站去重活跃用户数。展示为什么不能把两个板块的活跃用户数直接相加作为全站活跃用户数。

#### 3. 查询实现（20 分）

写出按 `board_id` 聚合的查询。要求：

- 用户类指标按 `board_id + user_id` 去重；
- 动作类指标按事件计数；
- 不因为一个用户多种行为而重复计算板块活跃用户。

#### 4. 结果核验（20 分）

至少检查：

- 板块互动用户数不大于板块活跃用户数；
- 板块浏览用户数不大于板块活跃用户数；
- 板块用户数之和可以大于全站用户数；
- 抽查跨板块用户 U1 的归属。

#### 5. 业务解释（20 分）

技术交流浏览量更高，但互动率更低；社区生活浏览量较低，但互动率更高。给出业务解释，并说明不能只根据互动率决定资源投入。

### 一票否决错误

- 将板块活跃用户数求和作为全站 DAU。
- 用互动动作数除以活跃用户数并命名为互动用户率。
- 只比较百分比，不查看用户规模和绝对互动贡献。

### 对应参考答案

#### A. 先固定板块指标口径

板块活跃用户是在该板块产生有效事件的独立普通用户；浏览用户产生过 `post_view`；互动用户产生过 `reply_create` 或 `post_like`。互动率是互动用户数除以板块活跃用户数。回复数、点赞数是动作量，可以大于对应用户数。

#### B. 在 `board_id + user_id` 粒度生成行为标记

```sql
WITH eligible_events AS (
    SELECT e.board_id, e.user_id, e.event_name
    FROM analytics_analyticsevent AS e
    JOIN auth_user AS u ON u.id = e.user_id
    WHERE e.occurred_at >= :window_start
      AND e.occurred_at <  :window_end
      AND e.board_id IS NOT NULL
      AND u.is_staff = FALSE
      AND u.is_superuser = FALSE
      AND e.event_name IN (
          'page_view', 'board_view', 'post_view',
          'post_create', 'reply_create', 'post_like'
      )
),
board_user_flags AS (
    SELECT
        board_id,
        user_id,
        MAX(CASE WHEN event_name = 'post_view' THEN 1 ELSE 0 END) AS viewed,
        MAX(CASE WHEN event_name IN ('reply_create', 'post_like') THEN 1 ELSE 0 END) AS interacted,
        SUM(CASE WHEN event_name = 'reply_create' THEN 1 ELSE 0 END) AS replies,
        SUM(CASE WHEN event_name = 'post_like' THEN 1 ELSE 0 END) AS likes
    FROM eligible_events
    GROUP BY board_id, user_id
)
SELECT * FROM board_user_flags ORDER BY board_id, user_id;
```

中间层只保留板块、用户及行为标记：

| 板块 | 用户 | 活跃标记 | 浏览标记 | 互动标记 | 回复动作 | 点赞动作 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 技术交流 | U1 | 1 | 1 | 1 | 1 | 0 |
| 技术交流 | U2 | 1 | 1 | 1 | 0 | 1 |
| 社区生活 | U1 | 1 | 1 | 0 | 0 | 0 |
| 社区生活 | U3 | 1 | 1 | 1 | 1 | 1 |

#### C. 聚合成板块级指标

```sql
WITH board_user_flags AS (...)
SELECT
    board_id,
    COUNT(*) AS active_users,
    SUM(viewed) AS post_view_users,
    SUM(interacted) AS interaction_users,
    SUM(replies) AS replies_created,
    SUM(likes) AS likes_created,
    ROUND(100.0 * SUM(interacted) / NULLIF(COUNT(*), 0), 2) AS interaction_rate_pct
FROM board_user_flags
GROUP BY board_id
ORDER BY board_id;
```

| 板块 | 活跃用户 | 浏览用户 | 互动用户 | 互动率 | 回复动作 | 点赞动作 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 技术交流 | 2 | 2 | 2 | 100.00% | 1 | 1 |
| 社区生活 | 2 | 2 | 1 | 50.00% | 1 | 1 |

全站人数必须脱离板块分组重新去重：

```sql
WITH eligible_events AS (...)
SELECT COUNT(DISTINCT user_id) AS sitewide_active_users
FROM eligible_events;
```

结果为 U1、U2、U3，共 3 人。两个板块的活跃用户数之和是 4，因为跨板块用户 U1 被各板块分别计数一次。

#### D. 用 SQL 核验分组与总体关系

```sql
SELECT *
FROM board_metrics_result
WHERE interaction_users > active_users
   OR post_view_users > active_users;
```

该查询应返回 0 行。需要注意，“板块活跃用户数之和大于全站活跃用户数”本身不是错误；它反映用户可同时属于多个板块。

#### E. 业务解释

某板块浏览量高但互动率低，可能承担知识查询和内容消费功能；另一个板块浏览量低但互动率高，可能拥有规模较小但更紧密的用户群。资源投入不能只看百分比，还应同时比较活跃用户规模、绝对互动人数、内容供给、样本量和战略定位，并继续下钻高浏览低互动的具体帖子。

---

## 综合评分与能力等级

### 单项评分

| 得分 | 结论 |
| :---: | :---: |
| 90～100 | 能独立交付，并能主动说明口径边界 |
| 80～89 | 基本工作可用，仍需改进核验或业务解释 |
| 60～79 | 会计算，但不足以独立用于业务决策 |
| 0～59 | 对过滤、去重、分母或时间窗口仍有明显误解 |

### 全局一票否决错误

出现以下任一错误，即使得分达到 80，也暂不判定为掌握：

1. 用事件数代替独立用户数。
2. 把每天独立用户数求和作为跨日独立用户数。
3. 没有定义分母或在查询中丢失零行为分母用户。
4. 混合匿名身份和登录身份，却没有说明连接与去重方法。
5. 把 staff、superuser 或测试账号当成真实业务用户。
6. 使用未完结自然日与完整历史日直接比较。
7. 将未成熟留存 Cohort 记为 0%。
8. 把行为与留存的相关性解释为因果关系。
9. 只给最终数字，无法展示过滤、连接、聚合和去重过程。

### 推荐学习顺序

```text
DAU
→ WAU / MAU
→ 新增激活率
→ 发帖、回复、点赞参与
→ 匿名注册转化
→ D1 / D7 留存
→ 帖子回应质量
→ 板块级分析
```

达到以下标准，可以认为具备论坛基础指标的工作能力：

- DAU、WAU/MAU、新增激活率和留存四项均达到 80 分；
- 其余题目至少选择两项达到 80 分；
- 没有一票否决错误；
- 能在不查看参考答案的情况下解释每项结果的证据边界。
