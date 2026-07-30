const TIMEOUT_MS = 90000

async function request(path, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(`/api${path}`, { ...options, signal: controller.signal })
    if (!res.ok) {
      let detail = `요청 실패 (${res.status})`
      try {
        const body = await res.json()
        if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      } catch {
        /* JSON 아님 */
      }
      throw new Error(detail)
    }
    return await res.json()
  } catch (e) {
    if (e.name === 'AbortError') throw new Error('응답이 너무 오래 걸려요. 서버 상태를 확인해 주세요.')
    throw e
  } finally {
    clearTimeout(timer)
  }
}

export const getJson = (path) => request(path)

export const postJson = (path, body) =>
  request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

export const postFile = (path, file) => {
  const form = new FormData()
  form.append('file', file)
  return request(path, { method: 'POST', body: form })
}
