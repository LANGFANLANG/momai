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
import ReferencesPage from '@/pages/ReferencesPage.vue'
import AiGenerationPage from '@/pages/AiGenerationPage.vue'
import AuthPage from '@/pages/AuthPage.vue'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/projects' },
  { path: '/login', component: AuthPage, meta: { public: true } },
  { path: '/projects', component: ProjectListPage },
  { path: '/ai-generation', component: AiGenerationPage },
  { path: '/projects/new', component: ProjectCreatePage },
  { path: '/projects/:projectId', component: ProjectLayout, children: [
    { path: '', redirect: to => `/projects/${String(to.params.projectId)}/brief` },
    { path: 'brief', component: ProjectBriefPage },
    { path: 'outline', component: OutlinePage },
    { path: 'relations', component: ChapterRelationsPage },
    { path: 'references', component: ReferencesPage },
    { path: 'chapters', component: ChapterWritingPage },
    { path: 'chapters/:chapterId', component: ChapterWritingPage },
    { path: 'review', component: ConsistencyReviewPage },
    { path: 'export', component: ExportPage },
  ] },
]
const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(to => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) return '/login'
  if (to.path === '/login' && auth.token) return '/projects'
})

export default router
