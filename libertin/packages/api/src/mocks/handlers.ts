import { http, HttpResponse } from 'msw';
import type {
  AuthResponse,
  FactorActivateResponse,
  FeedResponse,
  LoginRequest,
  MessagesResponse,
  PasskeyRegisterResponse,
  Profile,
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
  RecoveryCodeAuthResponse,
  RecoveryCodeRequest,
  RecoveryCodesResponse,
  RecoveryCodesStatus,
  RecoveryStatus,
  SessionsResponse,
  SmsActivateResponse,
  SmsEnrollResponse,
  TotpEnrollResponse,
  TwoFactorAuthResponse,
  TwoFactorChallenge,
  TwoFactorChallengeRequest,
  TwoFactorChallengeResult,
  TwoFactorFactorsResponse,
  TwoFactorVerifyRequest,
  VerifyResponse,
} from '../client';

const BASE = 'https://api.libertin.cz/v1';

const mockUser = {
  id: 'a1b2c3d4-0000-0000-0000-000000000001',
  email: 'user@example.com',
  verified: true,
  role: 'member' as const,
  displayName: 'Jan Novák',
  avatar: null,
  twoFactorEnabled: false,
};

const mockToken = 'mock-jwt-token-libertin-dev';
const mockMfaToken = 'mock-mfa-token-libertin-dev';
/** The only code the mock accepts, for every factor type. */
const MOCK_CODE = '123456';

// Any address containing "2fa" takes the challenge branch of POST /auth/login;
// everything else logs straight in, so the existing flows keep booting offline.
// Try `2fa@example.com` to exercise the second factor.
const wantsChallenge = (email: string | undefined) => (email ?? '').toLowerCase().includes('2fa');

// How another member appears to any authenticated client: no email, no role.
// Mirrors the PublicUser schema in the contract — mocks must not model a shape
// the real API is forbidden to return, or clients get built against a leak.
const publicUser = (id: string, displayName: string) => ({ id, displayName, avatar: null });

const authResponse = (): AuthResponse => ({
  token: mockToken,
  expiresIn: 600,
  user: { ...mockUser, twoFactorEnabled: true },
});

const challenge = (): TwoFactorChallenge => ({
  status: 'mfa_required',
  mfaToken: mockMfaToken,
  expiresIn: 300,
  methods: [
    { type: 'totp', factorId: 'factor-totp-1', default: true },
    // No label and no digits for SMS — the challenge screen is reachable with
    // the password alone, so it must not leak anything about the number.
    { type: 'sms', factorId: 'factor-sms-1' },
    { type: 'passkey', factorId: 'factor-passkey-1', label: 'Klíč 1' },
  ],
});

const invalidCode = () =>
  HttpResponse.json({ message: 'Kód se nepodařilo ověřit.', code: 'MFA_INVALID_CODE' }, { status: 401 });

const assertionOptions = (): PublicKeyCredentialRequestOptionsJSON => ({
  challenge: 'bW9jay1jaGFsbGVuZ2U',
  rpId: 'libertin.cz',
  timeout: 60_000,
  userVerification: 'required',
  allowCredentials: [],
});

