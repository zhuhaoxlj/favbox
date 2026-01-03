# FavBox AI分类与语义搜索系统 - 部署指南

## 🎉 系统概述

已完成以下核心功能开发：

### ✅ 数据库层
- PostgreSQL 16 + pgvector扩展
- 768维向量支持（Gemini Embeddings）
- 全文搜索支持（PostgreSQL TSVector）
- 层级分类表结构

### ✅ AI服务
- Gemini向量化服务（单个/批量）
- AI智能分类引擎
- 语义相似度搜索

### ✅ API端点
- `/api/categories` - 分类管理
- `/api/search/semantic` - 语义搜索
- `/api/search/similar/{id}` - 相似书签
- `/api/search/embeddings/stats` - 向量化统计

### ✅ 工具脚本
- SQLite → PostgreSQL迁移脚本
- 批量向量化脚本
- 默认分类初始化

---

## 🚀 快速开始

### 步骤 1: 启动PostgreSQL

```bash
# 在项目根目录
cd /home/ts/100-Project/23-HTML/favbox

# 启动Docker容器
docker-compose up -d

# 验证PostgreSQL运行
docker ps | grep favbox-postgres

# 查看日志（如有问题）
docker-compose logs postgres
```

**预期输出：**
```
favbox-postgres   ... Up
```

---

### 步骤 2: 更新环境变量

编辑 `backend/.env`：

```bash
# 切换到PostgreSQL
DATABASE_URL=postgresql+asyncpg://favbox:favbox_secure_password_change_in_production@localhost:5432/favbox

# 确保Gemini API Key已设置
GEMINI_API_KEY=your-actual-api-key-here
```

⚠️ **重要**: 将 `your-actual-api-key-here` 替换为您的真实Gemini API密钥！

---

### 步骤 3: 安装依赖

```bash
cd backend

# 使用uv安装（推荐）
uv sync

# 或使用pip
pip install -r requirements.txt

# 确保pgvector库已安装
pip show pgvector
```

**预期输出:**
```
Name: pgvector
Version: 0.x.x
...
```

---

### 步骤 4: 测试PostgreSQL连接

```bash
cd backend

# 测试连接
python -c "
import asyncio
from app.scripts.migrate_to_postgres import check_postgres_connection
asyncio.run(check_postgres_connection())
"
```

**预期输出:**
```
✅ PostgreSQL is running!
   Version: PostgreSQL 16.x...
✅ pgvector extension is installed!
```

---

### 步骤 5: 初始化数据库

```bash
# 启动后端（会自动创建表结构）
cd backend
python -m app.main
```

**预期输出:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ 表结构已创建，按 `Ctrl+C` 停止服务器。

---

### 步骤 6: 运行数据迁移（从SQLite）

```bash
cd backend

# 1. 检查SQLite数据
python -c "
import sqlite3
conn = sqlite3.connect('./favbox.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM bookmarks')
print(f'SQLite书签数: {cursor.fetchone()[0]}')
conn.close()
"

# 2. 执行迁移（脚本会自动备份SQLite）
python -m app.scripts.migrate_to_postgres --migrate
```

**预期输出:**
```
🚀 Starting migration from SQLite to PostgreSQL...
✅ SQLite database backed up to: ./favbox_backup_YYYYMMDD_HHMMSS.db
✅ Connected to both databases
📊 Migrating users...
   Found X users
📊 Migrating bookmarks...
   Found XXXX bookmarks
✅ Migration completed!
```

---

### 步骤 7: 初始化默认分类

首次登录后，系统会自动创建5个默认分类：

- 💻 **技术** - 编程、开发、框架
- 🎨 **设计** - UI/UX、Figma、原型
- 🎮 **Switch游戏资源** - Nintendo、eShop
- 📚 **图书下载资源** - 电子书、PDF
- ✍️ **Blog** - 博客、文章

**API调用示例：**
```bash
curl -X POST http://localhost:8000/api/categories/initialize \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 步骤 8: 批量向量化书签

这是最耗时的步骤（5000书签约需2-3小时）：

```bash
cd backend

# 获取您的用户ID（通过API或数据库）
# 假设用户ID为1

# 开始批量处理（包含向量化+AI分类）
python -m app.scripts.batch_embed \
  --user-id 1 \
  --batch-size 100 \
  --overwrite  # 如果要重新处理已有向量

# 仅向量化，不分类
python -m app.scripts.batch_embed \
  --user-id 1 \
  --no-classify
```

**预期输出：**
```
🚀 Starting batch embedding for user 1
   Batch size: 100
   Overwrite: False
   Also classify: True
✅ Services initialized
📊 Found 5234 bookmarks to process
📁 Found 5 categories

📦 Processing batch 1/53 (100 bookmarks)
   🔄 Generating embeddings...
   🤖 Classifying bookmarks...
   💾 Updating bookmarks...
   Progress: 1.9%
   Success: 100, Failed: 0, Skipped: 0

