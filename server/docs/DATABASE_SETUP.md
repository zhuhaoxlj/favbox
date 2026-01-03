# 数据库设置指南

## 快速开始

### 1. 安装PostgreSQL

#### macOS (使用Homebrew)
\`\`\`bash
brew install postgresql@15
brew services start postgresql@15
\`\`\`

#### Ubuntu/Debian
\`\`\`bash
sudo apt update
sudo apt install postgresql-15 postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
\`\`\`

#### Docker (推荐用于开发)
\`\`\`bash
docker run --name favbox-postgres \\
  -e POSTGRES_PASSWORD=your_password \\
  -e POSTGRES_DB=favbox_crdt \\
  -p 5432:5432 \\
  -d postgres:15-alpine
\`\`\`

### 2. 创建数据库和用户

\`\`\`bash
# 连接到PostgreSQL
psql -U postgres

# 在psql中执行
CREATE DATABASE favbox_crdt;
CREATE USER favbox WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE favbox_crdt TO favbox;
\\q
\`\`\`

### 3. 配置环境变量

编辑`server/.env`文件:

\`\`\`env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=favbox_crdt
DB_USER=favbox
DB_PASSWORD=your_password
\`\`\`

### 4. 运行迁移脚本

\`\`\`bash
cd server
npm run migrate
\`\`\`

### 5. 验证安装

\`\`\`bash
# 连接到数据库
psql -U favbox -d favbox_crdt

# 查看表列表
\\dt

# 应该看到:
#  users
#  devices
#  crdt_operations
#  crdt_snapshots
#  bookmark_index
#  sync_state
#  sessions
#  system_info
\`\`\`

## Redis设置

### 安装Redis

#### macOS
\`\`\`bash
brew install redis
brew services start redis
\`\`\`

#### Ubuntu/Debian
\`\`\`bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
\`\`\`

#### Docker
\`\`\`bash
docker run --name favbox-redis \\
  -p 6379:6379 \\
  -d redis:7-alpine
\`\`\`

### 测试Redis连接

\`\`\`bash
redis-cli ping
# 应该返回: PONG
\`\`\`

## 常见问题

### Q: PostgreSQL连接失败
**A**: 检查以��内容:
1. PostgreSQL服务是否运行: `systemctl status postgresql`
2. 端口5432是否监听: `sudo lsof -i :5432`
3. .env文件配置是否正确
4. 用户权限是否足够

### Q: 迁移失败
**A**:
1. 删除所有表后重新运行迁移
2. 检查PostgreSQL版本(需要15+)
3. 查看详细错误日志

### Q: Redis连接失败
**A**:
1. 检查Redis服务: `systemctl status redis`
2. 检查端口6379: `sudo lsof -i :6379`
3. 尝试手动连接: `redis-cli ping`

## 生产环境建议

### PostgreSQL优化

1. **连接池配置**
\`\`\`javascript
// config.js
database: {
  max: 20, // 最大连接数
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
}
\`\`\`

2. **定期维护**
\`\`\`sql
-- 清理过期会话
SELECT cleanup_expired_sessions();

-- 分析表(优化查询)
ANALYZE users;
ANALYZE crdt_operations;
ANALYZE bookmark_index;
\`\`\`

3. **备份策略**
\`\`\`bash
# 每日备份
pg_dump favbox_crdt > backup_$(date +%Y%m%d).sql

# 恢复备份
psql favbox_crdt < backup_20250127.sql
\`\`\`

### Redis优化

1. **持久化配置**
\`\`\`conf
# redis.conf
save 900 1
save 300 10
save 60 10000
appendonly yes
\`\`\`

2. **内存限制**
\`\`\`conf
maxmemory 2gb
maxmemory-policy allkeys-lru
\`\`\`

## 监控

### PostgreSQL监控

\`\`\`sql
-- 查看活跃连接
SELECT * FROM pg_stat_activity;

-- 查看数据库大小
SELECT pg_size_pretty(pg_database_size('favbox_crdt'));

-- 查看表大小
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
\`\`\`

### Redis监控

\`\`\`bash
# 查看信息
redis-cli info

# 查看内存使用
redis-cli info memory

# 查看连接数
redis-cli info clients
\`\`\`
