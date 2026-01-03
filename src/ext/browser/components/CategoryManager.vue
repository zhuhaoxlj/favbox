<template>
  <div class="p-6 max-w-6xl mx-auto">
    <!-- 页面标题 -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
          📁 分类管理
        </h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          管理书签分类，支持层级结构
        </p>
      </div>

      <div class="flex gap-2">
        <button
          @click="showCreateModal = true"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          ➕ 新建分类
        </button>

        <button
          @click="initializeDefaults"
          class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
          v-if="categories.length === 0"
        >
          🚀 初始化默认分类
        </button>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6" v-if="stats">
      <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
        <div class="text-sm text-gray-600 dark:text-gray-400">总分类数</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white">
          {{ stats.total_categories || 0 }}
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
        <div class="text-sm text-gray-600 dark:text-gray-400">顶级分类</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white">
          {{ stats.root_categories || 0 }}
        </div>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
        <div class="text-sm text-gray-600 dark:text-gray-400">已分类书签</div>
        <div class="text-2xl font-bold text-gray-900 dark:text-white">
          {{ stats.total_bookmarks_in_categories || 0 }}
        </div>
      </div>
    </div>

    <!-- 分类列表 -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div v-if="loading" class="p-8 text-center">
        <div class="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
        <p class="mt-2 text-gray-600 dark:text-gray-400">加载中...</p>
      </div>

      <div v-else-if="categories.length === 0" class="p-8 text-center">
        <p class="text-gray-500 dark:text-gray-400 mb-4">
          📭 还没有分类，点击右上角创建或初始化默认分类
        </p>
      </div>

      <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
        <div
          v-for="category in categories"
          :key="category.id"
          class="border-b border-gray-200 dark:border-gray-700"
        >
          <!-- 分类项 -->
          <div
            class="p-4 hover:bg-gray-50 dark:hover:bg-gray-750 transition cursor-pointer"
            @click="toggleCategory(category.id)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <!-- 展开/收起图标 -->
                <span class="text-lg text-gray-500">
                  {{ isExpanded(category.id) ? '▼' : '▶' }}
                </span>

                <!-- 图标 -->
                <span class="text-2xl">{{ category.icon || '📁' }}</span>

                <!-- 分类信息 -->
                <div>
                  <div class="flex items-center gap-2">
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                      {{ category.name }}
                    </h3>
                    <span
                      v-if="category.color"
                      class="w-4 h-4 rounded"
                      :style="{ backgroundColor: category.color }"
                    ></span>
                  </div>

                  <p v-if="category.description" class="text-sm text-gray-600 dark:text-gray-400">
                    {{ category.description }}
                  </p>

                  <!-- 关键词标签 -->
                  <div v-if="category.keywords && category.keywords.length" class="mt-2 flex gap-1 flex-wrap">
                    <span
                      v-for="keyword in category.keywords.slice(0, 5)"
                      :key="keyword"
                      class="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded"
                    >
                      {{ keyword }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- 书签数量和操作 -->
              <div class="flex items-center gap-4">
                <div class="text-center">
                  <div class="text-2xl font-bold text-gray-900 dark:text-white">
                    {{ category.bookmark_count }}
                  </div>
                  <div class="text-xs text-gray-600 dark:text-gray-400">书签</div>
                </div>

                <div class="flex gap-2" @click.stop>
                  <button
                    @click="editCategory(category)"
                    class="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900 rounded transition"
                    title="编辑"
                  >
                    ✏️
                  </button>

                  <button
                    @click="confirmDelete(category)"
                    class="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900 rounded transition"
                    title="删除"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 展开的书签列表 -->
          <div v-if="isExpanded(category.id)" class="bg-gray-50 dark:bg-gray-900">
            <!-- 加载中 -->
            <div v-if="isLoadingBookmarks(category.id)" class="p-8 text-center">
              <div class="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
              <p class="mt-2 text-gray-600 dark:text-gray-400">加载书签中...</p>
            </div>

            <!-- 书签列表 -->
            <div v-else-if="getCategoryBookmarksData(category.id).length > 0" class="p-4">
              <div class="space-y-2">
                <div
                  v-for="bookmark in getCategoryBookmarksData(category.id)"
                  :key="bookmark.id"
                  class="bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm hover:shadow-md transition"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="flex-1 min-w-0">
                      <!-- 标题和链接 -->
                      <a
                        :href="bookmark.url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium truncate block"
                      >
                        {{ bookmark.title || bookmark.url }}
                      </a>

                      <!-- 描述 -->
                      <p v-if="bookmark.description" class="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                        {{ bookmark.description }}
                      </p>

                      <!-- 标签 -->
                      <div v-if="bookmark.ai_tags && bookmark.ai_tags.length" class="mt-2 flex gap-1 flex-wrap">
                        <span
                          v-for="tag in bookmark.ai_tags.slice(0, 3)"
                          :key="tag"
                          class="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded"
                        >
                          {{ tag }}
                        </span>
                      </div>
                    </div>

                    <!-- 操作按钮 -->
                    <div class="flex gap-2 flex-shrink-0">
                      <button
                        @click.stop="openBookmark(bookmark.url)"
                        class="p-2 text-gray-600 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 rounded transition"
                        title="打开"
                      >
                        🔗
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 分页信息 -->
              <div v-if="categoryBookmarks.get(category.id)?.total > 50" class="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
                显示前 50 个书签，共 {{ categoryBookmarks.get(category.id)?.total }} 个
              </div>
            </div>

            <!-- 无书签 -->
            <div v-else class="p-8 text-center">
              <p class="text-gray-500 dark:text-gray-400">
                📭 该分类下暂无书签
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑分类模态框 -->
    <div
      v-if="showCreateModal || showEditModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModal"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
        <h2 class="text-xl font-bold mb-4 text-gray-900 dark:text-white">
          {{ editingCategory ? '✏️ 编辑分类' : '➕ 新建分类' }}
        </h2>

        <form @submit.prevent="saveCategory">
          <div class="space-y-4">
            <!-- 分类名称 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                分类名称 *
              </label>
              <input
                v-model="formData.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="例如: 技术"
              />
            </div>

            <!-- 描述 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                描述
              </label>
              <textarea
                v-model="formData.description"
                rows="2"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="分类的简短描述"
              ></textarea>
            </div>

            <!-- 图标和颜色 -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  图标 (Emoji)
                </label>
                <input
                  v-model="formData.icon"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="📁"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  颜色
                </label>
                <input
                  v-model="formData.color"
                  type="color"
                  class="w-full h-10 border border-gray-300 dark:border-gray-600 rounded-lg"
                />
              </div>
            </div>

            <!-- 关键词 -->
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                关键词 (逗号分隔)
              </label>
              <input
                v-model="keywordsText"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="Vue, React, Angular"
              />
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                这些关键词将帮助AI更准确地进行分类
              </p>
            </div>
          </div>

          <!-- 按钮 -->
          <div class="flex justify-end gap-2 mt-6">
            <button
              type="button"
              @click="closeModal"
              class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
            >
              取消
            </button>
            <button
              type="submit"
              :disabled="saving"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div
      v-if="showDeleteConfirm"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showDeleteConfirm = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-sm mx-4">
        <h2 class="text-xl font-bold mb-4 text-gray-900 dark:text-white">
          ⚠️ 确认删除
        </h2>

        <p class="text-gray-700 dark:text-gray-300 mb-4">
          确定要删除分类 "{{ categoryToDelete?.name }}" 吗？
        </p>

        <div v-if="categoryToDelete?.bookmark_count > 0" class="bg-yellow-50 dark:bg-yellow-900 border-l-4 border-yellow-400 p-4 mb-4">
          <p class="text-sm text-yellow-800 dark:text-yellow-200">
            ⚠️ 该分类下有 {{ categoryToDelete.bookmark_count }} 个书签。删除后这些书签将失去分类关联。
          </p>
        </div>

        <div class="flex justify-end gap-2">
          <button
            @click="showDeleteConfirm = false"
            class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
          >
            取消
          </button>
          <button
            @click="deleteCategory"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
          >
            确认删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import backendService from '@/services/backend.js';

// 数据
const categories = ref([]);
const stats = ref(null);
const loading = ref(true);

// 分类书签数据
const expandedCategories = ref(new Set()); // 存储展开的分类ID
const categoryBookmarks = ref(new Map()); // 存储每个分类的书签数据
const loadingBookmarks = ref(new Set()); // 存储正在加载书签的分类ID

// 模态框状态
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showDeleteConfirm = ref(false);

// 编辑状态
const editingCategory = ref(null);
const categoryToDelete = ref(null);
const saving = ref(false);

// 表单数据
const formData = ref({
  name: '',
  description: '',
  icon: '📁',
  color: '#3B82F6',
  parent_id: null,
  keywords: []
});

const keywordsText = computed({
  get: () => formData.value.keywords.join(', '),
  set: (val) => {
    formData.value.keywords = val.split(',').map(k => k.trim()).filter(k => k);
  }
});

// 加载分类
const loadCategories = async () => {
  try {
    loading.value = true;
    const data = await backendService.getCategories();
    categories.value = data;

    // 同时加载统计
    const statsData = await backendService.getCategoryStats();
    stats.value = statsData;
  } catch (error) {
    console.error('Failed to load categories:', error);
    notify({
      group: 'error',
      text: '加载分类失败: ' + error.message
    }, 5000);
  } finally {
    loading.value = false;
  }
};

// 切换分类展开/收起
const toggleCategory = async (categoryId) => {
  if (expandedCategories.value.has(categoryId)) {
    // 收起
    expandedCategories.value.delete(categoryId);
  } else {
    // 展开
    expandedCategories.value.add(categoryId);

    // 如果还没有加载过书签，则加载
    if (!categoryBookmarks.value.has(categoryId)) {
      await loadCategoryBookmarks(categoryId);
    }
  }
  // 触发响应式更新
  expandedCategories.value = new Set(expandedCategories.value);
};

// 加载分类下的书签
const loadCategoryBookmarks = async (categoryId) => {
  try {
    loadingBookmarks.value.add(categoryId);
    const data = await backendService.getCategoryBookmarks(categoryId, 1, 50);
    categoryBookmarks.value.set(categoryId, data);
    // 触发响应式更新
    categoryBookmarks.value = new Map(categoryBookmarks.value);
  } catch (error) {
    console.error('Failed to load category bookmarks:', error);
    notify({
      group: 'error',
      text: '加载书签失败: ' + error.message
    }, 5000);
  } finally {
    loadingBookmarks.value.delete(categoryId);
    // 触发响应式更新
    loadingBookmarks.value = new Set(loadingBookmarks.value);
  }
};

// 判断分类是否展开
const isExpanded = (categoryId) => {
  return expandedCategories.value.has(categoryId);
};

// 获取分类的书签
const getCategoryBookmarksData = (categoryId) => {
  return categoryBookmarks.value.get(categoryId)?.bookmarks || [];
};

// 判断是否正在加载书签
const isLoadingBookmarks = (categoryId) => {
  return loadingBookmarks.value.has(categoryId);
};

// 打开书签
const openBookmark = (url) => {
  window.open(url, '_blank', 'noopener,noreferrer');
};

// 初始化默认分类
const initializeDefaults = async () => {
  try {
    await backendService.initializeCategories();
    notify({
      group: 'success',
      text: '✅ 默认分类初始化成功！'
    }, 3000);
    await loadCategories();
  } catch (error) {
    notify({
      group: 'error',
      text: '初始化失败: ' + error.message
    }, 5000);
  }
};

// 编辑分类
const editCategory = (category) => {
  editingCategory.value = category;
  formData.value = {
    name: category.name,
    description: category.description || '',
    icon: category.icon || '📁',
    color: category.color || '#3B82F6',
    parent_id: category.parent_id,
    keywords: category.keywords || []
  };
  showEditModal.value = true;
};

// 确认删除
const confirmDelete = (category) => {
  categoryToDelete.value = category;
  showDeleteConfirm.value = true;
};

// 删除分类
const deleteCategory = async () => {
  try {
    await backendService.deleteCategory(categoryToDelete.value.id);
    notify({
      group: 'success',
      text: '✅ 分类已删除'
    }, 3000);

    showDeleteConfirm.value = false;
    categoryToDelete.value = null;
    await loadCategories();
  } catch (error) {
    notify({
      group: 'error',
      text: '删除失败: ' + error.message
    }, 5000);
  }
};

// 保存分类
const saveCategory = async () => {
  try {
    saving.value = true;

    if (editingCategory.value) {
      // 更新
      await backendService.updateCategory(editingCategory.value.id, formData.value);
      notify({
        group: 'success',
        text: '✅ 分类已更新'
      }, 3000);
    } else {
      // 创建
      await backendService.createCategory(formData.value);
      notify({
        group: 'success',
        text: '✅ 分类已创建'
      }, 3000);
    }

    closeModal();
    await loadCategories();
  } catch (error) {
    notify({
      group: 'error',
      text: '保存失败: ' + error.message
    }, 5000);
  } finally {
    saving.value = false;
  }
};

// 关闭模态框
const closeModal = () => {
  showCreateModal.value = false;
  showEditModal.value = false;
  editingCategory.value = null;
  formData.value = {
    name: '',
    description: '',
    icon: '📁',
    color: '#3B82F6',
    parent_id: null,
    keywords: []
  };
};

// 页面加载时获取数据
onMounted(() => {
  loadCategories();
});
</script>
