<template>
  <div class="flex h-screen w-full flex-col overflow-y-auto bg-white dark:bg-black p-6">
    <h1 class="text-2xl font-bold text-black dark:text-white mb-6">
      Cloud Sync Settings
    </h1>

    <!-- Server Configuration -->
    <div class="mb-8 rounded-lg border border-gray-200 dark:border-neutral-800 p-4">
      <h2 class="text-lg font-semibold text-black dark:text-white mb-4">
        Server Configuration
      </h2>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Server URL
          </label>
          <div class="flex gap-2">
            <input
              v-model="serverUrl"
              type="text"
              placeholder="http://localhost:8000"
              class="flex-1 rounded-md border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
            <button
              :disabled="!serverUrl || testing"
              class="px-4 py-2 bg-gray-100 dark:bg-neutral-800 text-black dark:text-white rounded-md hover:bg-gray-200 dark:hover:bg-neutral-700 disabled:opacity-50"
              @click="testConnection"
            >
              {{ testing ? 'Testing...' : 'Test' }}
            </button>
            <button
              :disabled="!serverUrl"
              class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
              @click="saveServerUrl"
            >
              Save
            </button>
          </div>
          <p
            v-if="connectionStatus"
            class="mt-2 text-sm"
            :class="connectionStatus === 'success' ? 'text-green-600' : 'text-red-600'"
          >
            {{ connectionMessage }}
          </p>
        </div>
      </div>
    </div>

    <!-- Authentication -->
    <div class="mb-8 rounded-lg border border-gray-200 dark:border-neutral-800 p-4">
      <h2 class="text-lg font-semibold text-black dark:text-white mb-4">
        Authentication
      </h2>

      <!-- Not logged in -->
      <div v-if="!isAuthenticated">
        <div class="flex gap-4 mb-4">
          <button
            :class="authMode === 'login' ? 'bg-blue-500 text-white' : 'bg-gray-100 dark:bg-neutral-800 text-black dark:text-white'"
            class="px-4 py-2 rounded-md"
            @click="authMode = 'login'"
          >
            Login
          </button>
          <button
            :class="authMode === 'register' ? 'bg-blue-500 text-white' : 'bg-gray-100 dark:bg-neutral-800 text-black dark:text-white'"
            class="px-4 py-2 rounded-md"
            @click="authMode = 'register'"
          >
            Register
          </button>
        </div>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Username
            </label>
            <input
              v-model="username"
              type="text"
              class="w-full rounded-md border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>
          <div v-if="authMode === 'register'">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Email
            </label>
            <input
              v-model="email"
              type="email"
              class="w-full rounded-md border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Password
            </label>
            <input
              v-model="password"
              type="password"
              class="w-full rounded-md border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
          </div>
          <p
            v-if="authError"
            class="text-sm text-red-600"
          >
            {{ authError }}
          </p>
          <button
            :disabled="!username || !password || authLoading"
            class="w-full px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            @click="handleAuth"
          >
            {{ authLoading ? 'Processing...' : (authMode === 'login' ? 'Login' : 'Register') }}
          </button>
        </div>
      </div>

      <!-- Logged in -->
      <div
        v-else
        class="space-y-4"
      >
        <div class="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-md">
          <div>
            <p class="text-sm font-medium text-green-800 dark:text-green-400">
              Logged in as {{ userInfo?.username }}
            </p>
            <p class="text-xs text-green-600 dark:text-green-500">
              {{ userInfo?.email }}
            </p>
          </div>
          <button
            class="px-3 py-1 bg-red-500 text-white text-sm rounded-md hover:bg-red-600"
            @click="handleLogout"
          >
            Logout
          </button>
        </div>
      </div>
    </div>

    <!-- Sync Actions -->
    <div
      v-if="isAuthenticated"
      class="mb-8 rounded-lg border border-gray-200 dark:border-neutral-800 p-4"
    >
      <h2 class="text-lg font-semibold text-black dark:text-white mb-4">
        Sync Actions
      </h2>
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="font-medium text-black dark:text-white">
              Full Sync
            </p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Upload all local bookmarks to server
            </p>
          </div>
          <button
            :disabled="syncing"
            class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            @click="handleFullSync"
          >
            {{ syncing ? 'Syncing...' : 'Sync Now' }}
          </button>
        </div>

        <div
          v-if="lastSyncTime"
          class="text-sm text-gray-500 dark:text-gray-400"
        >
          Last sync: {{ lastSyncTime }}
        </div>

        <div
          v-if="syncResult"
          class="p-3 rounded-md"
          :class="syncResult.success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'"
        >
          <p :class="syncResult.success ? 'text-green-800 dark:text-green-400' : 'text-red-800 dark:text-red-400'">
            {{ syncResult.message }}
          </p>
        </div>
      </div>
    </div>

    <!-- Analytics Preview -->
    <div
      v-if="isAuthenticated && analytics"
      class="rounded-lg border border-gray-200 dark:border-neutral-800 p-4"
    >
      <h2 class="text-lg font-semibold text-black dark:text-white mb-4">
        Analytics Overview
      </h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="p-3 bg-gray-50 dark:bg-neutral-900 rounded-md">
          <p class="text-2xl font-bold text-black dark:text-white">
            {{ analytics.total_bookmarks }}
          </p>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Total Bookmarks
          </p>
        </div>
        <div class="p-3 bg-gray-50 dark:bg-neutral-900 rounded-md">
          <p class="text-2xl font-bold text-black dark:text-white">
            {{ analytics.total_domains }}
          </p>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Domains
          </p>
        </div>
        <div class="p-3 bg-gray-50 dark:bg-neutral-900 rounded-md">
          <p class="text-2xl font-bold text-black dark:text-white">
            {{ analytics.total_tags }}
          </p>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Tags
          </p>
        </div>
        <div class="p-3 bg-gray-50 dark:bg-neutral-900 rounded-md">
          <p class="text-2xl font-bold text-black dark:text-white">
            {{ analytics.dead_links_count }}
          </p>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Dead Links
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { backendClient } from '@/services/backend.js';
import BookmarkStorage from '@/storage/bookmark.js';
import AttributeStorage from '@/storage/attribute.js';

