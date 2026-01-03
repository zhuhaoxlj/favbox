-- FavBox CRDT同步系统 - 数据库初始化脚本
-- PostgreSQL 15+

-- ============================================
-- 1. 用户表
-- ============================================
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  username VARCHAR(100),
  avatar_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_login_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.email IS '用户邮箱(唯一)';
COMMENT ON COLUMN users.password_hash IS 'bcrypt加密后的密码';

-- ============================================
-- 2. 设备表
-- ============================================
CREATE TABLE IF NOT EXISTS devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_id VARCHAR(100) UNIQUE NOT NULL,
  device_name VARCHAR(255),
  browser_type VARCHAR(50),
  os VARCHAR(50),
  last_sync_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT unique_user_device UNIQUE(user_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
COMMENT ON TABLE devices IS '设备表,记录每个用户的所有设备';
COMMENT ON COLUMN devices.device_id IS '浏览器扩展生成的设备唯一ID';
COMMENT ON COLUMN devices.browser_type IS '浏览器类型: chrome/edge/arc/firefox';

-- ============================================
-- 3. CRDT操作日志表
-- ============================================
CREATE TABLE IF NOT EXISTS crdt_operations (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_id VARCHAR(100) NOT NULL,
  operation_data BYTEA NOT NULL,
  operation_hash VARCHAR(64) UNIQUE NOT NULL,
  sequence_number BIGINT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crdt_ops_user ON crdt_operations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crdt_ops_device ON crdt_operations(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crdt_ops_sequence ON crdt_operations(user_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_crdt_ops_hash ON crdt_operations(operation_hash);

COMMENT ON TABLE crdt_operations IS 'CRDT操作日志表,存储所有Automerge变更';
COMMENT ON COLUMN crdt_operations.operation_data IS 'Automerge change的二进制数据';
COMMENT ON COLUMN crdt_operations.operation_hash IS 'SHA256哈希,用于防止重复操作';
COMMENT ON COLUMN crdt_operations.sequence_number IS '操作序列号,用于增量同步';

-- ============================================
-- 4. CRDT文档快照表
-- ============================================
CREATE TABLE IF NOT EXISTS crdt_snapshots (
  id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  snapshot_data BYTEA NOT NULL,
  last_operation_id BIGINT NOT NULL REFERENCES crdt_operations(id),
  bookmark_count INT NOT NULL DEFAULT 0,
  snapshot_size_bytes INT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crdt_snapshots_user ON crdt_snapshots(user_id, created_at DESC);

COMMENT ON TABLE crdt_snapshots IS 'CRDT文档快照表,定期保存完整文档加速首次加载';
COMMENT ON COLUMN crdt_snapshots.snapshot_data IS 'Automerge.save()的完整文档数据';
COMMENT ON COLUMN crdt_snapshots.bookmark_count IS '快照中的书签数量';

-- ============================================
-- 5. 书签索引表
-- ============================================
CREATE TABLE IF NOT EXISTS bookmark_index (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  title TEXT,
  domain VARCHAR(255),
  folder_path TEXT,
  tags TEXT[],
  deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  search_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('simple',
      coalesce(title, '') || ' ' ||
      coalesce(url, '') || ' ' ||
      array_to_string(tags, ' ')
    )
  ) STORED
);

CREATE INDEX IF NOT EXISTS idx_bookmark_index_user ON bookmark_index(user_id, deleted);
CREATE INDEX IF NOT EXISTS idx_bookmark_index_url ON bookmark_index(user_id, url);
CREATE INDEX IF NOT EXISTS idx_bookmark_index_domain ON bookmark_index(user_id, domain);
CREATE INDEX IF NOT EXISTS idx_bookmark_index_tags ON bookmark_index USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_bookmark_index_search ON bookmark_index USING GIN (search_vector);

COMMENT ON TABLE bookmark_index IS '书签索引表,从CRDT文档同步,用于快速搜索';
COMMENT ON COLUMN bookmark_index.search_vector IS '全文搜索向量';

-- ============================================
-- 6. 同步状态表
-- ============================================
CREATE TABLE IF NOT EXISTS sync_state (
  id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_id VARCHAR(100) NOT NULL,
  last_sync_operation_id BIGINT,
  sync_state_data BYTEA,
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT unique_user_device_sync UNIQUE(user_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_sync_state_user_device ON sync_state(user_id, device_id);

COMMENT ON TABLE sync_state IS '同步状态表,跟踪每个设备的同步进度';
COMMENT ON COLUMN sync_state.sync_state_data IS 'Automerge SyncState的二进制数据';

-- ============================================
-- 7. 会话表
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) UNIQUE NOT NULL,
  device_id VARCHAR(100),
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

COMMENT ON TABLE sessions IS 'JWT会话表,用于token验证和管理';

-- ============================================
-- 8. 触发器: 更新用户updated_at时间戳
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 9. 清理过期会话的函数
-- ============================================
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM sessions WHERE expires_at < NOW();
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_sessions IS '清理过期的JWT会话';

-- ============================================
-- 10. 获取用户统计信息的函数
-- ============================================
CREATE OR REPLACE FUNCTION get_user_stats(p_user_id UUID)
RETURNS TABLE (
  total_bookmarks BIGINT,
  total_operations BIGINT,
  total_devices INTEGER,
  storage_used_bytes BIGINT,
  last_sync_at TIMESTAMP
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    COUNT(DISTINCT bi.id)::BIGINT as total_bookmarks,
    COUNT(DISTINCT co.id)::BIGINT as total_operations,
    COUNT(DISTINCT d.id)::INTEGER as total_devices,
    COALESCE(SUM(LENGTH(co.operation_data)), 0)::BIGINT as storage_used_bytes,
    MAX(d.last_sync_at) as last_sync_at
  FROM users u
  LEFT JOIN bookmark_index bi ON bi.user_id = u.id AND bi.deleted = FALSE
  LEFT JOIN crdt_operations co ON co.user_id = u.id
  LEFT JOIN devices d ON d.user_id = u.id
  WHERE u.id = p_user_id
  GROUP BY u.id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_user_stats IS '获取用户的统计信息';

-- ============================================
-- 初始化完成
-- ============================================
-- 插入系统信息记录
CREATE TABLE IF NOT EXISTS system_info (
  key VARCHAR(50) PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO system_info (key, value) VALUES
  ('schema_version', '1.0.0'),
  ('initialized_at', NOW()::TEXT)
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();

-- 输出初始化成功消息
DO $$
BEGIN
  RAISE NOTICE '✅ FavBox CRDT数据库初始化完成!';
  RAISE NOTICE '📊 创建表: users, devices, crdt_operations, crdt_snapshots, bookmark_index, sync_state, sessions';
  RAISE NOTICE '🔍 创建索引: 14个优化索引';
  RAISE NOTICE '⚡ 创建函数: update_updated_at_column, cleanup_expired_sessions, get_user_stats';
END $$;
