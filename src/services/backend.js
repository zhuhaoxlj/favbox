/**
 * FavBox Backend API Client
 * Handles communication with the Python backend service
 */

const STORAGE_KEYS = {
  SERVER_URL: 'favbox_server_url',
  AUTH_TOKEN: 'favbox_auth_token',
  LAST_SYNC: 'favbox_last_sync',
  USER_INFO: 'favbox_user_info',
};

class BackendClient {
  constructor() {
    this.serverUrl = null;
    this.token = null;
    this.userInfo = null;
    this.ws = null;
    this.wsReconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.eventListeners = new Map();
  }

  /**
   * Initialize client from stored settings
   */
  async init() {
    const stored = await chrome.storage.local.get([
      STORAGE_KEYS.SERVER_URL,
      STORAGE_KEYS.AUTH_TOKEN,
      STORAGE_KEYS.USER_INFO,
    ]);
    this.serverUrl = stored[STORAGE_KEYS.SERVER_URL] || null;
    this.token = stored[STORAGE_KEYS.AUTH_TOKEN] || null;
    this.userInfo = stored[STORAGE_KEYS.USER_INFO] || null;

    // 如果有 token 但没有用户信息，或者需要验证 token 有效性，尝试获取用户信息
    if (this.token && !this.userInfo) {
      try {
        this.userInfo = await this.getMe();
        await chrome.storage.local.set({ [STORAGE_KEYS.USER_INFO]: this.userInfo });
      } catch (e) {
        // Token 可能已过期，清除认证状态
        console.error('[BackendClient] Failed to restore user info, clearing auth:', e);
        await this.logout();
      }
    }

    // 如果已认证且有用户信息，连接 WebSocket
    if (this.token && this.userInfo) {
      this.connectWebSocket();
    }

    return this;
  }

  /**
   * Check if client is configured and authenticated
   */
  isConfigured() {
    return !!this.serverUrl;
  }

  isAuthenticated() {
    return !!this.token && !!this.userInfo;
  }

  getUserInfo() {
    return this.userInfo;
  }

  /**
   * Configure server URL
   */
  async setServerUrl(url) {
    // Remove trailing slash
    this.serverUrl = url.replace(/\/+$/, '');
    await chrome.storage.local.set({ [STORAGE_KEYS.SERVER_URL]: this.serverUrl });
  }

  /**
   * Make authenticated API request
   */
  async request(endpoint, options = {}) {
    if (!this.serverUrl) {
      throw new Error('Server URL not configured');
    }

    const url = `${this.serverUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (response.status === 401) {
      // Token expired, clear auth
      await this.logout();
      throw new Error('Authentication expired');
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const error = await response.json();
        errorMessage = error.detail || error.message || errorMessage;
      } catch (e) {
        errorMessage = `${errorMessage} - ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    if (response.status === 204) {
      return null;
    }

    return response.json();
  }

  // ==================== Authentication ====================

  /**
   * Register new user
   */
  async register(username, email, password) {
    return this.request('/api/auth/register', {
      method: 'POST',
      body: { username, email, password },
    });
  }

  /**
   * Login and store token
   */
  async login(username, password) {
    const data = await this.request('/api/auth/login', {
      method: 'POST',
      body: { username, password },
    });

    this.token = data.access_token;
    await chrome.storage.local.set({ [STORAGE_KEYS.AUTH_TOKEN]: this.token });

    // Get user info
    this.userInfo = await this.getMe();
    await chrome.storage.local.set({ [STORAGE_KEYS.USER_INFO]: this.userInfo });

    // Connect WebSocket
    this.connectWebSocket();

    return data;
  }

  /**
   * Logout and clear stored data
   */
  async logout() {
    this.token = null;
    this.userInfo = null;
    this.disconnectWebSocket();
    await chrome.storage.local.remove([
      STORAGE_KEYS.AUTH_TOKEN,
      STORAGE_KEYS.USER_INFO,
      STORAGE_KEYS.LAST_SYNC,
    ]);
  }

  /**
   * Get current user info
   */
  async getMe() {
    return this.request('/api/auth/me');
  }

  // ==================== Bookmark Sync ====================