...

============================================================
✅ Batch embedding completed!
   Total: 5234
   Processed: 5234
   Success: 5234
   Failed: 0
   Skipped: 0
   Duration: 7234.5s (120.6 minutes)
   Average: 1.38s per bookmark
============================================================
```

💡 **提示**: 可以中断（Ctrl+C）后重新运行，脚本会跳过已处理的。

---

### 步骤 9: 验证功能

#### 9.1 检查向量化统计

```bash
curl http://localhost:8000/api/search/embeddings/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**预期响应：**
```json
{
  "total_bookmarks": 5234,
  "embedded_bookmarks": 5234,
  "classified_bookmarks": 5234,
  "embedding_rate": "100.0%",
  "classification_rate": "100.0%"
}
```

#### 9.2 测试语义搜索

```bash
curl -X POST http://localhost:8000/api/search/semantic \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Vue.js教程",
    "min_similarity": 0.6,
    "limit": 10
  }'
```

**预期响应：**
```json
{
  "query": "Vue.js教程",
  "results": [
    {
      "id": 123,
      "title": "Vue 3 完全指南",
      "url": "https://vuejs.org/tutorial",
      "similarity": 0.8934,
      "category": {
        "id": 1,
        "name": "技术",
        "icon": "💻"
      }
    }
  ],
  "total": 10,
  "query_time_ms": 45.23
}
```

#### 9.3 测试分类管理

```bash
# 获取所有分类
curl http://localhost:8000/api/categories \
  -H "Authorization: Bearer YOUR_TOKEN"

# 创建新分类
curl -X POST http://localhost:8000/api/categories \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI工具",
    "description": "人工智能相关工具",
    "color": "#8B5CF6",
    "icon": "🤖",
    "keywords": ["AI", "ChatGPT", "机器学习"]
  }'
```

---

## 📊 API端点总览

### 分类管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/categories` | GET | 获取分类树 |
| `/api/categories` | POST | 创建分类 |
| `/api/categories/{id}` | PUT | 更新分类 |
| `/api/categories/{id}` | DELETE | 删除分类 |
| `/api/categories/initialize` | POST | 初始化默认分类 |
| `/api/categories/reset` | POST | 重置所有分类 |
| `/api/categories/stats` | GET | 分类统计 |

### 语义搜索

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/search/semantic` | POST | 自然语言搜索 |
| `/api/search/similar/{id}` | GET | 查找相似书签 |
| `/api/search/embeddings/stats` | GET | 向量化统计 |
| `/api/search/embeddings/batch` | POST | 批量向量化（需后台任务队列） |

---

## 🔧 故障排查

### 问题1: PostgreSQL连接失败

**错误信息：**
```
❌ Cannot connect to PostgreSQL: connection refused
```

**解决方案：**
```bash
# 检查容器状态
docker ps -a | grep favbox-postgres

# 重启容器
docker-compose restart postgres

# 查看日志
docker-compose logs postgres
```

---

### 问题2: pgvector扩展未安装

**错误信息：**
```
⚠️  pgvector extension NOT found
```

**解决方案：**
```bash
# 进入容器
docker exec -it favbox-postgres psql -U favbox -d favbox

# 创建扩展
CREATE EXTENSION IF NOT EXISTS vector;

# 退出
\q
```

---

### 问题3: 向量化失败

**错误信息：**
```
❌ Failed to generate embedding: API key not valid
```

**解决方案：**
1. 检查 `backend/.env` 中的 `GEMINI_API_KEY`
2. 验证API密钥是否有效：
   ```bash
   curl http://localhost:8000/api/ai/test-api-key
   ```

---

### 问题4: 速度太慢

**优化建议：**
1. **调整批次大小**：`--batch-size 50`（降低并发）
2. **仅向量化**：使用 `--no-classify` 跳过AI分类
3. **分批处理**：先处理最近30天，再处理更早的

---

## 💰 成本估算

### Gemini API使用（5000书签）

- **向量化**：$3-5（一次性）
- **分类**：$0.5-1（一次性）
- **日常搜索**：$0（本地向量搜索，无API调用）
- **后续新增**：$0.1/100书签

### PostgreSQL托管

- **自托管Docker**：$0/月
- **存储**：约100MB（5000书签）

---

## 🎯 下一步

### 核心功能已就绪
✅ 数据库迁移
✅ AI分类系统
✅ 语义搜索
✅ 分类管理API

### 可选增强功能
- [ ] 混合搜索（向量+关键词）
- [ ] 前端分类管理界面
- [ ] 实时搜索建议
- [ ] 搜索历史记录
- [ ] 批量编辑分类

---

## 📞 支持

如有问题，请查看：
- 项目计划：`.claude/plan/AI分类与语义搜索系统.md`
- API文档：启动后访问 `http://localhost:8000/docs`
- 日志：`backend/logs/`（如有配置）

祝您使用愉快！🎉
