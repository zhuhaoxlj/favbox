/**
 * @typedef {object} Bookmark
 * @property {string|number} id - 书签唯一标识符
 * @property {string} browserId - 浏览器原生书签ID
 * @property {string} url - 书签URL
 * @property {string} title - 书签标题
 * @property {string} [description] - 页面描述
 * @property {string[]} tags - 标签列表
 * @property {string[]} keywords - 关键词列表
 * @property {string} domain - 域名
 * @property {string} [favicon] - 网站图标URL
 * @property {string} [image] - 预览图URL
 * @property {string} [notes] - 用户备注
 * @property {string} folderName - 所属文件夹名称
 * @property {string} folderId - 所属文件夹ID
 * @property {number} pinned - 是否置顶 (0或1)
 * @property {number} [httpStatus] - HTTP状态码
 * @property {number} dateAdded - 添加时间戳
 * @property {string} [createdAt] - 创建时间ISO字符串
 * @property {string} [updatedAt] - 更新时间ISO字符串
 * @property {boolean} deleted - 是否已删除
 */

/**
 * @typedef {object} SearchQuery
 * @property {string} key - 查询键（folder/tag/domain/keyword/term/dateAdded）
 * @property {string|string[]} value - 查询值
 */

/**
 * BookmarkStorage - 书签存储管理类
 * 提供书签的CRUD操作和高级查询功能
 */
import useConnection from './idb/connection';

export default class BookmarkStorage {
  /**
   * 批量创建书签
   * @param {Bookmark[]} data - 书签数组
   * @returns {Promise<number>} 成功插入的记录数
   */
  async createMany(data) {
    const connection = await useConnection();
    const result = await connection.insert({
      into: 'bookmarks',
      values: data,
      validation: false,
      skipDataCheck: true,
      ignore: true,
    });
    return result;
  }

  /**
   * 查询指定ID之后的书签（用于分页）
   * @param {string|number} id - 起始ID
   * @param {number} limit - 返回数量限制
   * @returns {Promise<Bookmark[]>} 书签列表
   */
  async selectAfterId(id, limit) {
    const connection = await useConnection();
    const query = {
      from: 'bookmarks',
      limit,
      order: { by: 'id', type: 'asc' },
      where: id ? { id: { '>': id } } : null,
    };
    return connection.select(query);
  }

  /**
   * 高级搜索书签
   * 支持按文件夹、标签、域名、关键词、搜索词、日期范围查询
   * @param {SearchQuery[]} query - 查询条件数组
   * @param {number} [skip] - 跳过记录数
   * @param {number} [limit] - 返回数量限制
   * @param {string} [sortDirection] - 排序方向 ('asc' | 'desc')
   * @returns {Promise<Bookmark[]>} 书签列表
   */
  async search(query, skip = 0, limit = 50, sortDirection = 'desc') {
    const connection = await useConnection();
    const queryParams = {};
    const whereConditions = [];
    query.forEach(({ key, value }) => {
      (queryParams[key] ??= []).push(value);
    });
    const conditions = [
      { key: 'folder', condition: { folderName: { in: queryParams.folder } } },
      { key: 'tag', condition: { tags: { in: queryParams.tag } } },
      { key: 'domain', condition: { domain: { in: queryParams.domain } } },
      { key: 'keyword', condition: { keywords: { in: queryParams.keyword } } },
      { key: 'id', condition: { id: { in: queryParams.id } } },
    ];
    conditions.forEach(({ key, condition }) => {
      if (queryParams[key]) {
        whereConditions.push(condition);
      }
    });
    if (queryParams?.term) {
      const [term] = queryParams.term;
      const regexPattern = term.split(/\s+/).map((word) => `(?=.*${word})`).join('');
      const regex = new RegExp(`^${regexPattern}.*$`, 'i');
      whereConditions.push({
        title: { regex },
        or: {
          description: { regex },
          or: {
            url: { regex },
            or: {
              domain: { like: `%${term}%` },
              or: {
                keywords: { regex },
              },
            },
          },
        },
      });
    }
    if (queryParams?.dateAdded?.[0]) {
      const [startStr, endStr] = queryParams.dateAdded[0].split('~');
      const startDate = new Date(startStr);
      const endDate = new Date(endStr);
      const low = startDate.setHours(0, 0, 0, 0);
      const high = endDate.setHours(23, 59, 59, 999);
      whereConditions.push({
        dateAdded: {
          '-': { low, high },
        },
      });
    }
    return connection.select({
      from: 'bookmarks',
      distinct: true,
      limit,
      skip,
      order: {
        by: 'dateAdded',
        type: sortDirection,
      },
      where: whereConditions.length === 0 ? null : whereConditions,
    });
  }

