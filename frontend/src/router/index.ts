import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import ProjectListPage from '@/pages/ProjectListPage.vue'
import ProjectCreatePage from '@/pages/ProjectCreatePage.vue'
import ProjectLayout from '@/pages/ProjectLayout.vue'
import ProjectBriefPage from '@/pages/ProjectBriefPage.vue'
import OutlinePage from '@/pages/OutlinePage.vue'
import ChapterRelationsPage from '@/pages/ChapterRelationsPage.vue'
import ChapterWritingPage from '@/pages/ChapterWritingPage.vue'
import ConsistencyReviewPage from '@/pages/ConsistencyReviewPage.vue'
import ExportPage from '@/pages/ExportPage.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/projects' },
  { path: '/projects', component: ProjectListPage },
  { path: '/projects/new', component: ProjectCreatePage },
  { path: '/projects/:projectId', component: ProjectLayout, children: [
    { path: '', redirect: to => `/projects/${String(to.params.projectId)}/brief` },
    { path: 'brief', component: ProjectBriefPage },
    { path: 'outline', component: OutlinePage },
    { path: 'relations', component: ChapterRelationsPage },
    { path: 'chapters', component: ChapterWritingPage },
    { path: 'chapters/:chapterId', component: ChapterWritingPage },
    { path: 'review', component: ConsistencyReviewPage },
    { path: 'export', component: ExportPage },
  ] },
]
export default createRouter({ history: createWebHistory(), routes })
