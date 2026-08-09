# Django 简易论坛

一个使用 React、Django 和 SQLite 实现的演示论坛。React 提供单页前端，Django 提供 JSON API、会话认证和 Admin 后台。

- 帖子板块
- 发帖、浏览帖子和回复
- 登录用户点赞/取消点赞
- Django Admin 后台管理板块、帖子和回复

## 运行

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
cd frontend && npm install && npm run build && cd ..
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

访问 `http://127.0.0.1:8000/`。先在 `http://127.0.0.1:8000/admin/` 创建板块和用户，然后即可登录发帖。

## 前端开发

启动 Django 后，在另一个终端运行 `cd frontend && npm run dev`。Vite 开发服务器会将 `/api` 请求代理给 Django。