  /**
   * Full sync - send all bookmarks to server
   */
  async fullSync(bookmarks) {
    console.log('[BackendClient] fullSync called with', bookmarks.length, 'bookmarks');
    console.log('[BackendClient] Sample bookmark before transform:', bookmarks[0]);

    const transformedBookmarks = bookmarks.map((b) => this._transformBookmarkForServer(b));
    console.log('[BackendClient] Sample bookmark after transform:', transformedBookmarks[0]);

    const requestBody = {
      bookmarks: transformedBookmarks,
      client_timestamp: new Date().toISOString(),
    };

    console.log('[BackendClient] Request body size:', JSON.stringify(requestBody).length, 'bytes');

    const data = await this.request('/api/bookmarks/sync', {
      method: 'POST',
      body: requestBody,
    });

    await chrome.storage.local.set({
      [STORAGE_KEYS.LAST_SYNC]: data.server_timestamp,
    });

    return data;
  }

  /**
   * Incremental sync - send only changes
   */
  async incrementalSync(changes) {
    const stored = await chrome.storage.local.get(STORAGE_KEYS.LAST_SYNC);
    const lastSync = stored[STORAGE_KEYS.LAST_SYNC] || new Date(0).toISOString();

    const data = await this.request('/api/bookmarks/sync/incremental', {
      method: 'POST',
      body: {
        changes: changes.map((c) => this._transformBookmarkForServer(c)),
        last_sync_at: lastSync,
      },
    });

    await chrome.storage.local.set({
      [STORAGE_KEYS.LAST_SYNC]: data.server_timestamp,
    });

    return data;
  }

  /**
   * Get all bookmarks from server
   */
  async getBookmarks() {
    return this.request('/api/bookmarks');
  }

  /**
   * Get changes since last sync
   */
  async getChanges(since) {
    return this.request(`/api/bookmarks/changes?since=${encodeURIComponent(since)}`);
  }

