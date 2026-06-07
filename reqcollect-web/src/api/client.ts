/* ── API Client (fetch 封装) — 带 Auth 拦截器 ── */

const BASE = '/api'

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('reqcollect_token')
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
    ...(options?.headers as Record<string, string> || {}),
  }

  const resp = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  })

  // 401 → redirect to login
  if (resp.status === 401) {
    localStorage.removeItem('reqcollect_token')
    // Avoid redirect loop on login page
    if (!window.location.hash.startsWith('#/login')) {
      window.location.hash = '#/login'
    }
    throw new Error('HTTP 401: Not authenticated')
  }

  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`HTTP ${resp.status}: ${text.slice(0, 200)}`)
  }

  return resp.json()
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>(path)
}

export async function apiPost<T>(path: string, body?: any): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

export async function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}

export async function apiPatch<T>(path: string, body?: any): Promise<T> {
  return request<T>(path, {
    method: 'PATCH',
    body: body ? JSON.stringify(body) : undefined,
  })
}

/* ── SSE Stream (adds Authorization header) ── */
export function readSSEStream(
  body: any,
  onEvent: (event: Record<string, any>) => void,
  onError: (err: Error) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
  }

  ;(async () => {
    try {
      const resp = await fetch(`${BASE}/pm/agent`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (resp.status === 401) {
        localStorage.removeItem('reqcollect_token')
        if (!window.location.hash.startsWith('#/login')) {
          window.location.hash = '#/login'
        }
        onError(new Error('Not authenticated'))
        return
      }
      if (!resp.ok || !resp.body) {
        onError(new Error(`HTTP ${resp.status}`))
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        buffer = buffer.replace(/\r\n/g, '\n')
        const frames = buffer.split('\n\n')
        buffer = frames.pop() || ''
        for (const frame of frames) {
          const dataLine = frame.split('\n').find(l => l.startsWith('data: '))
          if (!dataLine) continue
          try {
            onEvent(JSON.parse(dataLine.slice(6)))
          } catch { /* skip bad frame */ }
        }
      }
      onDone()
    } catch (e: any) {
      if (e.name !== 'AbortError') onError(e)
    }
  })()

  return controller
}
