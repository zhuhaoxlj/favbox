# FavBox AI功能使用指南

本文档介绍如何使用FavBox新增的AI打标签、备份管理和语义化搜索功能。

## 功能概览

### 1. 🔄 备份管理
在AI处理前自动或手动创建书签备份，支持一键还原。

### 2. 🤖 AI批量打标签
指定时间范围，让AI为书签自动生成标签和分类。

### 3. 🔍 语义化搜索
基于向量嵌入的智能搜索，理解查询的语义含义。

---

## 安装步骤

### 后端配置

1. **更新环境变量**

在 `backend/.env` 文件中添加Google Gemini API密钥：

```env
# AI Services
GEMINI_API_KEY=your-gemini-api-key-here
```

2. **安装新依赖**

```bash
cd backend
pip install httpx numpy
```

3. **运行后端**

```bash
cd backend
python -m app.main
```

### 前端配置

前端组件已创建，无需额外配置。

---

## 功能使用说明

### 1. 备份管理

**组件位置**：`src/ext/browser/components/BackupManager.vue`

**功能**：
- 创建书签快照备份
- 查看备份历史
- 删除备份
- 完全还原或合并还原

**API端点**：
- `POST /api/backups` - 创建备份
- `GET /api/backups` - 获取备份列表
- `DELETE /api/backups/{id}` - 删除备份
- `POST /api/backups/restore` - 还原备份

**使用示例**：

```javascript
import backendService from '@/services/backend.js';

// 创建备份
await backendService.createBackup({
  name: 'AI处理前备份',
  description: '2025年1月3日创建'
});

// 获取备份列表
const backups = await backendService.getBackups();

// 还原备份（完全覆盖）
await backendService.restoreBackup({
  backup_id: 1,
  merge_mode: false
});
```

---

### 2. AI批量打标签

**组件位置**：`src/ext/browser/components/AITagBatchProcessor.vue`

**功能**：
- 指定时间范围（7天、30天、90天等）
- 设置最大标签数
- 覆盖或新增标签
- 处理前自动备份

**API端点**：
- `POST /api/ai/batch-tag` - 批量打标签
- `POST /api/ai/suggest-tags` - 为单个书签建议标签
- `GET /api/ai/stats` - 获取AI处理统计

**使用示例**：

```javascript
// 批量处理最近30天的书签
const result = await backendService.batchTagBookmarks({
  days: 30,
  max_tags: 5,
  overwrite: false,
  create_backup: true
});

console.log(`处理了 ${result.processed} 个书签`);
console.log(`成功: ${result.success}, 失败: ${result.failed}`);
```

**处理流程**：
1. 如果设置了`create_backup`，先创建备份
2. 查找指定时间范围内的书签
3. 如果`overwrite=false`，只处理没有标签的书签
4. 调用AI API生成标签
5. 更新书签的`tags`和`ai_tags`字段
6. 返回处理结果

---

### 3. 语义化搜索

**组件位置**：`src/ext/browser/components/SemanticSearch.vue`

**功能**：
- 输入自然语言查询
- 调整相似度阈值
- 生成向量嵌入
- 查看搜索结果及相似度评分

**API端点**：
- `POST /api/search/semantic` - 执行语义搜索
- `POST /api/search/generate-embeddings` - 生成向量嵌入
- `GET /api/search/embedding-stats` - 获取嵌入统计

**使用示例**：

```javascript
// 执行语义搜索
const results = await backendService.semanticSearch({
  query: '前端框架',
  min_similarity: 0.5,
  limit: 20
});

results.forEach(item => {
  console.log(`${item.bookmark.title} - 相似度: ${item.similarity}`);
});

// 生成向量嵌入
await backendService.generateEmbeddings({
  days: 30,
  overwrite: false
});
```

**工作原理**：
1. 将查询文本转换为向量嵌入
2. 计算查询与已有书签嵌入的余弦相似度
3. 返回相似度超过阈值的结果
4. 按相似度排序

---

## 数据模型扩展

### Bookmark表新增字段

```python
# AI related fields
ai_tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
ai_tags_confidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
ai_category_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
ai_embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Vector embedding
last_ai_analysis_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

### BookmarkBackup表

```python
class BookmarkBackup(Base):
    id: int
    user_id: int
    name: str
    description: str
    snapshot_data: dict  # JSON snapshot of all bookmarks
    total_bookmarks: int
    bookmarks_with_tags: int
    created_at: datetime
