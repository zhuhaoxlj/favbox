<template>
  <div class="flex flex-col h-full p-6">
    <h1 class="text-2xl font-bold mb-6">备份管理</h1>

    <!-- 创建备份表单 -->
    <div class="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-800 p-6 mb-6">
      <h2 class="text-lg font-semibold mb-4">创建新备份</h2>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-1">备份名称</label>
          <input
            v-model="backupName"
            type="text"
            placeholder="例如：AI处理前备份"
            class="w-full px-3 py-2 border rounded-md bg-white dark:bg-neutral-800 border-gray-300 dark:border-neutral-700"
          >
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">描述（可选）</label>
          <textarea
            v-model="backupDescription"
            placeholder="备份的说明"
            class="w-full px-3 py-2 border rounded-md bg-white dark:bg-neutral-800 border-gray-300 dark:border-neutral-700"
            rows="2"
          />
        </div>
        <button
          :disabled="creating || !backupName"
          class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
          @click="createBackup"
        >
          {{ creating ? '创建中...' : '创建备份' }}
        </button>
      </div>
    </div>

    <!-- 备份列表 -->
    <div class="bg-white dark:bg-neutral-900 rounded-lg border border-gray-200 dark:border-neutral-800 p-6">
      <h2 class="text-lg font-semibold mb-4">备份历史</h2>
      
      <div v-if="loading" class="text-center py-8">
        加载中...
      </div>
      
      <div v-else-if="backups.length === 0" class="text-center py-8 text-gray-500">
        暂无备份
      </div>
      
      <div v-else class="space-y-3">
        <div
          v-for="backup in backups"
          :key="backup.id"
          class="border border-gray-200 dark:border-neutral-700 rounded-md p-4"
        >
          <div class="flex justify-between items-start mb-2">
            <div>
              <h3 class="font-semibold">{{ backup.name }}</h3>
              <p v-if="backup.description" class="text-sm text-gray-500">{{ backup.description }}</p>
            </div>
            <button
              @click="deleteBackup(backup.id)"
              class="text-red-500 hover:text-red-700 text-sm"
            >
              删除
            </button>
          </div>
          
          <div class="text-sm text-gray-500 mb-3">
            {{ formatDate(backup.created_at) }} · {{ backup.total_bookmarks }} 个书签
          </div>
          
          <div class="flex gap-2">
            <button
              class="px-3 py-1 text-sm bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800"
              @click="restoreBackup(backup.id, false)"
            >
              完全还原
            </button>
            <button
              class="px-3 py-1 text-sm bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-800"
              @click="restoreBackup(backup.id, true)"
            >
              合并还原
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 还原确认对话框 -->
    <div v-if="showRestoreConfirm" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white dark:bg-neutral-900 rounded-lg p-6 max-w-md w-full mx-4">
        <h3 class="text-lg font-semibold mb-4">确认还原</h3>
        <p class="mb-4">
          {{ restoreMode ? '合并模式：' : '完全覆盖：' }}
          将从备份还原书签。此操作无法撤销。
        </p>
        <div class="flex justify-end gap-3">
          <button
            class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-md"
            @click="showRestoreConfirm = false"
          >
            取消
          </button>
          <button
            class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            @click="confirmRestore"
          >
            确认还原
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import backendService from '../../../../services/backend.js';

export default {
  name: 'BackupManager',
  setup() {
    const backups = ref([]);
    const backupName = ref('');
    const backupDescription = ref('');
    const creating = ref(false);
    const loading = ref(false);
    const showRestoreConfirm = ref(false);
    const restoreMode = ref(false);
    const restoreBackupId = ref(null);

    const loadBackups = async () => {
      loading.value = true;
      try {
        backups.value = await backendService.getBackups();
      } catch (error) {
        console.error('Failed to load backups:', error);
      } finally {
        loading.value = false;
      }
    };

    const createBackup = async () => {
      creating.value = true;
      try {
        await backendService.createBackup({
          name: backupName.value,
          description: backupDescription.value,
        });
        backupName.value = '';
        backupDescription.value = '';
        await loadBackups();
      } catch (error) {
        console.error('Failed to create backup:', error);
        alert('创建备份失败');
      } finally {
        creating.value = false;
      }
    };

    const deleteBackup = async (backupId) => {
      if (!confirm('确定要删除此备份吗？')) return;
      
      try {
        await backendService.deleteBackup(backupId);
        await loadBackups();
      } catch (error) {
        console.error('Failed to delete backup:', error);
        alert('删除备份失败');
      }
    };

    const restoreBackup = (backupId, mode) => {
      restoreBackupId.value = backupId;
      restoreMode.value = mode;
      showRestoreConfirm.value = true;
    };

    const confirmRestore = async () => {
      try {
        const result = await backendService.restoreBackup({
          backup_id: restoreBackupId.value,
          merge_mode: restoreMode.value,
        });
        alert(`还原成功！还原了 ${result.restored_count} 个书签`);
        showRestoreConfirm.value = false;
        await loadBackups();
      } catch (error) {
        console.error('Failed to restore backup:', error);
        alert('还原失败');
      }
    };

    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN');
    };

    onMounted(() => {
      loadBackups();
    });

    return {
      backups,
      backupName,
      backupDescription,
      creating,
      loading,
      showRestoreConfirm,
      restoreMode,
      createBackup,
      deleteBackup,
      restoreBackup,
      confirmRestore,
      formatDate,
    };
  },
};
</script>
