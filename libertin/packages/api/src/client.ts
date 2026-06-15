export interface LoginRequest { email: string; password: string; }
export interface RegisterRequest { email: string; password: string; }
export interface VerifyRequest { token: string; }
export interface VerifyResponse { success: boolean; }
export interface User { id: string; email: string; verified: boolean; displayName?: string; avatar?: string | null; }
export interface AuthResponse { token: string; user: User; }
export interface Profile { id: string; email: string; displayName: string; avatar?: string | null; }
export interface UpdateProfileRequest { displayName?: string; avatar?: string; }
export interface FeedItem { id: string; type: 'post' | 'photo' | 'event'; content?: string | null; author?: User; createdAt: string; }
export interface FeedResponse { items: FeedItem[]; total: number; page?: number; limit?: number; }
export interface Conversation { id: string; participant: User; lastMessage?: string | null; updatedAt: string; unreadCount?: number; }
export interface MessagesResponse { conversations: Conversation[]; }
export interface ErrorResponse { message: string; code?: string; }

type RequestOptions = { token?: string };

async function request<T>(baseURL: string, path: string, init: RequestInit, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
  };
  const res = await fetch(`${baseURL}${path}`, { ...init, headers });
  if (!res.ok) {
    const err: ErrorResponse = await res.json().catch(() => ({ message: res.statusText }));
    throw Object.assign(new Error(err.message), { status: res.status, code: err.code });
  }
  return res.json() as Promise<T>;
}

export interface LibertinClient {
  auth: {
    login(body: LoginRequest): Promise<AuthResponse>;
    register(body: RegisterRequest): Promise<AuthResponse>;
    verify(body: VerifyRequest): Promise<VerifyResponse>;
  };
  feed: { get(params?: { page?: number; limit?: number }, token?: string): Promise<FeedResponse>; };
  messages: { list(token: string): Promise<MessagesResponse>; };
  profile: { get(token: string): Promise<Profile>; update(body: UpdateProfileRequest, token: string): Promise<Profile>; };
}

export function createClient(baseURL: string): LibertinClient {
  return {
    auth: {
      login: (body) => request<AuthResponse>(baseURL, '/auth/login', { method: 'POST', body: JSON.stringify(body) }),
      register: (body) => request<AuthResponse>(baseURL, '/auth/register', { method: 'POST', body: JSON.stringify(body) }),
      verify: (body) => request<VerifyResponse>(baseURL, '/auth/verify', { method: 'POST', body: JSON.stringify(body) }),
    },
    feed: {
      get: (params = {}, token) => {
        const qs = new URLSearchParams();
        if (params.page !== undefined) qs.set('page', String(params.page));
        if (params.limit !== undefined) qs.set('limit', String(params.limit));
        return request<FeedResponse>(baseURL, `/feed?${qs}`, { method: 'GET' }, { token });
      },
    },
    messages: { list: (token) => request<MessagesResponse>(baseURL, '/messages', { method: 'GET' }, { token }) },
    profile: {
      get: (token) => request<Profile>(baseURL, '/profile', { method: 'GET' }, { token }),
      update: (body, token) => request<Profile>(baseURL, '/profile', { method: 'PATCH', body: JSON.stringify(body) }, { token }),
    },
  };
}
