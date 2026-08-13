<script setup lang="ts">
import { BookOpen, CheckCircle2, Copy, ExternalLink, Workflow } from 'lucide-vue-next'

const mcpConfig = `{
  "mcpServers": {
    "drawio": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "@next-ai-drawio/mcp-server@latest"
      ]
    }
  }
}`

const quickTestPrompt = `请调用 drawio MCP 创建一张简单流程图：

用户
↓
前端系统
↓
后端服务
↓
MySQL数据库

要求：
使用中文，
从左到右排列，
使用箭头表示调用关系。`

const analyzePrompt = `请分析当前整个项目。

暂时不要画图，也不要调用 Draw.io MCP。
需要真实读取项目代码，不要只根据 README 推测。

重点分析：
1. 项目整体技术栈
2. 前端结构
3. 后端结构
4. Controller
5. Service
6. Mapper / Repository
7. 数据库
8. Redis
9. 消息队列
10. AI模块
11. 第三方服务
12. 模块之间的调用关系

最后整理出一个简洁的系统架构说明。`

const drawPrompt = `根据刚才对当前项目真实代码的分析结果，
调用 Next AI Draw.io MCP，
为当前项目生成一张完整的系统架构图。

要求：
1. 使用中文
2. 使用分层架构
3. 不展示过细的类
4. 重点展示核心模块
5. 标明模块调用关系
6. 标明数据库和中间件
7. 标明第三方服务
8. 如果存在 AI 模块，需要单独划分 AI 层

请直接调用 Draw.io MCP 创建，不要只给我 Mermaid 或文本。`

const editPrompt = `继续修改刚才的 Draw.io 架构图。

不要重新创建一张图。

调整：
1. 前端放在顶部
2. 后端放在中间
3. 数据库放在底部
4. AI模块放在右侧
5. 删除过细的类
6. 保留主要业务模块`

const sections = [
  {
    title: '1. 最终效果',
    body: '让 Cursor / AI Agent 阅读本地项目代码，分析系统架构，然后调用 Next AI Draw.io MCP 自动生成架构图、流程图、时序图，并支持继续修改和导出 .drawio / PNG / SVG。',
  },
  {
    title: '2. 两个角色',
    body: 'Cursor Agent 负责读取代码、分析业务、理解模块关系并决定画什么；Next AI Draw.io MCP 负责创建图、节点、箭头、浏览器预览、保存和导出。可以理解为：Agent 是大脑，MCP 是画图工具。',
  },
  {
    title: '3. 准备环境',
    body: '需要 Windows、Cursor、Node.js、npm / npx 和你的本地项目。不需要 clone Next AI Draw.io 源码、不需要手动部署 Next.js、不需要安装 Draw.io 桌面版，也不依赖 Docker 或 Python。',
  },
  {
    title: '4. 打开项目',
    body: '建议用 Cursor 打开项目根目录，而不是只打开 frontend 或 backend。这样 Agent 才能同时分析前端、后端、数据库、Docker、AI 模块和配置文件。',
  },
  {
    title: '5. 配置 MCP',
    body: '推荐项目级配置：在项目根目录创建 .cursor/mcp.json。也可以放在用户目录 ~/.cursor/mcp.json 作为全局配置；如果两边都有相同名称的 MCP，项目级配置优先。',
  },
  {
    title: '6. 重启与检查',
    body: '修改 mcp.json 后完全关闭 Cursor 并重新打开。进入 Settings / Customize / MCP，找到 drawio，正常应显示已启用或已连接。',
  },
  {
    title: '7. 推荐流程',
    body: '第一次先测试 MCP 链路，不要直接分析完整项目；第二次分析登录模块生成时序图；第三次再分析整个项目生成完整系统架构图。',
  },
  {
    title: '8. 常见问题',
    body: 'MCP 没显示时检查 .cursor/mcp.json、node -v、npm -v、npx -v，并重启 Cursor。6002 端口被占用时可在 env 里指定 PORT。No active session 时先调用 start_session。',
  },
]

const diagramIdeas = [
  '01 系统整体架构图',
  '02 后端模块架构图',
  '03 AI / RAG 架构图',
  '04 数据库关系图',
  '05 用户登录时序图',
  '06 AI 对话时序图',
]

async function copyText(text: string) {
  await navigator.clipboard.writeText(text)
}
</script>

