# Django 简易论坛

一个使用 Django、SQLite 和服务端模板实现的演示论坛，功能包括：

- 帖子板块
- 发帖、浏览帖子和回复
- 登录用户点赞/取消点赞
- Django Admin 后台管理板块、帖子和回复

## 运行

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

访问 `http://127.0.0.1:8000/`。先在 `http://127.0.0.1:8000/admin/` 创建板块和用户，然后即可登录发帖。
