<template>
  <div class="h-screen w-full flex flex-col">
    <AppInfiniteScroll
      class="flex flex-col flex-1 overflow-y-auto bg-white dark:bg-black"
      :limit="50"
      @scroll:end="skip => loadDuplicates({ skip, limit: BOOKMARKS_LIMIT, append: true })"
    >
      <div
        class="sticky top-0 z-10 flex w-full flex-col  bg-white/70 p-4 backdrop-blur-sm dark:bg-black/50"
      >
        <div class="flex w-full items-center justify-between">
          <span class="text-xl font-extralight text-black dark:text-white">
            Total duplicate groups: <NumberFlow :value="total" />
          </span>
        </div>
      </div>
      <div
        v-if="loading || bookmarks.length === 0"
        class="flex flex-1 flex-col items-center justify-center p-5"
      >
        <AppSpinner v-if="loading" />
        <div
          v-else
          class="text-2xl text-black dark:text-white"
        >
          🚀 No duplicate bookmarks found.
        </div>
      </div>
      <div
        v-show="bookmarks.length > 0"
        v-auto-animate
        class="flex flex-col gap-y-4 p-4"
      >
        <div
          v-for="group in bookmarks"
          :key="group.url"
          class="rounded-md border border-solid bg-white shadow-xs dark:border-neutral-900 dark:bg-neutral-950 mb-3"
        >
          <div class="flex items-center justify-between w-full p-3 pb-0">
            <div class="flex items-center gap-x-2">
              <div class="flex h-6 min-w-6 items-center justify-center rounded-full bg-black px-1 text-xs font-medium text-white dark:bg-white dark:text-black">
                {{ group.count }}
              </div>
              <span class="text-xs text-gray-900 dark:text-white truncate w-full">
                <a
                  :href="group.url"
                  class="block max-w-xs md:max-w-md lg:max-w-2xl truncate hover:underline focus:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                  :title="group.url"
                >
                  {{ group.url }}
                </a>
              </span>
            </div>
          </div>
          <div class="flex flex-col gap-y-3 p-3 pt-2">
            <DuplicateCard
              v-for="bookmark in group.bookmarks"
              :key="bookmark.id"
              :bookmark="bookmark"
              @onDelete="onDelete"
            />
          </div>
        </div>
      </div>
    </AppInfiniteScroll>
    <AppConfirmation ref="confirmation">
      <template #title>
        Delete bookmark
      </template>
      <template #description>
        Are you sure you want to delete this bookmark? This action cannot be undone. Removing the bookmark from FavBox will also delete it from your browser.
      </template>
      <template #cancel>
        Cancel
      </template>
      <template #confirm>
        Delete
      </template>
    </AppConfirmation>
  </div>
</template>

<script setup>
import { ref, onMounted, useTemplateRef } from 'vue';
import { notify } from 'notiwind';
import BookmarkStorage from '@/storage/bookmark';
import { useBookmarkActions } from '@/composables/useBookmarkActions';
import AppInfiniteScroll from '@/components/app/AppInfiniteScroll.vue';
import AppSpinner from '@/components/app/AppSpinner.vue';
import DuplicateCard from '@/ext/browser/components/card/DuplicateCard.vue';
import AppConfirmation from '@/components/app/AppConfirmation.vue';
import NumberFlow from '@number-flow/vue';

const NOTIFICATION_DURATION = import.meta.env.VITE_NOTIFICATION_DURATION;
const bookmarkStorage = new BookmarkStorage();
const { deleteBookmark } = useBookmarkActions();

const loading = ref(true);
const bookmarks = ref([]);
const total = ref(0);
const confirmationRef = useTemplateRef('confirmation');
const removedGroupsCount = ref(0);

const BOOKMARKS_LIMIT = import.meta.env.VITE_BOOKMARKS_PAGINATION_LIMIT;
const loadDuplicates = async ({ skip = 0, limit = BOOKMARKS_LIMIT, append = false } = {}) => {
  try {
    if (!append) loading.value = true;
    const result = await bookmarkStorage.getDuplicatesGrouped(skip, limit);
    if (append) {
      bookmarks.value.push(...result.groups);
    } else {
      bookmarks.value = result.groups;
      total.value = result.total;
      notify({ group: 'success', text: `Found ${result.total} duplicate groups` }, NOTIFICATION_DURATION);
    }
  } catch (error) {
    console.error('Error loading duplicates:', error);
    notify({ group: 'error', text: 'Error loading duplicates' }, NOTIFICATION_DURATION);
  } finally {
    if (!append) loading.value = false;
  }
};

const onDelete = async (bookmark) => {
  if (await confirmationRef.value.request() === false) {
    return;
  }

  try {
    // 使用统一的删除方法
    await deleteBookmark(bookmark);

    // 手动变更书签数据以实现平滑动画
    const groupIndex = bookmarks.value.findIndex((group) => group.bookmarks.some((b) => b.id === bookmark.id));
    if (groupIndex !== -1) {
      const group = bookmarks.value[groupIndex];
      const bookmarkIndex = group.bookmarks.findIndex((b) => b.id === bookmark.id);
      if (bookmarkIndex !== -1) {
        group.bookmarks.splice(bookmarkIndex, 1);
        // 如果组中只剩下0或1个书签，删除整个组
        if (group.bookmarks.length <= 1) {
          bookmarks.value.splice(groupIndex, 1);
          removedGroupsCount.value += 1;
          total.value -= 1;
          // 删除后如果数据库中仍有重复项，加载一个新组
          if (bookmarks.value.length + removedGroupsCount.value < total.value) {
            const result = await bookmarkStorage.getDuplicatesGrouped(bookmarks.value.length + removedGroupsCount.value, 1);
            if (result.groups.length > 0) {
              bookmarks.value.push(result.groups[0]);
            }
          }
        }
      }
    }

    notify({ group: 'default', text: 'Bookmark deleted. This group no longer contains duplicates.' }, NOTIFICATION_DURATION);
  } catch (error) {
    console.error('Error deleting bookmark:', error);
    notify({ group: 'error', text: 'Error deleting bookmark' }, NOTIFICATION_DURATION);
  }
};

onMounted(async () => {
  await loadDuplicates();
});
</script>
