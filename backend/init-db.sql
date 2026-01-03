-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 启用全文搜索支持（已内置在PostgreSQL中）
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 创建基础索引配置（中文全文搜索需要zhparser，此处先用英文）
-- 如果需要中文支持，后续可安装 zhparser 扩展

COMMENT ON EXTENSION vector IS 'Vector similarity search for PostgreSQL';
