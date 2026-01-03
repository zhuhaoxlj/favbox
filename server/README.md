# FavBox CRDT同步服务器

基于Fastify + PostgreSQL + Redis + Automerge的书签同步后端服务。

## 功能特性

- ✅ JWT身份认证
- ✅ CRDT操作日志存储
- ✅ 快照管理
- ✅ WebSocket实时同步
- ✅ RESTful API
- ✅ Redis缓存加速

## 技术栈

- **框架**: Fastify 4.x
- **数据库**: PostgreSQL 15+
- **缓存**: Redis 7+
- **CRDT**: Automerge 2.x
- **认证**: JWT + bcrypt

## 快速开始

### 1. 安装依赖

\`\`\`bash
cd server
npm install
\`\`\`

### 2. 配置环境变量

复制`.env.example`为`.env`并修改配置:

\`\`\`bash
cp .env.example .env
# 编辑.env文件,设置数据库和Redis连接信息
\`\`\`

### 3. 初始化数据库

\`\`\`bash
# 创建数据库
createdb favbox_crdt

# 运行迁移脚本
npm run migrate
\`\`\`

### 4. 启动服务器

\`\`\`bash
# 开发模式(热重载)
npm run dev

# 生产模式
npm start
\`\`\`

服务器将在 http://localhost:3000 启动

### 5. 健康检查

访问 http://localhost:3000/health 检查服务状态

## API文档

### 认证接口

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/me` - 获取当前用户信息

### 同步接口

- `GET /api/sync/snapshot` - 获取CRDT快照
- `GET /api/sync/operations` - 获取增量操作
- `POST /api/sync/operations` - 上传操作

### WebSocket

- `WS /ws` - 实时同步连接

详细API文档请查看: [API.md](./docs/API.md)

## 项目结构

\`\`\`
server/
├── src/
│   ├── index.js           # 入口文件
│   ├── config.js          # 配置管理
│   ├── db.js              # 数据库连接
│   ├── redis.js           # Redis客户端
│   ├── routes/            # 路由目录
│   ├── services/          # 业务逻辑
│   └── middleware/        # 中间件
├── migrations/            # 数据库迁移
├── package.json
└── .env.example
\`\`\`

## 开发指南

### 添加新的API路由

1. 在`src/routes/`目录创建路由文件
2. 在`src/index.js`中注册路由
3. 实现对应的service逻辑

### 数据库迁移

\`\`\`bash
# 创建新迁移
npm run migrate:create <migration_name>

# 运行迁移
npm run migrate
\`\`\`

## 部署

### Docker部署

\`\`\`bash
# 构建镜像
docker build -t favbox-server .

# 运行容器
docker run -p 3000:3000 --env-file .env favbox-server
\`\`\`

### PM2部署

\`\`\`bash
# 安装PM2
npm install -g pm2

# 启动服务
pm2 start src/index.js --name favbox-server

# 查看日志
pm2 logs favbox-server
\`\`\`

## 监控与日志

- 使用Pino进行结构化日志记录
- 开发环境启用pretty-print
- 生产环境输出JSON格式日志

## 安全性

- ✅ JWT token认证
- ✅ bcrypt密码加密
- ✅ SQL注入防护(参数化查询)
- ✅ CORS配置
- ✅ 速率限制 (TODO)

## 性能优化

- ✅ PostgreSQL连接池
- ✅ Redis缓存
- ✅ CRDT增量同步
- ✅ 快照策略
- ✅ 批量操作优化

## 测试

\`\`\`bash
# 运行单元测试
npm test

# 运行集成测试
npm run test:integration

# 测试覆盖率
npm run test:coverage
\`\`\`

## License

MIT

## 相关链接

- [Fastify文档](https://www.fastify.io/)
- [Automerge文档](https://automerge.org/)
- [PostgreSQL文档](https://www.postgresql.org/docs/)
