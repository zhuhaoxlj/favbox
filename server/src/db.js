/**
 * PostgreSQL数据库连接管理
 * 使用连接池提升性能
 */
import pg from 'pg';
import config from './config.js';

const { Pool } = pg;

/**
 * 创建数据库连接池
 */
export const pool = new Pool(config.database);

/**
 * 测试数据库连接
 */
export async function testConnection() {
  try {
    const client = await pool.connect();
    const result = await client.query('SELECT NOW()');
    client.release();
    return {
      success: true,
      time: result.rows[0].now,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

/**
 * 执行SQL查询
 * @param {string} text - SQL查询语句
 * @param {Array} params - 参数数组
 * @returns {Promise<Object>} 查询结果
 */
export async function query(text, params) {
  const start = Date.now();
  try {
    const result = await pool.query(text, params);
    const duration = Date.now() - start;
    console.log('Executed query', { text, duration, rows: result.rowCount });
    return result;
  } catch (error) {
    console.error('Query error', { text, error: error.message });
    throw error;
  }
}

/**
 * 获取单个客户端连接(用于事务)
 */
export async function getClient() {
  const client = await pool.connect();
  const originalQuery = client.query;
  const originalRelease = client.release;

  // 包装query方法添加日志
  client.query = (...args) => {
    const start = Date.now();
    return originalQuery.apply(client, args).then((result) => {
      const duration = Date.now() - start;
      console.log('Executed query', { duration, rows: result.rowCount });
      return result;
    });
  };

  // 确保release只调用一次
  let released = false;
  client.release = () => {
    if (released) return;
    released = true;
    originalRelease.apply(client);
  };

  return client;
}

/**
 * 优雅关闭数据库连接池
 */
export async function closePool() {
  await pool.end();
  console.log('Database pool closed');
}

export default {
  pool,
  query,
  getClient,
  testConnection,
  closePool,
};
