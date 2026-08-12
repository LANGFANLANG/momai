import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const WorkflowPlaceholder = {
  template: '<section><h1 class="text-2xl font-semibold">{{ $route.meta.title }}</h1></section>',
}

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/projects' },
  { path: '/projects', component: WorkflowPlaceholder, meta: { title: '项目' } },
  { path: '/projects/new', component: WorkflowPlaceholder, meta: { title: '新建项目' } },
  { path: '/projects/:projectId/brief', component: WorkflowPlaceholder, meta: { title: '项目 Brief' } },
  { path: '/projects/:projectId/outline', component: WorkflowPlaceholder, meta: { title: '大纲' } },
  { path: '/projects/:projectId/relations', component: WorkflowPlaceholder, meta: { title: '章节关系' } },
  { path: '/projects/:projectId/chapters/:chapterId', component: WorkflowPlaceholder, meta: { title: '章节写作' } },
  { path: '/projects/:projectId/review', component: WorkflowPlaceholder, meta: { title: '一致性检查' } },
  { path: '/projects/:projectId/export', component: WorkflowPlaceholder, meta: { title: '导出' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
