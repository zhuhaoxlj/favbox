/**
 * FavBox CRDT同步服务器
 * 主入口文件
 */
import Fastify from 'fastify';
import cors from '@fastify/cors';
import jwt from '@fastify/jwt';
import websocket from '@fastify/websocket';
import config from './config.js';
import { testConnection, closePool } from './db.js';
import { testRedisConnection, closeRedis } from './redis.js';

/**
 * 创建Fastify实例
 */
const fastify = Fastify({
  logger: {
    level: config.logger.level,
    transport: config.env === 'development'
      ? { target: 'pino-pretty' }
      : undefined,
  },
});

/**
 * 注册插件
 */
async function registerPlugins() {
  // CORS支持
  await fastify.register(cors, config.cors);

  // JWT认证
  await fastify.register(jwt, {
    secret: config.jwt.secret,
  });

  // WebSocket支持
  await fastify.register(websocket, {
    options: {
      maxPayload: 1048576, // 1MB
      perMessageDeflate: true,
    },
  });

  fastify.log.info('Plugins registered successfully');
}

/**
 * 注册路由
 */
async function registerRoutes() {
  // 健康检查
  fastify.get('/health', async (request, reply) => {
    const dbTest = await testConnection();
    const redisTest = await testRedisConnection();

    const isHealthy = dbTest.success && redisTest.success;

    return {
      status: isHealthy ? 'healthy' : 'unhealthy',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      services: {
        database: dbTest,
        redis: redisTest,
      },
    };
  });

  // API根路径
  fastify.get('/api', async () => {
    return {
      name: 'FavBox CRDT Sync Server',
      version: '1.0.0',
      endpoints: {
        health: '/health',
        auth: '/api/auth/*',
        sync: '/api/sync/*',
        export: '/api/export/*',
        history: '/api/history',
        devices: '/api/devices',
        ws: '/ws',
      },
    };
  });

  // TODO: 注册其他路由
  // await fastify.register(authRoutes, { prefix: '/api/auth' });
  // await fastify.register(syncRoutes, { prefix: '/api/sync' });
  // 等等...

  fastify.log.info('Routes registered successfully');
}

/**
 * 启动服务器
 */
async function start() {
  try {
    // 注册插件
    await registerPlugins();

    // 注册路由
    await registerRoutes();

    // 启动服务器
    await fastify.listen({
      port: config.port,
      host: config.host,
    });

    fastify.log.info(`Server listening on ${config.host}:${config.port}`);
    fastify.log.info(`Environment: ${config.env}`);

    // 测试数据库连接
    const dbTest = await testConnection();
    if (dbTest.success) {
      fastify.log.info('Database connected successfully');
    } else {
      fastify.log.error('Database connection failed:', dbTest.error);
    }

    // 测试Redis连接
    const redisTest = await testRedisConnection();
    if (redisTest.success) {
      fastify.log.info('Redis connected successfully');
    } else {
      fastify.log.error('Redis connection failed:', redisTest.error);
    }
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
}

/**
 * 优雅关闭
 */
async function gracefulShutdown(signal) {
  fastify.log.info(`Received ${signal}, shutting down gracefully...`);

  try {
    await fastify.close();
    await closePool();
    await closeRedis();
    fastify.log.info('Server closed successfully');
    process.exit(0);
  } catch (err) {
    fastify.log.error('Error during shutdown:', err);
    process.exit(1);
  }
}

// 监听退出信号
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// 启动服务器
start();
