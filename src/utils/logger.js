/**
 * 环境感知的日志系统
 * 根据环境自动调整日志级别，生产环境减少不必要的日志输出
 */

/**
 * 日志级别枚举
 * @enum {number}
 */
const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
};

/**
 * 获取当前环境的日志级别
 * @returns {number} 日志级别
 */
const getCurrentLogLevel = () => {
  if (import.meta.env.DEV) {
    return LogLevel.DEBUG; // 开发环境：输出所有日志
  }
  return LogLevel.INFO; // 生产环境：不输出 debug 日志
};

const currentLevel = getCurrentLogLevel();

/**
 * 格式化日志消息
 * @param {string} level - 日志级别标识
 * @param {string} context - 日志上下文
 * @param {any[]} args - 日志参数
 * @returns {any[]} 格式化后的日志参数数组
 */
const formatMessage = (level, context, ...args) => {
  const timestamp = new Date().toISOString();
  const prefix = context ? `[${context}]` : '';
  return [`[${timestamp}] ${level} ${prefix}`, ...args];
};

/**
 * 环境感知的日志工具
 * 提供统一的日志接口，自动根据环境控制输出
 */
export const logger = {
  /**
   * 调试日志 - 仅在开发环境输出
   * 用于详细的调试信息，不应在生产环境显示
   * @param {string} context - 日志上下文（模块名、功能名等）
   * @param {...any} args - 日志内容
   * @example
   * logger.debug('BookmarkSync', 'Processing bookmark:', bookmark);
   */
  debug: (context, ...args) => {
    if (currentLevel <= LogLevel.DEBUG) {
      console.log(...formatMessage('DEBUG', context, ...args));
    }
  },

  /**
   * 信息日志
   * 用于一般的信息输出，记录正常的业务流程
   * @param {string} context - 日志上下文
   * @param {...any} args - 日志内容
   * @example
   * logger.info('ServiceWorker', 'Wake up..');
   */
  info: (context, ...args) => {
    if (currentLevel <= LogLevel.INFO) {
      console.info(...formatMessage('INFO', context, ...args));
    }
  },

  /**
   * 警告日志
   * 用于警告信息，表示可能出现的问题但不影响主流程
   * @param {string} context - 日志上下文
   * @param {...any} args - 日志内容
   * @example
   * logger.warn('Sync', 'Retry attempt 3/5');
   */
  warn: (context, ...args) => {
    if (currentLevel <= LogLevel.WARN) {
      console.warn(...formatMessage('WARN', context, ...args));
    }
  },

  /**
   * 错误日志 - 总是输出
   * 用于错误信息，需要关注和处理
   * @param {string} context - 日志上下文
   * @param {...any} args - 日志内容
   * @example
   * logger.error('Database', 'Failed to connect:', error);
   */
  error: (context, ...args) => {
    console.error(...formatMessage('ERROR', context, ...args));
  },

  /**
   * 性能计时开始 - 仅在开发环境有效
   * 用于测量代码执行时间
   * @param {string} label - 计时标签
   * @example
   * logger.time('fetchBookmarks');
   * await fetchBookmarks();
   * logger.timeEnd('fetchBookmarks');
   */
  time: (label) => {
    if (currentLevel <= LogLevel.DEBUG) {
      console.time(label);
    }
  },

  /**
   * 性能计时结束 - 仅在开发环境有效
   * 输出计时结果
   * @param {string} label - 计时标签
   */
  timeEnd: (label) => {
    if (currentLevel <= LogLevel.DEBUG) {
      console.timeEnd(label);
    }
  },

  /**
   * 分组开始 - 仅在开发环境有效
   * 用于将相关日志分组显示
   * @param {string} label - 分组标签
   * @example
   * logger.group('Bookmark Processing');
   * logger.debug('Processing', 'Step 1');
   * logger.debug('Processing', 'Step 2');
   * logger.groupEnd();
   */
  group: (label) => {
    if (currentLevel <= LogLevel.DEBUG) {
      console.group(label);
    }
  },

  /**
   * 分组结束 - 仅在开发环境有效
   */
  groupEnd: () => {
    if (currentLevel <= LogLevel.DEBUG) {
      console.groupEnd();
    }
  },

  /**
   * 折叠分组开始 - 仅在开发环境有效
   * 默认折叠的分组
   * @param {string} label - 分组标签
   */
  groupCollapsed: (label) => {
    if (currentLevel <= LogLevel.DEBUG) {
      console.groupCollapsed(label);
    }
  },

  /**
   * 表格输出 - 仅在开发环境有效
   * 以表格形式显示数组或对象
   * @param {Array | object} data - 要显示的数据
   * @example
   * logger.table(bookmarks);
   */
  table: (data) => {
    if (currentLevel <= LogLevel.DEBUG) {
      console.table(data);
    }
  },

  /**
   * 追踪调用栈 - 仅在开发环境有效
   * 输出当前的函数调用栈
   * @param {string} [label] - 追踪标签
   */
  trace: (label = '') => {
    if (currentLevel <= LogLevel.DEBUG) {
      console.trace(label);
    }
  },
};

/**
 * 创建带上下文的日志记录器
 * 返回一个预设上下文的日志对象，避免重复传入上下文参数
 * @param {string} context - 固定的日志上下文
 * @returns {object} 带上下文的日志对象
 * @example
 * const syncLogger = createLogger('BookmarkSync');
 * syncLogger.info('Starting sync...');
 * syncLogger.debug('Processing bookmark:', bookmark);
 */
export function createLogger(context) {
  return {
    debug: (...args) => logger.debug(context, ...args),
    info: (...args) => logger.info(context, ...args),
    warn: (...args) => logger.warn(context, ...args),
    error: (...args) => logger.error(context, ...args),
    time: (label) => logger.time(`${context}:${label}`),
    timeEnd: (label) => logger.timeEnd(`${context}:${label}`),
    group: (label) => logger.group(`${context} - ${label}`),
    groupEnd: () => logger.groupEnd(),
    groupCollapsed: (label) => logger.groupCollapsed(`${context} - ${label}`),
    table: (data) => logger.table(data),
    trace: (label) => logger.trace(`${context}${label ? ` - ${label}` : ''}`),
  };
}

export default logger;