const bookmarkStorage = new BookmarkStorage();
const attributeStorage = new AttributeStorage();

const serverUrl = ref('http://localhost:8000');
const testing = ref(false);
const connectionStatus = ref(null);
const connectionMessage = ref('');

const authMode = ref('login');
const username = ref('');
const email = ref('');
const password = ref('');
const authLoading = ref(false);
const authError = ref('');

// 强制刷新计数器，用于触发响应式更新
const refreshCounter = ref(0);

const syncing = ref(false);
const syncResult = ref(null);
const lastSyncTime = ref(null);

const analytics = ref(null);

// 从 backendClient 获取登录状态和用户信息
const isAuthenticated = computed(() => {
  // 添加 refreshCounter 作为依赖，确保响应式更新
  refreshCounter.value; // eslint-disable-line no-unused-expressions
  return backendClient.isAuthenticated();
});

const userInfo = computed(() => {
  // 添加 refreshCounter 作为依赖，确保响应式更新
  refreshCounter.value; // eslint-disable-line no-unused-expressions
  return backendClient.getUserInfo();
});

// 强制刷新函数
const forceRefresh = () => {
  refreshCounter.value++;
};

const testConnection = async () => {
  testing.value = true;
  connectionStatus.value = null;
  try {
    const response = await fetch(`${serverUrl.value}/health`);
    if (response.ok) {
      connectionStatus.value = 'success';
      connectionMessage.value = 'Connection successful!';
    } else {
      throw new Error('Server returned error');
    }
  } catch (e) {
    connectionStatus.value = 'error';
    connectionMessage.value = `Connection failed: ${e.message}`;
  } finally {
    testing.value = false;
  }
};

const saveServerUrl = async () => {
  await backendClient.setServerUrl(serverUrl.value);
  connectionStatus.value = 'success';
  connectionMessage.value = 'Server URL saved!';
};

const loadAnalytics = async () => {
  try {
    analytics.value = await backendClient.getAnalyticsOverview();
  } catch (e) {
    console.error('Failed to load analytics:', e);
  }
};

const handleAuth = async () => {
  authLoading.value = true;
  authError.value = '';
  try {
    if (authMode.value === 'register') {
      await backendClient.register(username.value, email.value, password.value);
    }
    await backendClient.login(username.value, password.value);

    // 清空输入框
    username.value = '';
    email.value = '';
    password.value = '';

    // 强制刷新 UI
    forceRefresh();

    // 加载分析数据
    await loadAnalytics();
  } catch (e) {
    authError.value = e.message;
  } finally {
    authLoading.value = false;
  }
};

const handleLogout = async () => {
  await backendClient.logout();
  analytics.value = null;
  // 强制刷新 UI
  forceRefresh();
};

/**
 * 分批获取所有书签，避免一次性加载导致内存问题
 * @param {Function} onProgress - 进度回调函数
 * @returns {Promise<Array>} 所有书签数组
 */
const getAllBookmarks = async (onProgress) => {
  const limit = 1000; // 每批1000条
  let skip = 0;
  const allBookmarks = [];

  while (true) {
    const batch = await bookmarkStorage.search([], skip, limit, 'desc');

    // 检查是否获取到数据
    if (!batch || batch.length === 0) break;

    allBookmarks.push(...batch);

    // 报告进度
    if (onProgress) {
      onProgress(allBookmarks.length);
    }

    // 如果返回的数据少于limit，说明已经是最后一批
    if (batch.length < limit) break;

    skip += limit;
  }

  return allBookmarks;
};

