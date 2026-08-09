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

指标生成是幂等的，可以安全重复执行。原始事件保存在 `analytics_analyticsevent`，用户日汇总、产品日指标和留存同期群分别保存在 `analytics_useractivitydaily`、`analytics_productmetricsdaily` 和 `analytics_retentioncohort`。

## React 开发

启动 Django 后，在另一个终端运行：

```bash
cd frontend
npm run dev
```

Vite 会将论坛 `/api` 请求代理给 Django。行为事件接口使用 `/analytics/api/events/`；本地开发时也应通过相同 Django 源访问，或在 Vite 代理中增加 `/analytics` 路径。
