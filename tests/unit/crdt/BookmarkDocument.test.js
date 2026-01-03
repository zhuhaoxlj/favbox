/**
 * BookmarkDocument CRDT测试
 * 测试基础CRDT操作
 */
import { describe, it, expect, beforeAll } from 'vitest';
import { initAutomerge } from '../../../src/crdt/wasm-loader.js';
import {
  initFavboxDocument,
  addBookmark,
  updateBookmark,
  deleteBookmark,
  moveBookmark,
  addFolder,
  renameFolder,
  getDocumentStats,
} from '../../../src/crdt/BookmarkDocument.js';

describe('BookmarkDocument CRDT', () => {
  // 在所有测试前初始化Automerge WASM
  beforeAll(async () => {
    await initAutomerge();
  });

  it('应该成功初始化FavBox文档', async () => {
    const userId = 'test-user-123';
    const deviceId = 'test-device-456';

    const doc = await initFavboxDocument(userId, deviceId);

    expect(doc).toBeDefined();
    expect(doc.metadata.userId).toBe(userId);
    expect(doc.metadata.deviceId).toBe(deviceId);
    expect(doc.bookmarks).toEqual({});
    expect(doc.folders).toEqual({});
    expect(doc.tags).toEqual({});
  });

  it('应该成功添加书签', async () => {
    const doc = await initFavboxDocument('user-1', 'device-1');

    const bookmark = {
      id: 'bookmark-1',
      url: 'https://example.com',
      title: '示例网站',
      folderId: 'folder-1',
      folderPath: '/工作',
      tags: ['vue', 'javascript'],
    };

    const newDoc = await addBookmark(doc, bookmark);

    expect(newDoc.bookmarks['bookmark-1']).toBeDefined();
    expect(newDoc.bookmarks['bookmark-1'].url).toBe('https://example.com');
    expect(newDoc.bookmarks['bookmark-1'].title).toBe('示例网站');
    expect(newDoc.bookmarks['bookmark-1'].tags).toEqual(['vue', 'javascript']);

    // 检查标签计数
    expect(newDoc.tags.vue.count).toBe(1);
    expect(newDoc.tags.javascript.count).toBe(1);
  });

  it('应该成功更新���签', async () => {
    let doc = await initFavboxDocument('user-1', 'device-1');

    doc = await addBookmark(doc, {
      id: 'bookmark-1',
      url: 'https://example.com',
      title: '旧标题',
      tags: ['old'],
    });

    doc = await updateBookmark(doc, 'bookmark-1', {
      title: '新标题',
      tags: ['new'],
    });

    expect(doc.bookmarks['bookmark-1'].title).toBe('新标题');
    expect(doc.bookmarks['bookmark-1'].tags).toEqual(['new']);

    // 旧标签计数应该减少
    expect(doc.tags.old.count).toBe(0);
    expect(doc.tags.new.count).toBe(1);
  });

  it('应该成功软删除书签', async () => {
    let doc = await initFavboxDocument('user-1', 'device-1');

    doc = await addBookmark(doc, {
      id: 'bookmark-1',
      url: 'https://example.com',
      title: '要删除的书签',
      tags: ['test'],
    });

    doc = await deleteBookmark(doc, 'bookmark-1');

    expect(doc.bookmarks['bookmark-1'].deleted).toBe(true);
    expect(doc.bookmarks['bookmark-1'].deletedAt).toBeDefined();
    expect(doc.deletedBookmarks['bookmark-1']).toBeDefined();

    // 标签计数应该减少
    expect(doc.tags.test.count).toBe(0);
  });

  it('应该成功移动书签到新文件夹', async () => {
    let doc = await initFavboxDocument('user-1', 'device-1');

    doc = await addBookmark(doc, {
      id: 'bookmark-1',
      url: 'https://example.com',
      title: '书签',
      folderId: 'folder-1',
      folderPath: '/旧文件夹',
    });

    doc = await moveBookmark(doc, 'bookmark-1', 'folder-2', '/新文件夹');

    expect(doc.bookmarks['bookmark-1'].folderId).toBe('folder-2');
    expect(doc.bookmarks['bookmark-1'].folderPath).toBe('/新文件夹');
  });

  it('应该成功添加文件夹', async () => {
    let doc = await initFavboxDocument('user-1', 'device-1');

    doc = await addFolder(doc, {
      id: 'folder-1',
      title: '工作',
      parentId: 'root',
      path: '/工作',
    });

    expect(doc.folders['folder-1']).toBeDefined();
    expect(doc.folders['folder-1'].title).toBe('工作');
    expect(doc.folders['folder-1'].path).toBe('/工作');
  });

  it('应该成功重命名文件夹', async () => {
    let doc = await initFavboxDocument('user-1', 'device-1');

    doc = await addFolder(doc, {
      id: 'folder-1',
      title: '旧名称',
      path: '/旧名称',
    });

    doc = await renameFolder(doc, 'folder-1', '新名称');

    expect(doc.folders['folder-1'].title).toBe('新名称');
  });

  it('应该正确统计文档信息', async () => {
    let doc = await initFavboxDocument('user-1', 'device-1');

    // 添加3个书签
    doc = await addBookmark(doc, {
      id: 'bookmark-1',
      url: 'https://example1.com',
      title: '书签1',
      tags: ['tag1'],
    });
    doc = await addBookmark(doc, {
      id: 'bookmark-2',
      url: 'https://example2.com',
      title: '书签2',
      tags: ['tag2'],
    });
    doc = await addBookmark(doc, {
      id: 'bookmark-3',
      url: 'https://example3.com',
      title: '书签3',
      tags: ['tag1'],
    });

    // 删除1个书签
    doc = await deleteBookmark(doc, 'bookmark-3');

    // 添加2个文件夹
    doc = await addFolder(doc, { id: 'folder-1', title: '文件夹1' });
    doc = await addFolder(doc, { id: 'folder-2', title: '文件夹2' });

    const stats = await getDocumentStats(doc);

    expect(stats.totalBookmarks).toBe(3);
    expect(stats.activeBookmarks).toBe(2);
    expect(stats.deletedBookmarks).toBe(1);
    expect(stats.totalFolders).toBe(2);
    expect(stats.totalTags).toBe(2);
  });

  it('应该自动处理并发冲突(CRDT特性)', async () => {
    const { clone, merge } = await import('@automerge/automerge-wasm');

    // 创建初始文档
    let doc1 = await initFavboxDocument('user-1', 'device-1');
    doc1 = await addBookmark(doc1, {
      id: 'bookmark-1',
      url: 'https://example.com',
      title: '初始标题',
    });

    // Fork文档模拟两个设备
    let doc2 = clone(doc1);

    // 两个设备同时修改标题
    doc1 = await updateBookmark(doc1, 'bookmark-1', { title: '设备1的标题' });
    doc2 = await updateBookmark(doc2, 'bookmark-1', { title: '设备2的标题' });

    // 合并两个文档
    const mergedDoc = merge(doc1, doc2);

    // CRDT应该自动解决冲突(使用LWW或其他策略)
    expect(mergedDoc.bookmarks['bookmark-1'].title).toBeDefined();
    // 标题应该是其中一个(CRDT保证确定性)
    expect([
      '设备1的标题',
      '设备2的标题',
    ]).toContain(mergedDoc.bookmarks['bookmark-1'].title);
  });
});