export const handlers = [
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Partial<LoginRequest>;
    if (wantsChallenge(body.email)) return HttpResponse.json(challenge());
    return HttpResponse.json({ token: mockToken, expiresIn: 600, user: mockUser } satisfies AuthResponse);
  }),
  http.post(`${BASE}/auth/register`, async () => {
    return HttpResponse.json(
      { token: mockToken, expiresIn: 600, user: { ...mockUser, verified: false, role: 'guest' } } satisfies AuthResponse,
      { status: 201 },
    );
  }),
  http.post(`${BASE}/auth/verify`, async () => {
    return HttpResponse.json({ success: true } satisfies VerifyResponse);
  }),

  // --- 2FA login flow (designed surface, ADR 0001 §9.2) ---------------------
  http.post(`${BASE}/auth/2fa/challenge`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Partial<TwoFactorChallengeRequest>;
    if (body.method === 'sms') {
      return HttpResponse.json({ sent: true, retryAfter: 60 } satisfies TwoFactorChallengeResult);
    }
    if (body.method === 'passkey') {
      return HttpResponse.json({ publicKey: assertionOptions() } satisfies TwoFactorChallengeResult);
    }
    return HttpResponse.json({ ok: true } satisfies TwoFactorChallengeResult);
  }),
  http.post(`${BASE}/auth/2fa/verify`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Partial<TwoFactorVerifyRequest>;
    const passkey = body.method === 'passkey' && body.assertionResponse !== undefined;
    if (!passkey && body.code !== MOCK_CODE) return invalidCode();
    return HttpResponse.json({
      ...authResponse(),
      ...(body.rememberDevice ? { deviceTrustToken: 'mock-device-trust-token' } : {}),
    } satisfies TwoFactorAuthResponse);
  }),
  http.post(`${BASE}/auth/2fa/recovery-code`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as Partial<RecoveryCodeRequest>;
    if (!body.code) return invalidCode();
    return HttpResponse.json({ ...authResponse(), remainingCodes: 9 } satisfies RecoveryCodeAuthResponse);
  }),
  http.post(`${BASE}/auth/passkey/options`, () => HttpResponse.json(assertionOptions())),
  http.post(`${BASE}/auth/passkey/login`, () => HttpResponse.json(authResponse())),

  // --- factor management (ADR 0001 §9.3) -----------------------------------
  http.get(`${BASE}/auth/2fa/factors`, () => {
    return HttpResponse.json({
      factors: [
        {
          factorId: 'factor-totp-1',
          type: 'totp',
          status: 'active',
          default: true,
          createdAt: '2026-07-01T10:00:00.000Z',
          lastUsedAt: '2026-08-01T18:20:00.000Z',
        },
        {
          factorId: 'factor-passkey-1',
          type: 'passkey',
          label: 'Klíč 1',
          status: 'active',
          createdAt: '2026-07-05T09:00:00.000Z',
          lastUsedAt: null,
        },
      ],
      recoveryCodesRemaining: 8,
    } satisfies TwoFactorFactorsResponse);
  }),
  http.delete(`${BASE}/auth/2fa/factors/:factorId`, ({ params }) => {
    // Refuses to leave the account with no way back in (MFA_LAST_FACTOR).
    if (params.factorId === 'factor-totp-1') {
      return HttpResponse.json(
        { message: 'Toto je poslední faktor.', code: 'MFA_LAST_FACTOR' },
        { status: 409 },
      );
    }
    return new HttpResponse(null, { status: 204 });
  }),
  http.post(`${BASE}/auth/2fa/totp/enroll`, () => {
    return HttpResponse.json({
      factorId: 'factor-totp-new',
      // Neutral label on purpose (ADR risk R-1): an authenticator app shows it
      // to anyone holding the unlocked device.
      otpauthUri: 'otpauth://totp/Ucet?secret=JBSWY3DPEHPK3PXP&issuer=Ucet&digits=6&period=30',
      secretBase32: 'JBSWY3DPEHPK3PXP',
      digits: 6,
      period: 30,
      algorithm: 'SHA1',
    } satisfies TotpEnrollResponse);
  }),
  http.post(`${BASE}/auth/2fa/totp/activate`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as { code?: string };
    if (body.code !== MOCK_CODE) return invalidCode();
    return HttpResponse.json({
      activated: true,
      recoveryCodes: [
        'A1B2C3D4E5', 'F6G7H8J9K0', 'M1N2P3Q4R5', 'S6T7V8W9X0', 'Y1Z2A3B4C5',
        'D6E7F8G9H0', 'J1K2M3N4P5', 'Q6R7S8T9V0', 'W1X2Y3Z4A5', 'B6C7D8E9F0',
      ],
    } satisfies FactorActivateResponse);
  }),
  http.post(`${BASE}/auth/2fa/sms/enroll`, () => {
    // The number is never echoed back, not even masked.
    return HttpResponse.json({ factorId: 'factor-sms-new', retryAfter: 60 } satisfies SmsEnrollResponse);
  }),
  http.post(`${BASE}/auth/2fa/sms/activate`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as { code?: string };
    if (body.code !== MOCK_CODE) return invalidCode();
    // S-4: a freshly bound number is only usable after 24 h.
    return HttpResponse.json({
      activated: true,
      usableFrom: new Date(Date.now() + 24 * 3600_000).toISOString(),
    } satisfies SmsActivateResponse);
  }),
  http.post(`${BASE}/auth/2fa/passkey/register/options`, () => {
    return HttpResponse.json({
      challenge: 'bW9jay1yZWctY2hhbGxlbmdl',
      rp: { id: 'libertin.cz', name: 'Libertin' },
      // Neutral `name` (R-1) — no e-mail, nothing that outs membership in an OS
      // passkey manager.
      user: { id: 'dXNlci1oYW5kbGU', name: 'Ucet', displayName: 'Ucet' },
      pubKeyCredParams: [
        { type: 'public-key', alg: -7 },
        { type: 'public-key', alg: -257 },
      ],
      timeout: 60_000,
      attestation: 'none',
      authenticatorSelection: { residentKey: 'preferred', userVerification: 'required' },
      excludeCredentials: [],
    } satisfies PublicKeyCredentialCreationOptionsJSON);
  }),
  http.post(`${BASE}/auth/2fa/passkey/register`, async ({ request }) => {
    const body = (await request.json().catch(() => ({}))) as { label?: string };
    return HttpResponse.json({
      factorId: 'factor-passkey-new',
      label: body.label ?? 'Klíč',
    } satisfies PasskeyRegisterResponse);
  }),
  http.post(`${BASE}/auth/2fa/recovery-codes/regenerate`, () => {
    return HttpResponse.json({
      codes: [
        'G1H2J3K4M5', 'N6P7Q8R9S0', 'T1V2W3X4Y5', 'Z6A7B8C9D0', 'E1F2G3H4J5',
        'K6M7N8P9Q0', 'R1S2T3V4W5', 'X6Y7Z8A9B0', 'C1D2E3F4G5', 'H6J7K8M9N0',
      ],
      generatedAt: new Date().toISOString(),
    } satisfies RecoveryCodesResponse);
  }),
  http.get(`${BASE}/auth/2fa/recovery-codes/status`, () => {
    // Counts only — never the codes.
    return HttpResponse.json({ remaining: 8, generatedAt: '2026-07-01T10:00:00.000Z' } satisfies RecoveryCodesStatus);
  }),

  // --- recovery and sessions (ADR 0001 §9.4) -------------------------------
  http.post(`${BASE}/auth/recovery/request`, () => {
    return HttpResponse.json(
      {
        state: 'pending',
        requestedAt: new Date().toISOString(),
        scheduledFor: new Date(Date.now() + 72 * 3600_000).toISOString(),
      } satisfies RecoveryStatus,
      { status: 202 },
    );
  }),
  http.get(`${BASE}/auth/recovery/status`, () => {
    return HttpResponse.json({ state: 'none', requestedAt: null, scheduledFor: null } satisfies RecoveryStatus);
  }),
  http.post(`${BASE}/auth/recovery/cancel`, () => {
    return HttpResponse.json({ state: 'cancelled', requestedAt: null, scheduledFor: null } satisfies RecoveryStatus);
  }),
  http.get(`${BASE}/auth/sessions`, () => {
    return HttpResponse.json({
      sessions: [
        {
          id: 'session-current',
          deviceLabel: 'Tento prohlížeč',
          platform: 'web',
          approximateLocation: 'Praha',
          createdAt: '2026-08-01T08:00:00.000Z',
          lastSeenAt: new Date().toISOString(),
          current: true,
          deviceTrusted: false,
        },
        {
          id: 'session-phone',
          deviceLabel: 'Telefon',
          platform: 'android',
          approximateLocation: null,
          createdAt: '2026-07-20T19:30:00.000Z',
          lastSeenAt: '2026-08-05T21:10:00.000Z',
          current: false,
          deviceTrusted: true,
        },
      ],
    } satisfies SessionsResponse);
  }),
  http.delete(`${BASE}/auth/sessions/:id`, () => new HttpResponse(null, { status: 204 })),
  http.delete(`${BASE}/auth/sessions`, () => new HttpResponse(null, { status: 204 })),

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
    return HttpResponse.json({ id: mockUser.id, email: mockUser.email, displayName: mockUser.displayName ?? 'Anonym', role: mockUser.role, avatar: null } satisfies Profile);
  }),
  http.patch(`${BASE}/profile`, async ({ request }) => {
    const patch = await request.json() as Partial<Profile>;
    // `role` is deliberately not read from the patch: it is operator-granted,
    // and honouring it here would model a privilege escalation the real API
    // must reject.
    return HttpResponse.json({ id: mockUser.id, email: mockUser.email, displayName: patch.displayName ?? mockUser.displayName ?? 'Anonym', role: mockUser.role, avatar: patch.avatar ?? null } satisfies Profile);
  }),
];
