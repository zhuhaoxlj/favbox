/**
 * 服务器配置管理
 * 从环境变量加载配置
 */
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 加载.env文件
dotenv.config({ path: join(__dirname, '../.env') });

export const config = {
  // 服务器配置
  env: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT || '3000', 10),
  host: process.env.HOST || '0.0.0.0',

  // 数据库配置
  database: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'favbox_crdt',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '',
    max: 20, // 连接池最大连接数
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
  },

  // Redis配置
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379', 10),
    password: process.env.REDIS_PASSWORD || undefined,
    db: 0,
    retryStrategy: (times) => {
      const delay = Math.min(times * 50, 2000);
      return delay;
    },
  },

  // JWT配置
  jwt: {
    secret: process.env.JWT_SECRET || 'development-secret-change-in-production',
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
  },

  // CORS配置
  cors: {
    origin: process.env.CORS_ORIGIN || '*',
    credentials: true,
  },

  // 日志配置
  logger: {
    level: process.env.LOG_LEVEL || 'info',
    prettyPrint: process.env.NODE_ENV === 'development',
  },

  // CRDT配置
  crdt: {
    snapshotInterval: 1000, // 每1000个操作创建一次快照
    maxSnapshotsPerUser: 10, // 每个用户保留最多10个快照
    operationBatchSize: 100, // 批量处理操作的大小
  },
};

export default config;
