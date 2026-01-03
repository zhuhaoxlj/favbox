import { createWebHashHistory, createRouter } from 'vue-router';

const routes = [
  {
    path: '/bookmarks',
    alias: '/ext/browser/index.html',
    name: 'BookmarksView',
    component: () => import('./views/BookmarksView.vue'),
    meta: {
      page: 1,
    },
  },
  {
    path: '/bookmarks/:id',
    name: 'BookmarkDetailView',
    component: () => import('./views/BookmarksView.vue'),
    meta: {
      page: 1,
    },
  },
  {
    path: '/pinned',
    name: 'PinnedView',
    component: () => import('./views/PinnedView.vue'),
    meta: { page: 2 },
  },
  {
    path: '/health-check',
    name: 'HealthCheckView',
    component: () => import('./views/HealthCheckView.vue'),
    meta: { page: 3 },
  },
  {
    path: '/duplicates',
    name: 'DuplicatesView',
    component: () => import('./views/DuplicatesView.vue'),
    meta: { page: 4 },
  },
  {
    path: '/sync-settings',
    name: 'SyncSettingsView',
    component: () => import('./views/SyncSettingsView.vue'),
    meta: { page: 5 },
  },
  {
    path: '/ai-batch-tag',
    name: 'AITagBatchView',
    component: () => import('./views/AITagBatchView.vue'),
    meta: { page: 6 },
  },
  {
    path: '/categories',
    name: 'CategoriesView',
    component: () => import('./views/CategoriesView.vue'),
    meta: { page: 7 },
  },
  {
    path: '/semantic-search',
    name: 'SemanticSearchView',
    component: () => import('./views/SemanticSearchView.vue'),
    meta: { page: 8 },
  },
  {
    path: '/',
    redirect: '/bookmarks',
  },
  {
    path: '/:catchAll(.*)',
    redirect: '/bookmarks',
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
