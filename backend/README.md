# FavBox Backend

FavBox 浏览器插件的 Python 后端服务，提供书签同步、数据分析和协作共享功能。

## 功能特性

- **用户认证**: 注册/登录，JWT Token 认证
- **书签同步**: 全量同步、增量同步、实时 WebSocket 推送
- **数据分析**: 域名分布、标签云、时间趋势、重复检测
- **协作共享**: 书签集合、分享链接、权限管理

## 技术栈

- **框架**: FastAPI
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **ORM**: SQLAlchemy 2.0
- **认证**: JWT (python-jose)
- **实时通信**: WebSocket

## 快速开始

### 1. 安装依赖

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件，设置 SECRET_KEY
```

### 3. 启动服务

```bash
# 开发模式
python -m app.main

# 或使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问 API 文档

打开浏览器访问: http://localhost:8000/docs

## API 端点

### 认证

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | /api/auth/register | 注册新用户 |
| POST | /api/auth/login | 登录获取 Token |
| GET | /api/auth/me | 获取当前用户信息 |

### 书签同步

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | /api/bookmarks | 获取所有书签 |
| POST | /api/bookmarks/sync | 全量同步 |
| POST | /api/bookmarks/sync/incremental | 增量同步 |
| GET | /api/bookmarks/changes?since= | 获取变更 |
| WS | /api/ws?token= | WebSocket 实时连接 |

### 数据分析

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | /api/analytics/overview | 总览统计 |
| GET | /api/analytics/domains | 域名分布 |
| GET | /api/analytics/tags | 标签统计 |
| GET | /api/analytics/timeline | 时间趋势 |
| GET | /api/analytics/duplicates | 重复检测 |

### 协作共享

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | /api/collections | 获取我的集合 |
| POST | /api/collections | 创建集合 |
| GET | /api/collections/shared | 获取共享集合 |
| POST | /api/collections/{id}/share | 分享集合 |

## 配置说明

| 变量 | 默认值 | 描述 |
|------|--------|------|
| DATABASE_URL | sqlite+aiosqlite:///./favbox.db | 数据库连接字符串 |
| SECRET_KEY | - | JWT 密钥 (生产环境必须修改) |
| ACCESS_TOKEN_EXPIRE_MINUTES | 10080 | Token 有效期 (分钟) |
| CORS_ORIGINS | chrome-extension://,moz-extension:// | 允许的跨域来源 |

## 生产部署

### 使用 PostgreSQL

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/favbox
```

### 使用 Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app app/
COPY alembic alembic/
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 使用 systemd

```ini
[Unit]
Description=FavBox Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/favbox/backend
Environment="PATH=/opt/favbox/backend/venv/bin"
ExecStart=/opt/favbox/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx 反向代理

```nginx
server {
    listen 443 ssl http2;
    server_name favbox.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 开发说明

### 项目结构

```
backend/
├── app/
│   ├── main.py           # FastAPI 入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── models/           # 数据库模型
│   ├── schemas/          # Pydantic 模式
│   ├── api/              # API 路由
│   └── utils/            # 工具函数
├── alembic/              # 数据库迁移
├── requirements.txt
└── .env.example
```

### 同步策略

- **全量同步**: 客户端上传所有书签，服务器合并并返回最终状态
- **增量同步**: 仅同步变更，支持创建、更新、删除操作
- **冲突解决**: Last-Write-Wins (基于 updated_at 时间戳)
- **实时推送**: WebSocket 广播变更到用户的所有设备

## License

MIT
