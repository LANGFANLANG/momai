import type { ProjectReference } from '@/types/project'

export function isBibliographyChapter(title: string) {
  const normalized = title.replace(/\s+/g, '').replace(/^第[0-9一二三四五六七八九十百]+章/, '')
  return (
    ['参考文献', '参考资料', 'References', 'Bibliography'].includes(normalized)
    || normalized.toLowerCase() === 'references'
    || normalized.toLowerCase() === 'bibliography'
    || normalized.endsWith('参考文献')
  )
}

export function formatReferenceEntry(ref: ProjectReference, number: number) {
  const parts = [`[${number}]`]
  if (ref.authors?.trim()) parts.push(`${ref.authors.trim().replace(/[。.]+$/, '')}.`)
  if (ref.title?.trim()) parts.push(`${ref.title.trim().replace(/[。.]+$/, '')}.`)
  const tail = [
    ref.source?.trim().replace(/[，,。.]+$/, ''),
    ref.year?.trim().replace(/[。.]+$/, ''),
  ].filter(Boolean)
  if (tail.length) parts.push(`${tail.join(', ')}.`)
  if (ref.extra?.trim()) parts.push(ref.extra.trim())
  return parts.join(' ')
}

export function applyCitationNumbers(texts: string[], refs: ProjectReference[]) {
  const refsById = new Map(refs.map(item => [item.id, item]))
  const index = new Map<string, number>()
  const order: string[] = []

  const remapped = texts.map(text =>
    text.replace(/\[cite:([^\]]+)\]/gi, (_full, rawIds: string) => {
      const numbers: string[] = []
      let hasKnownDuplicate = false
      for (const rawId of rawIds.split(',')) {
        const refId = rawId.trim()
        if (!refId || !refsById.has(refId)) continue
        if (index.has(refId)) {
          hasKnownDuplicate = true
          continue
        }
        order.push(refId)
        index.set(refId, order.length)
        numbers.push(String(index.get(refId)))
      }
      return numbers.length ? `[${numbers.join(',')}]` : (hasKnownDuplicate ? '' : `[cite:${rawIds}]`)
    }),
  )

  const bibliography = order
    .map(id => refsById.get(id))
    .filter((item): item is ProjectReference => Boolean(item))
    .map((item, i) => ({ number: i + 1, line: formatReferenceEntry(item, i + 1), ref: item }))

  return { texts: remapped, bibliography }
}
