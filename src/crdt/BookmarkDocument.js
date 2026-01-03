/**
 * FavBox CRDT文档结构定义
 * 使用Automerge实现的书签CRDT文档
 */
import { getAutomerge } from './wasm-loader.js';

/**
 * 初始化FavBox CRDT文档
 * @param {string} userId - 用户ID
 * @param {string} deviceId - 设备ID (用作Automerge actor ID)
 * @returns {Promise<AutomergeDoc>} CRDT文档实例
 */
export async function initFavboxDocument(userId, deviceId) {
  const { create, change } = await getAutomerge();

  // 将deviceId转换为十六进制字符串 (Automerge要求hex格式)
  // 简单方案: 使用deviceId的哈希或直接生成随机hex
  const actorId = Buffer.from(deviceId).toString('hex');

  // 创建新文档,使用十六进制actor ID
  let doc = create({ actor: actorId });

  // 初始化文档结构
  doc = change(doc, '初始化FavBox文档', (d) => {
    // 元数据
    d.metadata = {
      userId,
      deviceId,
      version: '1.0.0',
      createdAt: Date.now(),
    };

    // 书签集合 (Map结构)
    d.bookmarks = {};

    // 文件夹集合 (Map结构)
    d.folders = {};

    // 标签集合 (Map结构,存储标签使用计数)
    d.tags = {};

    // 删除操作记录 (支持版本历史回溯)
    d.deletedBookmarks = {};

    // 删除的文件夹记录
    d.deletedFolders = {};
  });

  console.log('[CRDT] ✅ FavBox文档初始化成功', { userId, deviceId });
  return doc;
}

/**
 * 添加书签到CRDT文档
 * @param {AutomergeDoc} doc - CRDT文档
 * @param {Object} bookmark - 书签对象
 * @param {string} bookmark.id - 书签ID
 * @param {string} bookmark.url - URL
 * @param {string} bookmark.title - 标题
 * @param {string} bookmark.folderId - 文件夹ID
 * @param {string[]} [bookmark.tags] - 标签数组
 * @param {string} [bookmark.notes] - 备注
 * @returns {Promise<AutomergeDoc>} 更新后的文档
 */
export async function addBookmark(doc, bookmark) {
  const { change } = await getAutomerge();

  const newDoc = change(doc, `添加书签: ${bookmark.title}`, (d) => {
    d.bookmarks[bookmark.id] = {
      id: bookmark.id,
      browserId: bookmark.browserId || '',
      url: bookmark.url,
      title: bookmark.title || '',
      description: bookmark.description || '',
      folderId: bookmark.folderId || 'root',
      folderPath: bookmark.folderPath || '/',
      tags: bookmark.tags || [],
      notes: bookmark.notes || '',
      favicon: bookmark.favicon || '',
      image: bookmark.image || '',
      domain: bookmark.domain || new URL(bookmark.url).hostname,
      keywords: bookmark.keywords || [],
      httpStatus: bookmark.httpStatus || 0,
      pinned: 0,
      createdAt: bookmark.createdAt || Date.now(),
      updatedAt: Date.now(),
      deleted: false,
      deletedAt: null,
    };

    // 更新标签计数
    if (bookmark.tags && bookmark.tags.length > 0) {
      bookmark.tags.forEach((tag) => {
        if (!d.tags[tag]) {
          d.tags[tag] = { count: 1 };
        } else {
          d.tags[tag].count += 1;
        }
      });
    }
  });

  return newDoc;
}

/**
 * 更新书签
 * @param {AutomergeDoc} doc - CRDT文档
 * @param {string} bookmarkId - 书签ID
 * @param {Object} changes - 要更新的字段
 * @returns {Promise<AutomergeDoc>} 更新后的文档
 */
export async function updateBookmark(doc, bookmarkId, changes) {
  const { change } = await getAutomerge();

  const newDoc = change(doc, `更新书签: ${bookmarkId}`, (d) => {
    if (!d.bookmarks[bookmarkId]) {
      console.warn(`[CRDT] 书签不存在: ${bookmarkId}`);
      return;
    }

    const bookmark = d.bookmarks[bookmarkId];

    // 更新标签前先减少旧标签计数
    if (changes.tags && bookmark.tags) {
      bookmark.tags.forEach((tag) => {
        if (d.tags[tag] && d.tags[tag].count > 0) {
          d.tags[tag].count -= 1;
        }
      });
    }

    // 应用更新
    Object.keys(changes).forEach((key) => {
      bookmark[key] = changes[key];
    });

    bookmark.updatedAt = Date.now();

    // 更新新标签计数
    if (changes.tags) {
      changes.tags.forEach((tag) => {
        if (!d.tags[tag]) {
          d.tags[tag] = { count: 1 };
        } else {
          d.tags[tag].count += 1;
        }
      });
    }
  });

  return newDoc;
}