  /**
   * Delete a single bookmark
   */
  async deleteBookmark(browserId) {
    return this.request(`/api/bookmarks/${browserId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Transform bookmark to server format
   */
  _transformBookmarkForServer(bookmark) {
    return {
      browser_id: bookmark.id,
      url: bookmark.url,
      title: bookmark.title,
      description: bookmark.description || null,
      domain: bookmark.domain || null,
      favicon: bookmark.favicon || null,
      image: bookmark.image || null,
      tags: bookmark.tags || [],
      keywords: bookmark.keywords || [],
      notes: bookmark.notes || null,
      folder_name: bookmark.folderName || null,
      folder_id: bookmark.folderId || null,
      pinned: bookmark.pinned || 0,
      http_status: bookmark.httpStatus || null,
      date_added: bookmark.dateAdded || null,
      updated_at: bookmark.updatedAt || null,
      deleted: bookmark.deleted || false,
    };
  }

  /**
   * Transform bookmark from server format
   */
  _transformBookmarkFromServer(bookmark) {
    return {
      id: bookmark.browser_id,
      url: bookmark.url,
      title: bookmark.title,
      description: bookmark.description,
      domain: bookmark.domain,
      favicon: bookmark.favicon,
      image: bookmark.image,
      tags: bookmark.tags || [],
      keywords: bookmark.keywords || [],
      notes: bookmark.notes,
      folderName: bookmark.folder_name,
      folderId: bookmark.folder_id,
      pinned: bookmark.pinned,
      httpStatus: bookmark.http_status,
      dateAdded: bookmark.date_added,
      createdAt: bookmark.created_at,
      updatedAt: bookmark.updated_at,
    };
  }

  // ==================== Analytics ====================

  /**
   * Get analytics overview
   */
  async getAnalyticsOverview() {
    return this.request('/api/analytics/overview');
  }

  /**
   * Get domain statistics
   */
  async getDomainStats(limit = 20) {
    return this.request(`/api/analytics/domains?limit=${limit}`);
  }

  /**
   * Get tag statistics
   */
  async getTagStats(limit = 50) {
    return this.request(`/api/analytics/tags?limit=${limit}`);
  }

  /**
   * Get timeline statistics
   */
  async getTimelineStats(period = 'day') {
    return this.request(`/api/analytics/timeline?period=${period}`);
  }

  /**
   * Get duplicate bookmarks
   */
  async getDuplicates() {
    return this.request('/api/analytics/duplicates');
  }

  // ==================== Collections ====================

  /**
   * Get user's collections
   */
  async getCollections() {
    return this.request('/api/collections');
  }

  /**
   * Get shared collections
   */
  async getSharedCollections() {
    return this.request('/api/collections/shared');
  }

  /**
   * Create collection
   */
  async createCollection(name, description = null, isPublic = false) {
    return this.request('/api/collections', {
      method: 'POST',
      body: { name, description, is_public: isPublic },
    });
  }

  /**
   * Get collection with bookmarks
   */
  async getCollection(id) {
    return this.request(`/api/collections/${id}`);
  }

  /**
   * Update collection
   */
  async updateCollection(id, data) {
    return this.request(`/api/collections/${id}`, {
      method: 'PUT',
      body: data,
    });
  }

  /**
   * Delete collection
   */
  async deleteCollection(id) {
    return this.request(`/api/collections/${id}`, {
      method: 'DELETE',
    });
  }

  /**
   * Add bookmark to collection
   */
  async addToCollection(collectionId, bookmarkId) {
    return this.request(`/api/collections/${collectionId}/bookmarks/${bookmarkId}`, {
      method: 'POST',
    });
  }

  /**
   * Remove bookmark from collection
   */
  async removeFromCollection(collectionId, bookmarkId) {
    return this.request(`/api/collections/${collectionId}/bookmarks/${bookmarkId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Share collection with user
   */
  async shareCollection(collectionId, userId, permission = 'read') {
    return this.request(`/api/collections/${collectionId}/share`, {
      method: 'POST',
      body: { user_id: userId, permission },
    });
  }

  // ==================== WebSocket ====================

  /**
   * Connect to WebSocket for real-time sync
   */
  connectWebSocket() {
    if (!this.serverUrl || !this.token) {
      return;
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = `${this.serverUrl.replace(/^http/, 'ws')}/api/ws?token=${this.token}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[FavBox] WebSocket connected');
      this.wsReconnectAttempts = 0;
      this._emit('ws:connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._handleWebSocketMessage(data);
      } catch (e) {
        console.error('[FavBox] WebSocket message parse error:', e);
      }
    };

    this.ws.onclose = () => {
      console.log('[FavBox] WebSocket disconnected');
      this._emit('ws:disconnected');
      this._scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('[FavBox] WebSocket error:', error);
      this._emit('ws:error', error);
    };
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Handle incoming WebSocket messages
   */
  _handleWebSocketMessage(data) {
    switch (data.type) {
      case 'connected':
        console.log(`[FavBox] Connected as user ${data.user_id}, ${data.connections} device(s)`);
        break;

      case 'bookmark_created':
        this._emit('bookmark:created', this._transformBookmarkFromServer(data.bookmark));
        break;

      case 'bookmark_updated':
        this._emit('bookmark:updated', this._transformBookmarkFromServer(data.bookmark));
        break;

      case 'bookmark_deleted':
        this._emit('bookmark:deleted', { id: data.browser_id });
        break;

      case 'ping':
        this.ws?.send(JSON.stringify({ type: 'pong' }));
        break;

      default:
        console.log('[FavBox] Unknown WebSocket message:', data);
    }
  }

  /**
   * Schedule WebSocket reconnection
   */
  _scheduleReconnect() {
    if (this.wsReconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[FavBox] Max reconnect attempts reached, will retry in 5 minutes');
      // 长时间等待后重置计数器，避免永久放弃
      setTimeout(() => {
        console.log('[FavBox] Resetting reconnect attempts after long delay');
        this.wsReconnectAttempts = 0;
        if (this.token) {
          this.connectWebSocket();
        }
      }, 5 * 60 * 1000); // 5分钟后重试
      return;
    }

    // 指数退避，但限制最大延迟为30秒
    const delay = Math.min(
      this.reconnectDelay * 2 ** this.wsReconnectAttempts,
      30000, // 最大延迟30秒
    );
    this.wsReconnectAttempts++;

    console.log(`[FavBox] Reconnecting in ${delay}ms (attempt ${this.wsReconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      if (this.token) {
        this.connectWebSocket();
      }
    }, delay);
  }

  /**
   * Manually reconnect WebSocket
   * Resets reconnection attempts and tries to connect immediately
   */
  reconnect() {
    console.log('[FavBox] Manual reconnect requested');
    this.wsReconnectAttempts = 0;
    this.disconnectWebSocket();
    if (this.token) {
      this.connectWebSocket();
    }
  }

  // ==================== Event System ====================

  /**
   * Subscribe to events
   */
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);
  }

  /**
   * Unsubscribe from events
   */
  off(event, callback) {
    if (!this.eventListeners.has(event)) return;
    const listeners = this.eventListeners.get(event);
    const index = listeners.indexOf(callback);
    if (index > -1) {
      listeners.splice(index, 1);
    }
  }

  /**
   * Emit event
   */
  _emit(event, data) {
    if (!this.eventListeners.has(event)) return;
    for (const callback of this.eventListeners.get(event)) {
      try {
        callback(data);
      } catch (e) {
        console.error(`[FavBox] Event handler error for ${event}:`, e);
      }
    }
  }
}

// Export singleton instance
export const backendClient = new BackendClient();
export default backendClient;