  /**
   * 获取书签总数
   * @returns {Promise<number>} 书签总数
   */
  async total() {
    const connection = await useConnection();
    return connection.count({
      from: 'bookmarks',
    });
  }

  /**
   * 创建单个书签
   * @param {Bookmark} entity - 书签对象
   * @returns {Promise<number>} 成功插入的记录数
   */
  async create(entity) {
    const connection = await useConnection();
    return connection.insert({
      into: 'bookmarks',
      values: [entity],
    });
  }

  /**
   * 更新书签HTTP状态码
   * @param {string|number} id - 书签ID
   * @param {number} status - HTTP状态码
   * @returns {Promise<number>} 更新的记录数
   */
  async updateHttpStatusById(id, status) {
    const connection = await useConnection();
    return connection.update({
      in: 'bookmarks',
      set: {
        httpStatus: parseInt(status, 10),
        updatedAt: new Date().toISOString(),
      },
      where: {
        id,
      },
    });
  }

  /**
   * 将所有书签HTTP状态设置为200
   * @returns {Promise<number>} 更新的记录数
   */
  async setOK() {
    const connection = await useConnection();
    return connection.update({
      in: 'bookmarks',
      set: { httpStatus: 200 },
    });
  }

  /**
   * 获取置顶的书签
   * @param {number} [skip] - 跳过记录数
   * @param {number} [limit] - 返回数量限制
   * @param {string} [term] - 搜索词
   * @returns {Promise<Bookmark[]>} 置顶书签列表
   */
  async getPinnedBookmarks(skip = 0, limit = 50, term = '') {
    const connection = await useConnection();
    const whereConditions = [{ pinned: 1 }];
    if (term) {
      const regexPattern = term.split(/\s+/).map((word) => `(?=.*${word})`).join('');
      const regex = new RegExp(`^${regexPattern}.*$`, 'i');
      whereConditions.push({
        notes: { regex },
        or: {
          title: { regex },
          or: {
            description: { regex },
            or: {
              domain: { like: `%${term}%` },
            },
          },
        },
      });
    }
    return connection.select({
      from: 'bookmarks',
      limit,
      skip,
      order: {
        by: 'updatedAt',
        type: 'desc',
      },
      where: whereConditions,
    });
  }

  async updatePinStatusById(id, status) {
    const connection = await useConnection();
    return connection.update({
      in: 'bookmarks',
      set: {
        pinned: parseInt(status, 10),
        updatedAt: new Date().toISOString(),
      },
      where: {
        id,
      },
    });
  }

  /**
   * 更新书签
   * @param {string|number} id - 书签ID
   * @param {Partial<Bookmark>} data - 要更新的字段
   * @returns {Promise<number>} 更新的记录数
   */
  async update(id, data) {
    const connection = await useConnection();
    return connection.update({
      in: 'bookmarks',
      set: data,
      where: {
        id,
      },
    });
  }

  /**
   * 批量删除书签
   * @param {Array<string|number>} ids - 书签ID数组
   * @returns {Promise<number>} 删除的记录数
   */
  async removeByIds(ids) {
    const connection = await useConnection();
    const result = await connection.remove({
      from: 'bookmarks',
      where: {
        id: {
          in: ids,
        },
      },
    });
    return result;
  }

  /**
   * 删除单个书签
   * @param {string|number} id - 书签ID
   * @returns {Promise<number>} 删除的记录数
   */
  async removeById(id) {
    const connection = await useConnection();
    return connection.remove({
      from: 'bookmarks',
      where: { id },
    });
  }

  async createMultiple(data) {
    const connection = await useConnection();
    return connection.insert({
      into: 'bookmarks',
      values: data,
      validation: false,
      skipDataCheck: true,
      ignore: true,
    });
  }

  async getIds(ids) {
    const connection = await useConnection();
    const response = await connection.select({
      from: 'bookmarks',
      where: {
        id: {
          in: ids,
        },
      },
    });
    return response.map((i) => i.id);
  }

  async getByFolderName(folderId) {
    const connection = await useConnection();
    const response = await connection.select({
      from: 'bookmarks',
      limit: 1,
      where: {
        folderId,
      },
    });

    return response.length === 1 ? response.shift() : null;
  }

  async updateFolderNameByFolderId(id, title) {
    const connection = await useConnection();
    return connection.update({
      in: 'bookmarks',
      set: {
        folderName: title,
        folderId: id,
      },
      where: {
        folderId: id,
      },
    });
  }