const handleFullSync = async () => {
  syncing.value = true;
  syncResult.value = null;
  try {
    // 检查认证状态
    if (!backendClient.isAuthenticated()) {
      throw new Error('Not authenticated. Please login first.');
    }

    // 检查服务器配置
    if (!backendClient.serverUrl) {
      throw new Error('Server URL not configured. Please configure server URL first.');
    }

    // 分批获取所有书签，避免一次性加载过多数据导致崩溃
    console.log('[Sync] Fetching local bookmarks in batches...');
    const localBookmarks = await getAllBookmarks((count) => {
      console.log(`[Sync] Loaded ${count} bookmarks...`);
    });

    if (!localBookmarks || !Array.isArray(localBookmarks)) {
      throw new Error('Failed to fetch local bookmarks - invalid data');
    }

    console.log(`[Sync] Starting sync with ${localBookmarks.length} local bookmarks`);

    // 调试:查看第一个书签的数据
    if (localBookmarks.length > 0) {
      console.log('[Sync] Sample bookmark:', JSON.stringify(localBookmarks[0], null, 2));
    } else {
      console.warn('[Sync] No bookmarks to sync');
    }

    const result = await backendClient.fullSync(localBookmarks);

    // 处理服务器返回的书签数据
    console.log(`[Sync] Server returned ${result.bookmarks.length} bookmarks`);

    // 将服务器返回的书签保存到本地
    // 1. 创建本地书签ID映射
    const localBookmarksMap = new Map(localBookmarks.map((b) => [b.id, b]));

    // 2. 处理服务器书签
    let newCount = 0;
    let updatedCount = 0;

    for (const serverBookmark of result.bookmarks) {
      // 将服务器格式转换为本地格式
      const transformedBookmark = {
        id: serverBookmark.browser_id,
        url: serverBookmark.url,
        title: serverBookmark.title,
        description: serverBookmark.description,
        domain: serverBookmark.domain,
        favicon: serverBookmark.favicon,
        image: serverBookmark.image,
        tags: serverBookmark.tags || [],
        keywords: serverBookmark.keywords || [],
        notes: serverBookmark.notes,
        folderName: serverBookmark.folder_name,
        folderId: serverBookmark.folder_id,
        pinned: serverBookmark.pinned,
        httpStatus: serverBookmark.http_status,
        dateAdded: serverBookmark.date_added,
        createdAt: serverBookmark.created_at,
        updatedAt: serverBookmark.updated_at,
      };

      if (localBookmarksMap.has(transformedBookmark.id)) {
        // 更新现有书签
        await bookmarkStorage.update(transformedBookmark.id, transformedBookmark);
        updatedCount++;
      } else {
        // 创建新书签
        await bookmarkStorage.create(transformedBookmark);
        newCount++;
      }
    }

    console.log(`[Sync] Applied changes: ${newCount} new, ${updatedCount} updated`);

    // 重新生成属性数据（域名、标签等）
    console.log('[Sync] Refreshing attributes...');
    await attributeStorage.refresh();
    console.log('[Sync] Attributes refreshed');

    // 通知其他页面刷新数据
    try {
      await chrome.runtime.sendMessage({
        type: 'BOOKMARKS_SYNCED',
        data: { newCount, updatedCount, total: result.bookmarks.length },
      });
    } catch (err) {
      console.log('[Sync] No listeners for sync message (this is ok)');
    }

    syncResult.value = {
      success: true,
      message: `Synced ${result.bookmarks.length} bookmarks (${newCount} new, ${updatedCount} updated). ${result.conflicts.length} conflicts resolved.`,
    };
    lastSyncTime.value = new Date().toLocaleString();

    // 保存最后同步时间
    await chrome.storage.local.set({
      favbox_last_sync: result.server_timestamp,
    });

    loadAnalytics();
  } catch (e) {
    console.error('[Sync] Full error object:', e);
    console.error('[Sync] Error message:', e.message);
    console.error('[Sync] Error stack:', e.stack);
    syncResult.value = {
      success: false,
      message: `Sync failed: ${e.message}`,
    };
  } finally {
    syncing.value = false;
  }
};

onMounted(async () => {
  await backendClient.init();
  if (backendClient.serverUrl) {
    serverUrl.value = backendClient.serverUrl;
  }

  // 强制刷新 UI 以反映初始化后的登录状态
  forceRefresh();

  // 如果已登录，加载分析数据
  if (backendClient.isAuthenticated()) {
    await loadAnalytics();
  }

  const stored = await chrome.storage.local.get('favbox_last_sync');
  if (stored.favbox_last_sync) {
    lastSyncTime.value = new Date(stored.favbox_last_sync).toLocaleString();
  }
});
</script>
