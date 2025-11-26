/**
 * useBookmarkActions - 书签操作组合式函数
 *
 * 提供统一的书签操作方法，包括删除、置顶等功能。
 * 遵循DRY原则，避免在多个组件中重复代码。
 * 支持撤销删除功能，提升用户体验。
 */

/* eslint-disable import/prefer-default-export */

import { notify } from 'notiwind';
import BookmarkStorage from '@/storage/bookmark';
import { backendClient } from '@/services/backend';
import browser from 'webextension-polyfill';

const NOTIFICATION_DURATION = import.meta.env.VITE_NOTIFICATION_DURATION;
const UNDO_DELAY = 10000; // 10秒撤销时间
const bookmarkStorage = new BookmarkStorage();

// 存储待删除的书签（支持撤销）
const pendingDeletions = new Map();

/**
 * 书签操作组合式函数
 * @returns {object} 书签操作方法集合
 */
export function useBookmarkActions() {
  /**
   * 删除书签（本地+云端）- 立即执行版本（不支持撤销）
   * @param {object} bookmark - 书签对象
   * @param {string|number} bookmark.id - 书签ID
   * @returns {Promise<string>} 返回被删除的书签ID
   * @throws {Error} 如果删除失败抛出错误
   */
  const deleteBookmarkImmediately = async (bookmark) => {
    const id = String(bookmark.id);

    // 删除本地书签
    await browser.bookmarks.remove(id);

    // 同步到云端（如果已配置）
    if (backendClient.isConfigured() && backendClient.isAuthenticated()) {
      try {
        await backendClient.deleteBookmark(id);
      } catch (error) {
        console.error('Error syncing deletion to backend:', error);
        // 本地删除成功，云端失败不影响用户
      }
    }

    console.log(`Bookmark ${id} successfully removed`);
    return id;
  };

  /**
   * 撤销删除
   * @param {string} id - 书签ID
   * @returns {object|null} 恢复的书签对象，如果不存在返回null
   */
  const undoDelete = (id) => {
    if (pendingDeletions.has(id)) {
      const { bookmark, timeoutId } = pendingDeletions.get(id);

      // 取消延迟删除
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      // 从待删除列表移除
      pendingDeletions.delete(id);

      // 显示恢复通知
      notify(
        {
          group: 'default',
          text: 'Bookmark restored',
        },
        3000,
      );

      console.log(`Bookmark ${id} deletion cancelled`);
      return bookmark;
    }
    return null;
  };

  /**
   * 删除书签（支持撤销）
   * @param {object} bookmark - 书签对象
   * @param {string|number} bookmark.id - 书签ID
   * @param {number} [undoDelay] - 撤销延迟时间（毫秒）
   * @returns {Promise<string>} 返回被删除的书签ID
   */
  const deleteBookmark = async (bookmark, undoDelay = UNDO_DELAY) => {
    const id = String(bookmark.id);

    // 标记为待删除
    pendingDeletions.set(id, {
      bookmark,
      deleteAt: Date.now() + undoDelay,
      timeoutId: null,
    });

    // 显示带撤销按钮的通知
    notify(
      {
        group: 'default',
        text: 'Bookmark deleted',
        actionLabel: 'Undo',
        action: () => undoDelete(id),
      },
      undoDelay,
    );

    // 延迟执行真正的删除
    const timeoutId = setTimeout(async () => {
      if (pendingDeletions.has(id)) {
        try {
          await deleteBookmarkImmediately(bookmark);
          pendingDeletions.delete(id);

          // 显示最终删除确认
          notify(
            {
              group: 'default',
              text: 'Bookmark permanently removed',
            },
            3000,
          );
        } catch (error) {
          console.error('Failed to delete bookmark:', error);
          // 删除失败，自动恢复
          undoDelete(id);
          notify(
            {
              group: 'error',
              text: 'Failed to delete bookmark',
            },
            NOTIFICATION_DURATION,
          );
        }
      }
    }, undoDelay);

    // 保存 timeout ID 以便取消
    pendingDeletions.get(id).timeoutId = timeoutId;

    return id;
  };

  /**
   * 批量删除书签
   * @param {object[]} bookmarks - 书签数组
   * @param {boolean} [withUndo] - 是否支持撤销
   * @returns {Promise<string[]>} 返回成功删除的书签ID数组
   */
  const deleteBookmarks = async (bookmarks, withUndo = true) => {
    const deletedIds = [];

    for (const bookmark of bookmarks) {
      try {
        const deleteMethod = withUndo ? deleteBookmark : deleteBookmarkImmediately;
        const id = await deleteMethod(bookmark);
        deletedIds.push(id);
      } catch (error) {
        console.error(`Failed to delete bookmark ${bookmark.id}:`, error);
        notify(
          {
            group: 'error',
            text: `Failed to remove bookmark: ${bookmark.title || bookmark.url}`,
          },
          NOTIFICATION_DURATION,
        );
      }
    }

    return deletedIds;
  };

  /**
   * 更新书签置顶状态
   * @param {object} bookmark - 书签对象
   * @param {string|number} bookmark.id - 书签ID
   * @param {number} status - 置顶状态 (0: 取消置顶, 1: 置顶)
   * @returns {Promise<void>}
   */
  const togglePin = async (bookmark, status) => {
    await bookmarkStorage.updatePinStatusById(bookmark.id, status);

    const message = status
      ? 'Bookmark successfully pinned!'
      : 'Bookmark successfully unpinned!';

    notify({ group: 'default', text: message }, NOTIFICATION_DURATION);
  };

  /**
   * 检查书签是否在待删除列表中
   * @param {string|number} id - 书签ID
   * @returns {boolean} 是否待删除
   */
  const isPendingDeletion = (id) => pendingDeletions.has(String(id));

  /**
   * 获取所有待删除的书签ID
   * @returns {string[]} 书签ID数组
   */
  const getPendingDeletions = () => Array.from(pendingDeletions.keys());

  return {
    deleteBookmark,
    deleteBookmarkImmediately,
    deleteBookmarks,
    togglePin,
    undoDelete,
    isPendingDeletion,
    getPendingDeletions,
  };
}
