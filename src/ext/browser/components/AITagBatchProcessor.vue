<template>
  <div class="flex flex-col h-full p-6">
    <h1 class="text-2xl font-bold mb-6">AI 批量打标签</h1>

    <!-- 配置面板 -->
    <div class="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-800 p-6 mb-6">
      <h2 class="text-lg font-semibold mb-4">处理配置</h2>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label class="block text-sm font-medium mb-1">时间范围（天数）</label>
          <select
            v-model="days"
            class="w-full px-3 py-2 border rounded-md bg-white dark:bg-neutral-800 border-gray-300 dark:border-neutral-700"
          >
            <option :value="7">最近7天</option>
            <option :value="30">最近30天</option>
            <option :value="90">最近90天</option>
            <option :value="180">最近半年</option>
            <option :value="365">最近一年</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium mb-1">最大标签数</label>
          <select
            v-model="maxTags"
            class="w-full px-3 py-2 border rounded-md bg-white dark:bg-neutral-800 border-gray-300 dark:border-neutral-700"
          >
            <option :value="3">3个标签</option>
            <option :value="5">5个标签</option>
            <option :value="8">8个标签</option>
            <option :value="10">10个标签</option>
          </select>
        </div>
        
        <div class="flex items-end">
          <label class="flex items-center">
            <input
              v-model="overwrite"
              type="checkbox"
              class="mr-2"
            >
            <span class="text-sm">覆盖已有标签</span>
          </label>
        </div>
      </div>
      
      <div class="mb-4">
        <label class="flex items-center">
          <input
            v-model="createBackup"
            type="checkbox"
            class="mr-2"
            checked
          >
          <span class="text-sm">处理前自动创建备份</span>
        </label>
      </div>
      
      <button
        :disabled="processing"
        class="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
        @click="startBatchTagging"
      >
        {{ processing ? '处理中...' : '开始批量打标签' }}
      </button>
    </div>

    <!-- 处理状态 -->
    <div
      v-if="processing || stats"
      class="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-800 p-6 mb-6"
    >
      <h2 class="text-lg font-semibold mb-4">处理状态</h2>
      
      <div v-if="processing" class="flex items-center mb-4">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mr-3"></div>
        <span>正在处理书签...</span>
      </div>
      
      <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="text-center">
          <div class="text-2xl font-bold text-blue-500">{{ stats.processed || 0 }}</div>
          <div class="text-sm text-gray-500">已处理</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-green-500">{{ stats.success || 0 }}</div>
          <div class="text-sm text-gray-500">成功</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-red-500">{{ stats.failed || 0 }}</div>
          <div class="text-sm text-gray-500">失败</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-gray-500">{{ stats.skipped || 0 }}</div>
          <div class="text-sm text-gray-500">跳过</div>
        </div>
      </div>

      <div v-if="stats && stats.backup_id" class="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-md">
        <span class="text-sm">已创建备份 ID: {{ stats.backup_id }}</span>
      </div>

      <div v-if="stats && stats.errors && stats.errors.length > 0" class="mt-4">
        <h3 class="text-sm font-semibold mb-2">错误详情：</h3>
        <ul class="text-sm text-red-500 list-disc list-inside">
          <li v-for="(error, index) in stats.errors" :key="index">
            {{ error }}
          </li>
        </ul>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-800 p-6">
      <h2 class="text-lg font-semibold mb-4">AI 处理统计</h2>
      
      <div v-if="loadingStats" class="text-center py-4">
        加载中...
      </div>
      
      <div v-else-if="aiStats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="text-center">
          <div class="text-2xl font-bold">{{ aiStats.total_bookmarks }}</div>
          <div class="text-sm text-gray-500">总书签数</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-blue-500">{{ aiStats.analyzed_bookmarks }}</div>
          <div class="text-sm text-gray-500">已AI分析</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-green-500">{{ aiStats.bookmarks_with_ai_tags }}</div>
          <div class="text-sm text-gray-500">有AI标签</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-purple-500">{{ aiStats.analysis_rate }}</div>
          <div class="text-sm text-gray-500">分析率</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import backendService from '../../../services/backend.js';

export default {
  name: 'AITagBatchProcessor',
  setup() {
    const days = ref(30);
    const maxTags = ref(5);
    const overwrite = ref(false);
    const createBackup = ref(true);
    const processing = ref(false);
    const stats = ref(null);
    const loadingStats = ref(false);
    const aiStats = ref(null);

    const loadAIStats = async () => {
      loadingStats.value = true;
      try {
        aiStats.value = await backendService.getAIStats();
      } catch (error) {
        console.error('Failed to load AI stats:', error);
      } finally {
        loadingStats.value = false;
      }
    };

    const startBatchTagging = async () => {
      if (!confirm(`确定要对最近 ${days.value} 天的书签进行AI打标签吗？${createBackup.value ? '处理前将自动创建备份。' : ''}`)) {
        return;
      }

      processing.value = true;
      stats.value = null;

      try {
        const result = await backendService.batchTagBookmarks({
          days: days.value,
          max_tags: maxTags.value,
          overwrite: overwrite.value,
          create_backup: createBackup.value,
        });

        stats.value = result;
        await loadAIStats();

        alert(`处理完成！\n成功: ${result.success}\n失败: ${result.failed}`);
      } catch (error) {
        console.error('Batch tagging failed:', error);
        alert('批量打标签失败：' + error.message);
      } finally {
        processing.value = false;
      }
    };

    onMounted(async () => {
      // 等待 backendService 完成初始化
      try {
        await backendService.init();
        // 只有在配置完成后才加载统计信息
        if (backendService.isConfigured()) {
          loadAIStats();
        } else {
          console.error('[AITagBatchProcessor] Backend not configured');
        }
      } catch (error) {
        console.error('[AITagBatchProcessor] Failed to initialize backend:', error);
      }
    });

    return {
      days,
      maxTags,
      overwrite,
      createBackup,
      processing,
      stats,
      loadingStats,
      aiStats,
      startBatchTagging,
    };
  },
};
</script>
