/**
 * Redis客户端管理
 * 用于缓存和实时通知
 */
import Redis from 'ioredis';
import config from './config.js';

/**
 * 创建Redis客户端
 */
export const redis = new Redis(config.redis);

/**
 * 创建Redis订阅客户端(WebSocket通知)
 */
export const redisSub = new Redis(config.redis);

/**
 * 创建Redis发布客户端
 */
export const redisPub = new Redis(config.redis);

/**
 * Redis连接事件监听
 */
redis.on('connect', () => {
  console.log('Redis connected');
});

redis.on('error', (err) => {
  console.error('Redis error:', err);
});

redis.on('close', () => {
  console.log('Redis connection closed');
});

/**
 * 测试Redis连接
 */
export async function testRedisConnection() {
  try {
    await redis.ping();
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * 缓存用户会话
 * @param {string} userId - 用户ID
 * @param {string} token - JWT token
 * @param {number} expiresIn - 过期时间(秒)
 */
export async function cacheSession(userId, token, expiresIn) {
  const key = `session:${userId}:${token}`;
  await redis.setex(key, expiresIn, JSON.stringify({ userId, token }));
}

/**
 * 检查会话是否有效
 * @param {string} userId - 用户ID
 * @param {string} token - JWT token
 * @returns {Promise<boolean>}
 */
export async function validateSession(userId, token) {
  const key = `session:${userId}:${token}`;
  const session = await redis.get(key);
  return session !== null;
}

/**
 * 删除会话(登出)
 * @param {string} userId - 用户ID
 * @param {string} token - JWT token
 */
export async function removeSession(userId, token) {
  const key = `session:${userId}:${token}`;
  await redis.del(key);
}

/**
 * 发布WebSocket消息到指定用户的所有设备
 * @param {string} userId - 用户ID
 * @param {Object} message - 消息内容
 */
export async function publishToUser(userId, message) {
  const channel = `user:${userId}`;
  await redisPub.publish(channel, JSON.stringify(message));
}

/**
 * 订阅用户频道
 * @param {string} userId - 用户ID
 * @param {Function} callback - 消息处理回调
 */
export function subscribeToUser(userId, callback) {
  const channel = `user:${userId}`;
  redisSub.subscribe(channel);
  redisSub.on('message', (ch, message) => {
    if (ch === channel) {
      callback(JSON.parse(message));
    }
  });
}

/**
 * 取消订阅用户频道
 * @param {string} userId - 用户ID
 */
export function unsubscribeFromUser(userId) {
  const channel = `user:${userId}`;
  redisSub.unsubscribe(channel);
}

/**
 * 优雅关闭Redis连接
 */
export async function closeRedis() {
  await redis.quit();
  await redisSub.quit();
  await redisPub.quit();
  console.log('Redis connections closed');
}

export default {
  redis,
  redisSub,
  redisPub,
  testRedisConnection,
  cacheSession,
  validateSession,
  removeSession,
  publishToUser,
  subscribeToUser,
  unsubscribeFromUser,
  closeRedis,
};
