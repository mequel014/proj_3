// utils/normalizeUrl.js
export function normalizeUrl(u, config) {
  if (!u) return ''
  
  const clean = u.replaceAll('\\', '/')
  
  if (clean.startsWith('http')) {
    return clean
  }

  return `${config.public.apiBase}${clean}`
}