  /**
   * 根据ID获取书签
   * @param {string|number} id - 书签ID
   * @returns {Promise<Bookmark|null>} 书签对象，不存在时返回null
   */
  async getById(id) {
    const connection = await useConnection();
    const response = await connection.select({
      from: 'bookmarks',
      limit: 1,
      where: {
        id,
      },
    });

    return response.length === 1 ? response.shift() : null;
  }

  async getByUrl(url) {
    const connection = await useConnection();
    const response = await connection.select({
      from: 'bookmarks',
      limit: 1,
      where: {
        url: String(url),
      },
    });

    return response.length === 1 ? response.shift() : null;
  }

  async getTags() {
    const connection = await useConnection();
    const response = await connection.select({
      from: 'bookmarks',
      flatten: ['tags'],
      groupBy: 'tags',
      order: {
        by: 'tags',
        type: 'asc',
      },
    });
    return response.map((item) => item.tags);
  }

  async updateStatusByIds(status, ids) {
    const connection = await useConnection();
    return connection.update({
      in: 'bookmarks',
      set: {
        httpStatus: status,
      },
      where: {
        id: {
          in: ids,
        },
      },
    });
  }

  async updateNotesById(id, notes) {
    const connection = await useConnection();
    return connection.update({
      in: 'bookmarks',
      set: {
        notes,
        updatedAt: new Date().toISOString(),
      },
      where: {
        id,
      },
    });
  }

  async updateImageById(id, image) {
    const connection = await useConnection();
    return connection.update({
      in: 'bookmarks',
      set: {
        image,
      },
      where: {
        id,
      },
    });
  }

  async getBookmarksByHttpStatusCode(statuses, skip = 0, limit = 50) {
    const connection = await useConnection();
    return connection.select({
      from: 'bookmarks',
      limit,
      skip,
      order: {
        by: 'id',
        type: 'desc',
      },
      where: {
        httpStatus: {
          in: statuses,
        },
      },
    });
  }

  async getTotalByHttpStatus(statuses) {
    const connection = await useConnection();
    return connection.count({
      from: 'bookmarks',
      order: {
        by: 'id',
        type: 'desc',
      },
      where: {
        httpStatus: {
          in: statuses,
        },
      },
    });
  }

  async getAllIds() {
    const connection = await useConnection();
    const response = await connection.select({
      from: 'bookmarks',
      columns: ['id'],
    });
    return response.map((i) => i.id);
  }

  /**
   * 获取重复书签分组
   * @param {number} [skip] - 跳过分组数
   * @param {number} [limit] - 返回分组数限制
   * @returns {Promise<{groups: Array<{url: string, bookmarks: Bookmark[], count: number, firstAdded: Bookmark, lastAdded: Bookmark}>, total: number, hasMore: boolean}>} 重复书签分组结果
   */
  async getDuplicatesGrouped(skip = 0, limit = 50) {
    const connection = await useConnection();

    // Get all URLs with the number of duplicates
    const groupedResults = await connection.select({
      from: 'bookmarks',
      groupBy: 'url',
      aggregate: {
        count: ['id'],
      },
    });

    // Filter only groups with duplicates (2+ bookmarks)
    const duplicateGroups = groupedResults.filter((group) => group['count(id)'] > 1);

    // Sort by url (alphabetically)
    duplicateGroups.sort((a, b) => String(a.url).localeCompare(String(b.url)));

    // Apply pagination
    const paginatedGroups = duplicateGroups.slice(skip, skip + limit);

    // Get all bookmarks for the current page in one query
    const urls = paginatedGroups.map((group) => group.url);
    const allBookmarks = await connection.select({
      from: 'bookmarks',
      where: { url: { in: urls } },
      order: {
        by: 'dateAdded',
        type: 'desc',
      },
    });

    // Group bookmarks by URL
    const bookmarksByUrl = {};
    allBookmarks.forEach((bookmark) => {
      if (!bookmarksByUrl[bookmark.url]) {
        bookmarksByUrl[bookmark.url] = [];
      }
      bookmarksByUrl[bookmark.url].push(bookmark);
    });

    // Form the result
    const groupsWithDetails = paginatedGroups.map((group) => {
      const bookmarks = bookmarksByUrl[group.url] || [];
      return {
        url: group.url,
        bookmarks,
        count: group['count(id)'],
        firstAdded: bookmarks[bookmarks.length - 1], // Oldest
        lastAdded: bookmarks[0], // Newest
      };
    });

    return {
      groups: groupsWithDetails,
      total: duplicateGroups.length,
      hasMore: skip + limit < duplicateGroups.length,
    };
  }
}
