# Django + React 简易论坛

一个带轻量数据仓库和管理员指标后台的论坛演示项目。

## 功能

- React 单页论坛：板块、帖子、回复、点赞
- Django JSON API、会话认证与 Admin
- 行为事件采集：页面、板块、帖子浏览及服务端业务事件
- 用户日活、WAU、MAU、新增用户、内容互动和 D1/D7/D30 留存
- 仅管理员可访问的独立指标页面 `/analytics/`
- SQLite 本地回退与 PostgreSQL 正式环境配置

## 本地运行

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
cd frontend && npm install && npm run build && cd ..
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

访问地址：

- 论坛：`http://127.0.0.1:8000/`
- Django Admin：`http://127.0.0.1:8000/admin/`
- 数据指标后台：`http://127.0.0.1:8000/analytics/`

指标后台要求登录 `is_staff=True` 的管理员账号。点击“重新生成指标”可生成最近 7、30 或 90 天的数据。

## 生成论坛演示数据

项目提供确定性数据生成命令，用于学习和验证 DAU、WAU、MAU、内容消费漏斗、发帖/回复/点赞、用户行为分层及 D1/D7/D30 留存：

```bash
.venv/bin/python manage.py seed_demo_data
```

默认生成截至昨天的 60 天数据和 180 个演示用户，并自动重算全部日指标与留存。演示数据包括：

- `reader`、`liker`、`discusser`、`creator` 四类行为分布；
- 登录用户及匿名用户的页面、板块和帖子浏览；
- 与业务表一致的帖子、回复、点赞和取消点赞事件；
- 跨 60 天注册 Cohort，支持 D1、D7、D30 留存；
- 可复现的随机种子，便于重复学习和测试。

自定义规模：

```bash
.venv/bin/python manage.py seed_demo_data --days 90 --users 300 --seed 20260810
```

此前已生成过演示数据时，需要明确使用 `--reset`：

```bash
.venv/bin/python manage.py seed_demo_data --reset
```

`--reset` 只删除用户名以 `demo_` 开头且由生成器标记的演示数据，不删除普通用户内容。所有演示用户使用密码 `DemoForum2026!`；这些账号不是工作人员，不能访问指标后台。

## PostgreSQL

启动数据库：

```bash
docker compose up -d postgres
```

将 `.env.example` 中的变量导入运行环境后执行迁移。只要设置了 `POSTGRES_DB`，Django 就会使用 PostgreSQL；未设置时使用 SQLite。

## 指标生成

默认生成昨天：

```bash
.venv/bin/python manage.py generate_metrics
```

生成指定日期或日期范围：

```bash
.venv/bin/python manage.py generate_metrics --date 2026-08-09
.venv/bin/python manage.py generate_metrics --start 2026-08-01 --end 2026-08-09
```

生产环境可通过 cron 每天凌晨运行：

```cron
10 1 * * * /path/to/project/.venv/bin/python /path/to/project/manage.py generate_metrics
```

指标生成是幂等的，可以安全重复执行。原始事件保存在 `analytics_analyticsevent`；用户日、产品日、板块日、整体留存和首日行为留存分别保存在 `analytics_useractivitydaily`、`analytics_productmetricsdaily`、`analytics_boardmetricsdaily`、`analytics_retentioncohort` 和 `analytics_behaviorretentioncohort`。

## 学习文档

- [论坛常见指标能力评估手册（Markdown）](docs/forum-metrics-assessment-guide.md)：使用 GFM 表格，适合在 GitHub 和支持 GFM 的编辑器中阅读、修改。
- [论坛常见指标能力评估手册（PDF）](output/pdf/forum-metrics-assessment-guide.pdf)：固定表格边界、全单元格居中，适合稳定查看和打印，不受 Markdown 渲染器影响。
- [analytics/services.py 数据转换学习笔记](docs/analytics-services-study-notes.md)：逐步理解事件如何生成用户日和产品日汇总。

重新生成 PDF：

```bash
.venv/bin/python -m pip install -r requirements-docs.txt
.venv/bin/python scripts/render_assessment_pdf.py
```

## React 开发

启动 Django 后，在另一个终端运行：

```bash
cd frontend
npm run dev
```

Vite 会将论坛 `/api` 请求代理给 Django。行为事件接口使用 `/analytics/api/events/`；本地开发时也应通过相同 Django 源访问，或在 Vite 代理中增加 `/analytics` 路径。
