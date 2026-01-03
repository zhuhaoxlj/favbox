<template>
  <div class="flex flex-col h-full">
    <div class="p-6 border-b border-gray-200 dark:border-neutral-800">
      <h1 class="text-2xl font-bold mb-4">语义化搜索</h1>
      
      <!-- 搜索输入 -->
      <div class="flex gap-2">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="输入搜索查询（支持语义理解）"
          class="flex-1 px-4 py-2 border rounded-md bg-white dark:bg-neutral-800 border-gray-300 dark:border-neutral-700"
          @keyup.enter="performSearch"
        >
        <button
          :disabled="searching || !searchQuery"
          class="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
          @click="performSearch"
        >
          {{ searching ? '搜索中...' : '搜索' }}
        </button>
      </div>
      
      <!-- 高级选项 -->
      <div class="flex gap-4 mt-3">
        <div class="flex items-center">
          <label class="text-sm mr-2">相似度阈值:</label>
          <input
            v-model.number="minSimilarity"
            type="range"
            min="0"
            max="1"
            step="0.1"
            class="w-32"
          >
          <span class="text-sm ml-2">{{ minSimilarity }}</span>
        </div>
        
        <div class="flex items-center">
          <label class="text-sm mr-2">结果数量:</label>
          <select
            v-model.number="limit"
            class="px-3 py-1 border rounded-md bg-white dark:bg-neutral-800 border-gray-300 dark:border-neutral-700"
          >
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 搜索结果 -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="searching" class="text-center py-8">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p>正在搜索...</p>
      </div>
      
      <div v-else-if="!searched && !results.length" class="text-center py-12 text-gray-500">
        <p class="text-lg mb-2">🔍 语义化搜索</p>
        <p>输入查询词开始搜索</p>
        <p class="text-sm mt-4">示例: "前端框架", "机器学习教程", "React组件"</p>
      </div>
      
      <div v-else-if="results.length === 0" class="text-center py-8 text-gray-500">
        <p>未找到匹配的书签</p>
        <p class="text-sm mt-2">尝试降低相似度阈值或使用不同的查询词</p>
      </div>
      
      <div v-else class="space-y-4">
        <div class="mb-4">
          <p class="text-sm text-gray-500">找到 {{ results.length }} 个相关书签</p>
        </div>
        
        <div
          v-for="(item, index) in results"
          :key="item.bookmark.id"
          class="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-800 p-4 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
        >
          <div class="flex justify-between items-start mb-2">
            <h3 class="font-semibold text-lg">{{ item.bookmark.title }}</h3>
            <span class="text-sm px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full">
              {{ (item.similarity * 100).toFixed(0) }}%
            </span>
          </div>
          
          <p v-if="item.bookmark.description" class="text-gray-600 dark:text-gray-400 text-sm mb-3 line-clamp-2">
            {{ item.bookmark.description }}
          </p>
          
          <a
            :href="item.bookmark.url"
            target="_blank"
            class="text-blue-500 hover:text-blue-700 text-sm break-all"
          >
            {{ item.bookmark.url }}
          </a>
          
          <!-- 标签 -->
          <div v-if="item.bookmark.tags && item.bookmark.tags.length > 0" class="mt-3 flex flex-wrap gap-1">
            <span
              v-for="tag in item.bookmark.tags"
              :key="tag"
              class="text-xs px-2 py-1 bg-gray-100 dark:bg-neutral-800 text-gray-700 dark:text-gray-300 rounded"
            >
              #{{ tag }}
            </span>
          </div>
          
          <!-- AI标签 -->
          <div v-if="item.bookmark.ai_tags && item.bookmark.ai_tags.length > 0" class="mt-2 flex flex-wrap gap-1">
            <span
              v-for="tag in item.bookmark.ai_tags"
              :key="'ai-' + tag"
              class="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded"
              title="AI生成的标签"
            >
              AI: {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 向量嵌入统计 -->
    <div class="border-t border-gray-200 dark:border-neutral-800 p-4">
      <div v-if="loadingEmbeddingStats" class="text-center text-sm">
        加载统计...
      </div>
      <div v-else-if="embeddingStats" class="flex justify-center gap-6 text-sm">
        <div>
          <span class="text-gray-500">总书签:</span>
          <span class="font-semibold ml-1">{{ embeddingStats.total_bookmarks }}</span>
        </div>
        <div>
          <span class="text-gray-500">有向量嵌入:</span>
          <span class="font-semibold ml-1 text-blue-500">{{ embeddingStats.bookmarks_with_embeddings }}</span>
        </div>
        <div>
          <span class="text-gray-500">覆盖率:</span>
          <span class="font-semibold ml-1 text-green-500">{{ embeddingStats.embedding_coverage }}</span>
        </div>
        <button
          @click="showGenerateModal = true"
          class="text-blue-500 hover:text-blue-700 underline"
        >
          生成向量嵌入
        </button>
      </div>
    </div>

    <!-- 生成向量嵌入对话框 -->
    <div v-if="showGenerateModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white dark:bg-neutral-900 rounded-lg p-6 max-w-md w-full mx-4">
        <h3 class="text-lg font-semibold mb-4">生成向量嵌入</h3>
        
        <div class="space-y-4 mb-4">
          <div>
            <label class="block text-sm font-medium mb-1">时间范围（天数）</label>
            <select
              v-model="embedDays"
              class="w-full px-3 py-2 border rounded-md bg-white dark:bg-neutral-800 border-gray-300 dark:border-neutral-700"
            >
              <option :value="7">最近7天</option>
              <option :value="30">最近30天</option>
              <option :value="90">最近90天</option>
              <option :value="180">最近半年</option>
            </select>
          </div>
          
          <label class="flex items-center">
            <input
              v-model="overwriteEmbeds"
              type="checkbox"
              class="mr-2"
            >
            <span class="text-sm">覆盖已有向量嵌入</span>
          </label>
        </div>
        
        <div class="flex justify-end gap-3">
          <button
            class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-md"
            @click="showGenerateModal = false"
          >
            取消
          </button>
          <button
            :disabled="generatingEmbeds"
            class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            @click="generateEmbeddings"
          >
            {{ generatingEmbeds ? '生成中...' : '生成' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import backendService from '@/services/backend.js';

export default {
  name: 'SemanticSearch',
  setup() {
    const searchQuery = ref('');
    const minSimilarity = ref(0.5);
    const limit = ref(20);
    const searching = ref(false);
    const searched = ref(false);
    const results = ref([]);
    
    const loadingEmbeddingStats = ref(false);
    const embeddingStats = ref(null);
    const showGenerateModal = ref(false);
    const embedDays = ref(30);
    const overwriteEmbeds = ref(false);
    const generatingEmbeds = ref(false);

    const loadEmbeddingStats = async () => {
      loadingEmbeddingStats.value = true;
      try {
        embeddingStats.value = await backendService.getEmbeddingStats();
      } catch (error) {
        console.error('Failed to load embedding stats:', error);
      } finally {
        loadingEmbeddingStats.value = false;
      }
    };

    const performSearch = async () => {
      if (!searchQuery.value.trim()) return;
      
      searching.value = true;
      searched.value = true;
      
      try {
        const searchResults = await backendService.semanticSearch({
          query: searchQuery.value,
          min_similarity: minSimilarity.value,
          limit: limit.value,
        });
        
        results.value = searchResults;
      } catch (error) {
        console.error('Search failed:', error);
        alert('搜索失败：' + error.message);
      } finally {
        searching.value = false;
      }
    };

    const generateEmbeddings = async () => {
      generatingEmbeds.value = true;
      
      try {
        const result = await backendService.generateEmbeddings({
          days: embedDays.value,
          overwrite: overwriteEmbeds.value,
        });
        
        alert(result.message);
        showGenerateModal.value = false;
        await loadEmbeddingStats();
      } catch (error) {
        console.error('Failed to generate embeddings:', error);
        alert('生成失败：' + error.message);
      } finally {
        generatingEmbeds.value = false;
      }
    };

    onMounted(() => {
      loadEmbeddingStats();
    });

    return {
      searchQuery,
      minSimilarity,
      limit,
      searching,
      searched,
      results,
      loadingEmbeddingStats,
      embeddingStats,
      showGenerateModal,
      embedDays,
      overwriteEmbeds,
      generatingEmbeds,
      performSearch,
      generateEmbeddings,
    };
  },
};
</script>