```

---

## 数据库迁移

运行后端时，SQLAlchemy会自动创建新表和字段。如果已有数据库，建议运行迁移：

```bash
# 方案1：删除数据库重新创建（开发环境）
rm backend/favbox.db
python -m app.main

# 方案2：使用Alembic迁移（生产环境）
cd backend
alembic revision --autogenerate -m "Add AI fields"
alembic upgrade head
```

---

## 前端集成

### 在现有视图中使用组件

```vue
<template>
  <div>
    <button @click="showBackupManager = true">备份管理</button>
    <button @click="showAITagger = true">AI打标签</button>
    <button @click="showSemanticSearch = true">语义搜索</button>
    
    <BackupManager v-if="showBackupManager" @close="showBackupManager = false" />
    <AITagBatchProcessor v-if="showAITagger" @close="showAITagger = false" />
    <SemanticSearch v-if="showSemanticSearch" @close="showSemanticSearch = false" />
  </div>
</template>

<script>
import BackupManager from '@/components/BackupManager.vue';
import AITagBatchProcessor from '@/components/AITagBatchProcessor.vue';
import SemanticSearch from '@/components/SemanticSearch.vue';

export default {
  components: {
    BackupManager,
    AITagBatchProcessor,
    SemanticSearch
  },
  data() {
    return {
      showBackupManager: false,
      showAITagger: false,
      showSemanticSearch: false
    };
  }
};
</script>
```

---

## 工作流程示例

### 完整的AI处理流程

```javascript
// 1. 创建备份
const backup = await backendService.createBackup({
  name: 'AI处理前备份',
  description: '处理前自动创建'
});

// 2. 批量打标签（最近30天）
const tagResult = await backendService.batchTagBookmarks({
  days: 30,
  max_tags: 5,
  overwrite: false,
  create_backup: false  // 已手动创建备份
});

// 3. 生成向量嵌入
await backendService.generateEmbeddings({
  days: 30,
  overwrite: false
});

// 4. 测试语义搜索
const searchResults = await backendService.semanticSearch({
  query: '机器学习教程',
  min_similarity: 0.6,
  limit: 10
});

// 5. 如果效果不满意，还原备份
await backendService.restoreBackup({
  backup_id: backup.id,
  merge_mode: false
});
```

---

## 注意事项

### API密钥安全
- 不要将`GEMINI_API_KEY`提交到Git
- 使用环境变量管理密钥
- 生产环境使用专用的API密钥

### 性能优化
- 批量处理时建议分批进行（每次100-200个书签）
- 向量嵌入生成较慢，建议在低峰期运行
- 缓存AI生成的结果

### 数据隐私
- 敏感内容不会被发送到AI服务
- 可以在本地运行开源模型替代云端API
- 备份文件包含完整书签数据，注意保护

---

## 故障排查

### AI标签生成失败

**问题**：批量处理时部分书签失败

**解决方案**：
1. 检查API密钥是否正确
2. 查看后端日志了解错误详情
3. 检查网络连接
4. 降级使用简单的关键词提取

### 语义搜索无结果

**问题**：向量嵌入生成但搜索无结果

**解决方案**：
1. 降低`min_similarity`阈值（如0.3）
2. 确认书签有`ai_embedding`字段
3. 检查查询词是否过于特殊
4. 尝试不同的查询词

### 备份还原失败

**问题**：还原操作无法完成

**解决方案**：
1. 检查备份ID是否正确
2. 查看后端日志
3. 确认数据库权限
4. 尝试合并模式而非完全覆盖

---

## 开发建议

### 扩展AI功能

1. **支持更多AI服务商**
   - OpenAI GPT
   - Anthropic Claude
   - 本地模型（Llama、Mistral）

2. **增强标签生成**
   - 基于用户历史标签的个性化
   - 标签层次结构
   - 标签去重和合并

3. **改进语义搜索**
   - 混合检索（关键词+语义）
   - 搜索历史记录
   - 搜索结果重排序

### 前端优化

1. 添加进度条显示批量处理进度
2. 实现标签编辑和确认界面
3. 添加搜索结果预览
4. 支持快捷键操作

---

## 更新日志

### 2025-01-03
- ✅ 实现备份管理系统
- ✅ AI批量打标签功能
- ✅ 语义化搜索
- ✅ 扩展数据模型
- ✅ 创建前端组件

---

## 贡献指南

欢迎提交Issue和Pull Request来改进这些功能！

---

## 许可证

与FavBox主项目保持一致。