<template>
  <section class="mx-auto max-w-6xl">
    <div class="mb-7 border-b border-stone-200 pb-6">
      <p class="page-kicker">AI GENERATION</p>
      <h1 class="page-heading">AI 智能生成参考文档</h1>
      <p class="page-copy mt-2 max-w-3xl">
        Cursor + Next AI Draw.io MCP 本地项目自动画图新手教程，用来让 AI Agent 阅读项目代码并自动生成架构图、流程图和时序图。
      </p>
    </div>

    <div class="mb-7 grid gap-3 md:grid-cols-3">
      <div class="panel p-5">
        <BookOpen class="mb-3 text-teal-800" :size="22" />
        <p class="text-sm font-semibold text-stone-900">读代码</p>
        <p class="mt-2 text-xs leading-5 text-stone-600">Agent 读取项目源码和配置，整理真实架构。</p>
      </div>
      <div class="panel p-5">
        <Workflow class="mb-3 text-teal-800" :size="22" />
        <p class="text-sm font-semibold text-stone-900">调 MCP</p>
        <p class="mt-2 text-xs leading-5 text-stone-600">Next AI Draw.io MCP 创建节点、连线和布局。</p>
      </div>
      <div class="panel p-5">
        <CheckCircle2 class="mb-3 text-teal-800" :size="22" />
        <p class="text-sm font-semibold text-stone-900">导出图</p>
        <p class="mt-2 text-xs leading-5 text-stone-600">浏览器预览后继续修改，导出 drawio、PNG 或 SVG。</p>
      </div>
    </div>

    <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
      <article class="panel">
        <div class="border-b border-stone-200 px-5 py-4">
          <h2 class="text-base font-semibold text-stone-900">教程正文</h2>
        </div>
        <div class="divide-y divide-stone-100">
          <section v-for="item in sections" :key="item.title" class="px-5 py-5">
            <h3 class="text-sm font-semibold text-stone-900">{{ item.title }}</h3>
            <p class="mt-2 text-sm leading-7 text-stone-600">{{ item.body }}</p>
          </section>
        </div>
      </article>

      <aside class="space-y-4">
        <div class="border border-teal-800 bg-white p-5 shadow-[4px_4px_0_0_#115e59]">
          <h2 class="text-sm font-semibold text-stone-900">MCP 配置</h2>
          <pre class="mt-3 overflow-x-auto bg-stone-950 p-3 text-xs leading-5 text-stone-50">{{ mcpConfig }}</pre>
          <button
            class="mt-3 inline-flex h-8 items-center gap-1.5 border border-stone-300 px-2.5 text-xs font-medium text-stone-700 hover:border-teal-700 hover:text-teal-800"
            type="button"
            @click="copyText(mcpConfig)"
          >
            <Copy :size="13" />
            复制配置
          </button>
        </div>

        <div class="panel p-5">
          <h2 class="text-sm font-semibold text-stone-900">推荐生成的图</h2>
          <ul class="mt-3 space-y-2 text-sm text-stone-600">
            <li v-for="item in diagramIdeas" :key="item">{{ item }}</li>
          </ul>
        </div>

        <a
          class="inline-flex h-9 items-center gap-1.5 border border-teal-800 bg-teal-800 px-3 text-sm font-medium text-white hover:bg-teal-900"
          href="https://www.npmjs.com/package/@next-ai-drawio/mcp-server"
          rel="noreferrer"
          target="_blank"
        >
          查看 MCP 包
          <ExternalLink :size="14" />
        </a>
      </aside>
    </div>

    <div class="mt-5 grid gap-4 lg:grid-cols-2">
      <div class="panel p-5">
        <h2 class="text-sm font-semibold text-stone-900">先测试 MCP</h2>
        <pre class="mt-3 whitespace-pre-wrap bg-stone-950 p-4 text-xs leading-6 text-stone-50">{{ quickTestPrompt }}</pre>
        <button class="mt-3 inline-flex h-8 items-center gap-1.5 border border-stone-300 px-2.5 text-xs font-medium text-stone-700 hover:border-teal-700 hover:text-teal-800" type="button" @click="copyText(quickTestPrompt)">
          <Copy :size="13" />
          复制 Prompt
        </button>
      </div>

      <div class="panel p-5">
        <h2 class="text-sm font-semibold text-stone-900">分析项目</h2>
        <pre class="mt-3 whitespace-pre-wrap bg-stone-950 p-4 text-xs leading-6 text-stone-50">{{ analyzePrompt }}</pre>
        <button class="mt-3 inline-flex h-8 items-center gap-1.5 border border-stone-300 px-2.5 text-xs font-medium text-stone-700 hover:border-teal-700 hover:text-teal-800" type="button" @click="copyText(analyzePrompt)">
          <Copy :size="13" />
          复制 Prompt
        </button>
      </div>

      <div class="panel p-5">
        <h2 class="text-sm font-semibold text-stone-900">生成架构图</h2>
        <pre class="mt-3 whitespace-pre-wrap bg-stone-950 p-4 text-xs leading-6 text-stone-50">{{ drawPrompt }}</pre>
        <button class="mt-3 inline-flex h-8 items-center gap-1.5 border border-stone-300 px-2.5 text-xs font-medium text-stone-700 hover:border-teal-700 hover:text-teal-800" type="button" @click="copyText(drawPrompt)">
          <Copy :size="13" />
          复制 Prompt
        </button>
      </div>

      <div class="panel p-5">
        <h2 class="text-sm font-semibold text-stone-900">继续修改图</h2>
        <pre class="mt-3 whitespace-pre-wrap bg-stone-950 p-4 text-xs leading-6 text-stone-50">{{ editPrompt }}</pre>
        <button class="mt-3 inline-flex h-8 items-center gap-1.5 border border-stone-300 px-2.5 text-xs font-medium text-stone-700 hover:border-teal-700 hover:text-teal-800" type="button" @click="copyText(editPrompt)">
          <Copy :size="13" />
          复制 Prompt
        </button>
      </div>
    </div>
  </section>
</template>
