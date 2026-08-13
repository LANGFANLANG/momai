export function normalizeHeadingTitle(title: string): string {
  return title
    .replace(/^#+\s*/, "")
    .replace(/^第[一二三四五六七八九十百千零〇\d]+[章节部分篇]\s*/, "")
    .replace(/^(?:\d+(?:[.\-．]\d+)*)[、.．]?\s*/, "")
    .replace(/^[（(][\d一二三四五六七八九十]+[）)]\s*/, "")
    .replace(/[\s：:]+/g, "")
    .toLowerCase()
}

export function titlesMatch(left: string, right: string): boolean {
  const a = normalizeHeadingTitle(left)
  const b = normalizeHeadingTitle(right)
  return Boolean(a && b && a === b)
}

export interface MarkdownSection {
  level: number
  title: string
  start: number
  end: number
}

export function findMarkdownSections(markdown: string): MarkdownSection[] {
  const heading = /^(#{1,6})\s+(.+?)\s*$/gm
  const matches: { level: number; title: string; start: number }[] = []
  let match = heading.exec(markdown)
  while (match) {
    matches.push({
      level: match[1].length,
      title: match[2].trim(),
      start: match.index,
    })
    match = heading.exec(markdown)
  }
  return matches.map((item, index) => {
    const next = matches.slice(index + 1).find(other => other.level <= item.level)
    return {
      level: item.level,
      title: item.title,
      start: item.start,
      end: next ? next.start : markdown.length,
    }
  })
}

function pickSection(
  markdown: string,
  title: string,
  level?: number,
): MarkdownSection | null {
  const matches = findMarkdownSections(markdown).filter(section => titlesMatch(section.title, title))
  if (!matches.length) return null
  if (level == null) return matches[0]
  return matches.find(section => section.level === level) ?? matches[0]
}

export function extractMarkdownSection(
  markdown: string,
  title: string,
  level?: number,
): string | null {
  const section = pickSection(markdown, title, level)
  return section ? markdown.slice(section.start, section.end).trim() : null
}

export function replaceMarkdownSection(
  markdown: string,
  title: string,
  newSection: string,
  level?: number,
): string | null {
  const section = pickSection(markdown, title, level)
  if (!section) return null
  const replacement = newSection.trim()
  const before = markdown.slice(0, section.start)
  const after = markdown.slice(section.end)
  const prefix = before.length > 0 && !before.endsWith("\n") ? "\n" : ""
  const suffix = after.length > 0 && !replacement.endsWith("\n") ? "\n" : ""
  return `${before}${prefix}${replacement}${suffix}${after}`
}
