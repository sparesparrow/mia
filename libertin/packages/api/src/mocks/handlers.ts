import { http, HttpResponse } from 'msw';
import type { AuthResponse, FeedResponse, MessagesResponse, Profile, VerifyResponse } from '../client';

const BASE = 'https://api.libertin.cz/v1';

const mockUser = {
  id: 'a1b2c3d4-0000-0000-0000-000000000001',
  email: 'user@example.com',
  verified: true,
  displayName: 'Jan Novák',
  avatar: null,
};

const mockToken = 'mock-jwt-token-libertin-dev';

// How another member appears to any authenticated client: no email. Mirrors the
// PublicUser schema in the contract — mocks must not model a shape the real API
// is forbidden to return, or clients get built against a leak.
const publicUser = (id: string, displayName: string) => ({ id, displayName, avatar: null });

export const handlers = [
  http.post(`${BASE}/auth/login`, async () => {
    const body: AuthResponse = { token: mockToken, user: mockUser };
    return HttpResponse.json(body);
  }),
  http.post(`${BASE}/auth/register`, async () => {
    return HttpResponse.json({ token: mockToken, user: { ...mockUser, verified: false } } satisfies AuthResponse, { status: 201 });
  }),
  http.post(`${BASE}/auth/verify`, async () => {
    return HttpResponse.json({ success: true } satisfies VerifyResponse);
  }),
  http.get(`${BASE}/feed`, () => {
    const body: FeedResponse = {
      items: [
        { id: 'feed-item-1', type: 'post', content: 'Vítejte v komunitě Libertin.', author: publicUser(mockUser.id, 'Jan Novák'), createdAt: new Date().toISOString() },
        { id: 'feed-item-2', type: 'event', content: null, author: publicUser('a1b2c3d4-0000-0000-0000-000000000002', 'Eva Nováková'), createdAt: new Date(Date.now() - 3600_000).toISOString() },
      ],
      total: 2, page: 1, limit: 20,
    };
    return HttpResponse.json(body);
  }),
  http.get(`${BASE}/messages`, () => {
    return HttpResponse.json({ conversations: [{ id: 'conv-1', participant: publicUser('a1b2c3d4-0000-0000-0000-000000000003', 'Petr K.'), lastMessage: null, updatedAt: new Date().toISOString(), unreadCount: 0 }] } satisfies MessagesResponse);
  }),
  http.get(`${BASE}/profile`, () => {
    return HttpResponse.json({ id: mockUser.id, email: mockUser.email, displayName: mockUser.displayName ?? 'Anonym', avatar: null } satisfies Profile);
  }),
  http.patch(`${BASE}/profile`, async ({ request }) => {
    const patch = await request.json() as Partial<Profile>;
    return HttpResponse.json({ id: mockUser.id, email: mockUser.email, displayName: patch.displayName ?? mockUser.displayName ?? 'Anonym', avatar: patch.avatar ?? null } satisfies Profile);
  }),
];
