/**
 * 统一错误处理系统
 * 提供一致的错误处理、日志记录和用户通知
 */

import { notify } from 'notiwind';

const NOTIFICATION_DURATION = import.meta.env.VITE_NOTIFICATION_DURATION;

/**
 * 错误类型枚举
 * @enum {string}
 */
export const ErrorType = {
  NETWORK: 'NetworkError',
  STORAGE: 'StorageError',
  AUTH: 'AuthError',
  VALIDATION: 'ValidationError',
  UNKNOWN: 'UnknownError',
};

/**
 * 错误处理配置选项
 * @typedef {object} ErrorHandlerOptions
 * @property {boolean} [showNotification=true] - 是否显示用户通知
 * @property {boolean} [silent=false] - 是否静默（不输出日志）
 * @property {boolean} [rethrow=false] - 是否重新抛出错误
 * @property {Function} [onError] - 自定义错误回调函数
 */

/**
 * 错误处理装饰器
 * 包装异步函数，提供统一的错误处理
 * @param {Function} handler - 异步处理函数
 * @param {string} [context] - 错误上下文描述
 * @param {ErrorHandlerOptions} [options] - 配置选项
 * @returns {Function} 包装后的函数
 * @example
 * const safeHandler = withErrorHandler(async () => {
 *   await riskyOperation();
 * }, 'bookmark creation', { rethrow: true });
 */
export function withErrorHandler(handler, context = '', options = {}) {
  const {
    showNotification = true,
    silent = false,
    rethrow = false,
    onError = null,
  } = options;

  return async (...args) => {
    try {
      return await handler(...args);
    } catch (error) {
      // 记录错误日志
      if (!silent) {
        const contextMsg = context ? ` in ${context}` : '';
        console.error(`Error${contextMsg}:`, error);
      }

      // 显示用户通知
      if (showNotification && error.name !== ErrorType.NETWORK) {
        const message = getErrorMessage(error);
        notify({
          group: 'error',
          text: message,
        }, NOTIFICATION_DURATION);
      }

      // 执行自定义错误回调
      if (onError && typeof onError === 'function') {
        try {
          onError(error);
        } catch (callbackError) {
          console.error('Error in error callback:', callbackError);
        }
      }

      // 可选：发送到错误跟踪服务（生产环境）
      // if (import.meta.env.PROD) {
      //   Sentry.captureException(error, { tags: { context } });
      // }

      // 重新抛出或返回 undefined
      if (rethrow) throw error;
      return undefined;
    }
  };
}

/**
 * 获取用户友好的错误消息
 * @param {Error} error - 错误对象
 * @returns {string} 错误消息
 */
function getErrorMessage(error) {
  switch (error.name) {
    case ErrorType.NETWORK:
      return 'Network connection failed. Please check your internet connection.';
    case ErrorType.STORAGE:
      return 'Failed to access local storage. Please try again.';
    case ErrorType.AUTH:
      return 'Authentication failed. Please log in again.';
    case ErrorType.VALIDATION:
      return error.message || 'Invalid input. Please check your data.';
    default:
      return error.message || 'An unexpected error occurred. Please try again.';
  }
}

/**
 * 创建自定义错误对象
 * @param {string} type - 错误类型（使用 ErrorType 枚举）
 * @param {string} message - 错误消息
 * @param {object} [details] - 额外的错误详情
 * @returns {Error} 错误对象
 * @example
 * throw createError(ErrorType.VALIDATION, 'Invalid URL format', { url: 'invalid-url' });
 */
export function createError(type, message, details = null) {
  const error = new Error(message);
  error.name = type;
  if (details) {
    error.details = details;
  }
  return error;
}

/**
 * Promise 包装器，自动处理错误
 * @param {Promise} promise - 要包装的 Promise
 * @param {string} [context] - 错误上下文
 * @returns {Promise<[Error|null, any]>} [错误, 结果] 元组
 * @example
 * const [error, data] = await safePromise(fetchData(), 'fetch user data');
 * if (error) {
 *   console.error('Failed to fetch:', error);
 *   return;
 * }
 * console.log('Data:', data);
 */
export async function safePromise(promise, context = '') {
  try {
    const data = await promise;
    return [null, data];
  } catch (error) {
    if (context) {
      console.error(`Error in ${context}:`, error);
    }
    return [error, null];
  }
}

/**
 * 批量操作错误处理
 * 处理批量操作中的部分失败情况
 * @param {Array} items - 要处理的项目数组
 * @param {Function} handler - 处理单个项目的函数
 * @param {string} [context] - 错误上下文
 * @returns {Promise<{success: Array, failed: Array<{item: any, error: Error}>}>} 成功和失败的项目
 * @example
 * const result = await batchOperation(
 *   bookmarks,
 *   async (bookmark) => await deleteBookmark(bookmark),
 *   'batch delete'
 * );
 * console.log(`Deleted: ${result.success.length}, Failed: ${result.failed.length}`);
 */
export async function batchOperation(items, handler, context = '') {
  const success = [];
  const failed = [];

  for (const item of items) {
    try {
      const result = await handler(item);
      success.push(result);
    } catch (error) {
      console.error(`Error processing item in ${context}:`, error);
      failed.push({ item, error });
    }
  }

  return { success, failed };
}

export default {
  withErrorHandler,
  createError,
  safePromise,
  batchOperation,
  ErrorType,
};