/**
 * 删除书签 (软删除)
 * @param {AutomergeDoc} doc - CRDT文档
 * @param {string} bookmarkId - 书签ID
 * @returns {Promise<AutomergeDoc>} 更新后的文档
 */
export async function deleteBookmark(doc, bookmarkId) {
  const { change } = await getAutomerge();

  const newDoc = change(doc, `删除书签: ${bookmarkId}`, (d) => {
    if (!d.bookmarks[bookmarkId]) {
      console.warn(`[CRDT] 书签不存在: ${bookmarkId}`);
      return;
    }

    const bookmark = d.bookmarks[bookmarkId];

    // 减少标签计数
    if (bookmark.tags && bookmark.tags.length > 0) {
      bookmark.tags.forEach((tag) => {
        if (d.tags[tag] && d.tags[tag].count > 0) {
          d.tags[tag].count -= 1;
        }
      });
    }

    // 软删除
    bookmark.deleted = true;
    bookmark.deletedAt = Date.now();

    // 移动到删除记录
    d.deletedBookmarks[bookmarkId] = { ...bookmark };
  });

  return newDoc;
}

/**
 * 移动书签到指定文件夹
 * @param {AutomergeDoc} doc - CRDT文档
 * @param {string} bookmarkId - 书签ID
 * @param {string} targetFolderId - 目标文件夹ID
 * @param {string} targetFolderPath - 目标文件夹路径
 * @returns {Promise<AutomergeDoc>} 更新后的文��
 */
export async function moveBookmark(doc, bookmarkId, targetFolderId, targetFolderPath) {
  const { change } = await getAutomerge();

  const newDoc = change(doc, `移动书签: ${bookmarkId} -> ${targetFolderId}`, (d) => {
    if (!d.bookmarks[bookmarkId]) {
      console.warn(`[CRDT] 书签不存���: ${bookmarkId}`);
      return;
    }

    d.bookmarks[bookmarkId].folderId = targetFolderId;
    d.bookmarks[bookmarkId].folderPath = targetFolderPath;
    d.bookmarks[bookmarkId].updatedAt = Date.now();
  });

  return newDoc;
}

/**
 * 添加文件夹
 * @param {AutomergeDoc} doc - CRDT文档
 * @param {Object} folder - 文件夹对象
 * @returns {Promise<AutomergeDoc>} 更新后的文档
 */
export async function addFolder(doc, folder) {
  const { change } = await getAutomerge();

  const newDoc = change(doc, `添加文件夹: ${folder.title}`, (d) => {
    d.folders[folder.id] = {
      id: folder.id,
      browserId: folder.browserId || '',
      title: folder.title,
      parentId: folder.parentId || 'root',
      path: folder.path || `/${folder.title}`,
      order: 0,
      createdAt: folder.createdAt || Date.now(),
      updatedAt: Date.now(),
      deleted: false,
    };
  });

  return newDoc;
}

/**
 * 重命名文件夹
 * @param {AutomergeDoc} doc - CRDT文档
 * @param {string} folderId - 文件夹ID
 * @param {string} newTitle - 新标题
 * @returns {Promise<AutomergeDoc>} 更新后的文档
 */
export async function renameFolder(doc, folderId, newTitle) {
  const { change } = await getAutomerge();

  const newDoc = change(doc, `重命名文件夹: ${folderId} -> ${newTitle}`, (d) => {
    if (!d.folders[folderId]) {
      console.warn(`[CRDT] 文件夹不存在: ${folderId}`);
      return;
    }

    d.folders[folderId].title = newTitle;
    d.folders[folderId].updatedAt = Date.now();
  });

  return newDoc;
}

/**
 * 获取文档统计信息
 * @param {AutomergeDoc} doc - CRDT文档
 * @returns {Promise<Object>} 统计信息
 */
export async function getDocumentStats(doc) {
  const bookmarks = Object.values(doc.bookmarks || {});
  const activeBookmarks = bookmarks.filter((b) => !b.deleted);
  const folders = Object.values(doc.folders || {});
  const tags = Object.keys(doc.tags || {});

  return {
    totalBookmarks: bookmarks.length,
    activeBookmarks: activeBookmarks.length,
    deletedBookmarks: bookmarks.length - activeBookmarks.length,
    totalFolders: folders.length,
    totalTags: tags.length,
    lastUpdated: Math.max(...bookmarks.map((b) => b.updatedAt || 0)),
  };
}

export default {
  initFavboxDocument,
  addBookmark,
  updateBookmark,
  deleteBookmark,
  moveBookmark,
  addFolder,
  renameFolder,
  getDocumentStats,
};
