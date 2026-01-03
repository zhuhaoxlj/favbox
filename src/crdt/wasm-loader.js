/**
 * Automerge WASM加载器
 * 初始化Automerge WASM模块,确保在使用前加载完成
 */

/**
 * WASM是否已初始化
 * @type {boolean}
 */
let wasmInitialized = false;

/**
 * WASM初始化Promise
 * @type {Promise<void>|null}
 */
let initPromise = null;

/**
 * 初始化Automerge WASM
 * 使用单例模式确保只初始化一次
 * @returns {Promise<void>}
 */
export async function initAutomerge() {
  // 如果已经初始化,直接返回
  if (wasmInitialized) {
    return;
  }

  // 如果正在初始化,返回现有Promise
  if (initPromise) {
    return initPromise;
  }

  // 创建初始化Promise
  initPromise = (async () => {
    try {
      console.log('[CRDT] 正在初始化Automerge WASM...');

      // 动态导入Automerge
      const Automerge = await import('@automerge/automerge-wasm');

      // Automerge 1.x WASM自动初始化
      // 只需导入即可，无需显式等待
      wasmInitialized = true;
      console.log('[CRDT] ✅ Automerge WASM初始化成功');
    } catch (error) {
      console.error('[CRDT] ❌ Automerge WASM初始化失败:', error);
      initPromise = null; // 重置Promise以允许重试
      throw error;
    }
  })();

  return initPromise;
}

/**
 * 检查WASM是否已初始化
 * @returns {boolean}
 */
export function isWasmInitialized() {
  return wasmInitialized;
}

/**
 * 确保WASM已初始化
 * 如果未初始化则抛出错误
 * @throws {Error} 如果WASM未初始化
 */
export function ensureWasmInitialized() {
  if (!wasmInitialized) {
    throw new Error('[CRDT] Automerge WASM未初始化,请先调用initAutomerge()');
  }
}

/**
 * 获取Automerge模块
 * 自动等待WASM初始化完成
 * @returns {Promise<typeof import('@automerge/automerge-wasm')>}
 */
export async function getAutomerge() {
  await initAutomerge();
  return import('@automerge/automerge-wasm');
}

export default {
  initAutomerge,
  isWasmInitialized,
  ensureWasmInitialized,
  getAutomerge,
};
