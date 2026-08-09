// Hand-written client, locked to contracts/openapi.snapshot.yaml (no codegen
// yet — E11-T3). Everything below mirrors a schema in the snapshot; when the
// snapshot changes, this file changes in the same commit.
//
// The 2FA surface (`auth.twoFactor`, `auth.passkey`, `auth.recovery`,
// `auth.sessions`) is DESIGNED, not observed — see the PROVENANCE header of the
// snapshot. It runs against MSW mocks today and against nothing else until the
// backend exists (D-003).

// --- roles (B1) -------------------------------------------------------------
// Never present on PublicUser: a role tells an attacker which accounts are
// worth attacking and outs staff. Never accepted in UpdateProfileRequest: a
// member must not be able to grant themselves one.
export type UserRole = 'admin' | 'editor' | 'member' | 'guest';

export interface LoginRequest { email: string; password: string; }
export interface RegisterRequest { email: string; password: string; }
export interface VerifyRequest { token: string; }
export interface VerifyResponse { success: boolean; }
// Another member, as returned to any authenticated client. Carries NO email and
// NO role — see the PublicUser note in contracts/openapi.snapshot.yaml.
export interface PublicUser { id: string; displayName: string; avatar?: string | null; }
// The authenticated member themselves; only ever returned for the caller.
export interface User {
  id: string;
  email: string;
  verified: boolean;
  role: UserRole;
  displayName?: string;
  avatar?: string | null;
  twoFactorEnabled?: boolean;
}
export interface AuthResponse { token: string; expiresIn?: number; user: User; }
export interface Profile { id: string; email: string; displayName: string; role: UserRole; avatar?: string | null; }
export interface UpdateProfileRequest { displayName?: string; avatar?: string; }
export interface FeedItem { id: string; type: 'post' | 'photo' | 'event'; content?: string | null; author?: PublicUser; createdAt: string; }
export interface FeedResponse { items: FeedItem[]; total: number; page?: number; limit?: number; }
export interface Conversation { id: string; participant: PublicUser; lastMessage?: string | null; updatedAt: string; unreadCount?: number; }
export interface MessagesResponse { conversations: Conversation[]; }

// Stable codes from ADR 0001 §9.5. Kept open (`| (string & {})`) because the
// server may return a code we have not modelled and a client must not crash on
// one — the union still autocompletes the known ones.
export type ErrorCode =
  | 'MFA_REQUIRED'
  | 'MFA_INVALID_CODE'
  | 'MFA_TOKEN_EXPIRED'
  | 'MFA_RATE_LIMITED'
  | 'MFA_FACTOR_EXISTS'
  | 'MFA_LAST_FACTOR'
  | 'MFA_METHOD_DISABLED'
  | 'STEPUP_REQUIRED'
  | 'RECOVERY_PENDING'
  | 'PHONE_COOLDOWN'
  // eslint-disable-next-line @typescript-eslint/ban-types
  | (string & {});
export interface ErrorResponse { message: string; code?: ErrorCode; }

// --- 2FA: login flow --------------------------------------------------------
export type TwoFactorMethod = 'totp' | 'sms' | 'passkey';

export interface TwoFactorMethodRef {
  type: TwoFactorMethod;
  factorId: string;
  default?: boolean;
  /** Member-chosen label, passkey only. Never phone digits, not even masked. */
  label?: string;
}

/** 200 branch of POST /auth/login when a second factor is required. */
export interface TwoFactorChallenge {
  status: 'mfa_required';
  /** Single-use, TTL 300 s, audience `mfa`. No resource endpoint accepts it. */
  mfaToken: string;
  expiresIn: number;
  methods: TwoFactorMethodRef[];
}

/** The discriminated union POST /auth/login actually returns. */
export type LoginResult = AuthResponse | TwoFactorChallenge;

export function isTwoFactorChallenge(result: LoginResult): result is TwoFactorChallenge {
  return (result as TwoFactorChallenge).status === 'mfa_required';
}

/**
 * Thrown by `auth.login()` when the server answers with a challenge instead of
 * a session. Existing call sites read `res.token` / `res.user`, so `login()`
 * keeps returning `AuthResponse` and refuses to hand back a challenge typed as
 * a session — a caller that ignores 2FA fails loudly rather than reading
 * `undefined` as a token. Callers that handle 2FA use `loginWithChallenge()`.
 */
export class TwoFactorRequiredError extends Error {
  readonly code = 'MFA_REQUIRED' as const;
  readonly status = 200;
  readonly challenge: TwoFactorChallenge;
  constructor(challenge: TwoFactorChallenge) {
    super('Two-factor authentication required');
    this.name = 'TwoFactorRequiredError';
    this.challenge = challenge;
  }
}

export interface TwoFactorChallengeRequest {
  mfaToken: string;
  method: TwoFactorMethod;
  factorId?: string;
}
export interface SmsChallengeResult { sent: boolean; retryAfter?: number; }
export interface PasskeyChallengeResult { publicKey: PublicKeyCredentialRequestOptionsJSON; }
export interface TotpChallengeResult { ok: boolean; }
export type TwoFactorChallengeResult = SmsChallengeResult | PasskeyChallengeResult | TotpChallengeResult;

export interface TwoFactorVerifyRequest {
  mfaToken: string;
  method: TwoFactorMethod;
  factorId?: string;
  code?: string;
  assertionResponse?: AuthenticatorAssertionJSON;
  /** Opt-in only; ignored by the server for admin/editor roles (ADR §7.3). */
  rememberDevice?: boolean;
}
export interface TwoFactorAuthResponse extends AuthResponse {
  deviceTrustToken?: string;
  deviceTrustExpiresAt?: string;
}
export interface RecoveryCodeRequest { mfaToken: string; code: string; }
export interface RecoveryCodeAuthResponse extends AuthResponse { remainingCodes: number; }
export interface PasskeyLoginRequest { assertionResponse: AuthenticatorAssertionJSON; }

// --- 2FA: factor management -------------------------------------------------
export interface TwoFactorFactor {
  factorId: string;
  type: TwoFactorMethod;
  /** Member-chosen. Never phone digits. */
  label?: string;
  status: 'pending' | 'active' | 'disabled';
  default?: boolean;
  createdAt: string;
  lastUsedAt?: string | null;
  /** SMS only — S-4 24 h delay after (re)binding a number. */
  usableFrom?: string | null;
}
export interface TwoFactorFactorsResponse {
  factors: TwoFactorFactor[];
  recoveryCodesRemaining?: number;
}
export interface TotpEnrollResponse {
  factorId: string;
  otpauthUri: string;
  secretBase32: string;
  digits: number;
  period: number;
  algorithm: 'SHA1' | 'SHA256' | 'SHA512';
}
export interface FactorActivateRequest { factorId: string; code: string; }
export interface FactorActivateResponse {
  activated: boolean;
  /** Only on the first activated factor, only once. */
  recoveryCodes?: string[];
}
export interface SmsEnrollRequest { phone: string; }
export interface SmsEnrollResponse { factorId: string; retryAfter?: number; }
export interface SmsActivateResponse extends FactorActivateResponse { usableFrom?: string; }
export interface PasskeyRegisterRequest { attestationResponse: AuthenticatorAttestationJSON; label: string; }
export interface PasskeyRegisterResponse { factorId: string; label?: string; recoveryCodes?: string[]; }
export interface RecoveryCodesResponse { codes: string[]; generatedAt: string; }
export interface RecoveryCodesStatus { remaining: number; generatedAt?: string | null; }

// --- recovery and sessions --------------------------------------------------
export interface RecoveryRequest { email: string; password: string; }
export interface RecoveryStatus {
  state: 'none' | 'pending' | 'cancelled' | 'completed';
  scheduledFor?: string | null;
  requestedAt?: string | null;
}
export interface RecoveryCancelRequest { cancelToken: string; }
export interface Session {
  id: string;
  deviceLabel?: string;
  platform?: 'web' | 'ios' | 'android' | 'unknown';
  /** City granularity at most. Never coordinates. */
  approximateLocation?: string | null;
  createdAt: string;
  lastSeenAt: string;
  current: boolean;
  deviceTrusted?: boolean;
}
export interface SessionsResponse { sessions: Session[]; }

// --- WebAuthn transport shapes ---------------------------------------------
// Plain JSON (base64url strings), not DOM types: the same client runs in React
// Native, where `PublicKeyCredential` does not exist.
export interface PublicKeyCredentialDescriptorJSON {
  type: 'public-key';
  id: string;
  transports?: string[];
}
export interface PublicKeyCredentialRequestOptionsJSON {
  challenge: string;
  rpId?: string;
  timeout?: number;
  userVerification?: 'required' | 'preferred' | 'discouraged';
  allowCredentials?: PublicKeyCredentialDescriptorJSON[];
}
export interface PublicKeyCredentialCreationOptionsJSON {
  challenge: string;
  rp: { id?: string; name: string };
  /** `name` is deliberately neutral — an OS passkey manager displays it (R-1). */
  user: { id: string; name: string; displayName: string };
  pubKeyCredParams: { type: 'public-key'; alg: number }[];
  timeout?: number;
  attestation?: 'none' | 'indirect' | 'direct' | 'enterprise';
  authenticatorSelection?: {
    authenticatorAttachment?: 'platform' | 'cross-platform';
    residentKey?: 'discouraged' | 'preferred' | 'required';
    userVerification?: 'required' | 'preferred' | 'discouraged';
  };
  excludeCredentials?: PublicKeyCredentialDescriptorJSON[];
}
export interface AuthenticatorAssertionJSON {
  id: string;
  rawId: string;
  type: 'public-key';
  response: {
    clientDataJSON: string;
    authenticatorData: string;
    signature: string;
    userHandle?: string | null;
  };
}
export interface AuthenticatorAttestationJSON {
  id: string;
  rawId: string;
  type: 'public-key';
  response: {
    clientDataJSON: string;
    attestationObject: string;
    transports?: string[];
  };
}

type RequestOptions = { token?: string | undefined };

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
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface TwoFactorApi {
  /** Ask for a factor to be challenged. Authorised by mfaToken, not a session. */
  challenge(body: TwoFactorChallengeRequest): Promise<TwoFactorChallengeResult>;
  /** Exchange the one-time mfaToken for a session. */
  verify(body: TwoFactorVerifyRequest): Promise<TwoFactorAuthResponse>;
  /** Redeem a single-use recovery code instead of a factor. */
  recoveryCode(body: RecoveryCodeRequest): Promise<RecoveryCodeAuthResponse>;
  listFactors(token: string): Promise<TwoFactorFactorsResponse>;
  deleteFactor(factorId: string, token: string): Promise<void>;
  totpEnroll(token: string): Promise<TotpEnrollResponse>;
  totpActivate(body: FactorActivateRequest, token: string): Promise<FactorActivateResponse>;
  smsEnroll(body: SmsEnrollRequest, token: string): Promise<SmsEnrollResponse>;
  smsActivate(body: FactorActivateRequest, token: string): Promise<SmsActivateResponse>;
  passkeyRegisterOptions(token: string): Promise<PublicKeyCredentialCreationOptionsJSON>;
  passkeyRegister(body: PasskeyRegisterRequest, token: string): Promise<PasskeyRegisterResponse>;
  regenerateRecoveryCodes(token: string): Promise<RecoveryCodesResponse>;
  recoveryCodesStatus(token: string): Promise<RecoveryCodesStatus>;
}

export interface LibertinClient {
  auth: {
    /**
     * Password step, narrowed to the session case. Throws
     * `TwoFactorRequiredError` (carrying the challenge) when the server needs a
     * second factor, so no caller can mistake a challenge for a session.
     */
    login(body: LoginRequest): Promise<AuthResponse>;
    /** The honest contract shape: session OR challenge. Use `isTwoFactorChallenge`. */
    loginWithChallenge(body: LoginRequest): Promise<LoginResult>;
    register(body: RegisterRequest): Promise<AuthResponse>;
    verify(body: VerifyRequest): Promise<VerifyResponse>;
    twoFactor: TwoFactorApi;
    passkey: {
      /** No identifier on purpose — conditional UI, and no enumeration oracle. */
      options(): Promise<PublicKeyCredentialRequestOptionsJSON>;
      login(body: PasskeyLoginRequest): Promise<AuthResponse>;
    };
    recovery: {
      request(body: RecoveryRequest): Promise<RecoveryStatus>;
      status(token: string): Promise<RecoveryStatus>;
      /** Unauthenticated by design: whoever still holds the account must be able to stop a hostile reset. */
      cancel(body: RecoveryCancelRequest): Promise<RecoveryStatus>;
    };
    sessions: {
      list(token: string): Promise<SessionsResponse>;
      revoke(id: string, token: string): Promise<void>;
      revokeAll(token: string): Promise<void>;
    };
  };
  feed: { get(params?: { page?: number; limit?: number }, token?: string): Promise<FeedResponse>; };
  messages: { list(token: string): Promise<MessagesResponse>; };
  profile: { get(token: string): Promise<Profile>; update(body: UpdateProfileRequest, token: string): Promise<Profile>; };
}

export function createClient(baseURL: string): LibertinClient {
  const post = <T>(path: string, body?: unknown, token?: string) =>
    request<T>(baseURL, path, { method: 'POST', ...(body === undefined ? {} : { body: JSON.stringify(body) }) }, { token });
  const get = <T>(path: string, token?: string) => request<T>(baseURL, path, { method: 'GET' }, { token });
  const del = <T>(path: string, token?: string) => request<T>(baseURL, path, { method: 'DELETE' }, { token });

  const loginWithChallenge = (body: LoginRequest) =>
    post<LoginResult>('/auth/login', body);

  return {
    auth: {
      loginWithChallenge,
      login: async (body) => {
        const result = await loginWithChallenge(body);
        if (isTwoFactorChallenge(result)) throw new TwoFactorRequiredError(result);
        return result;
      },
      register: (body) => post<AuthResponse>('/auth/register', body),
      verify: (body) => post<VerifyResponse>('/auth/verify', body),
      twoFactor: {
        challenge: (body) => post<TwoFactorChallengeResult>('/auth/2fa/challenge', body),
        verify: (body) => post<TwoFactorAuthResponse>('/auth/2fa/verify', body),
        recoveryCode: (body) => post<RecoveryCodeAuthResponse>('/auth/2fa/recovery-code', body),
        listFactors: (token) => get<TwoFactorFactorsResponse>('/auth/2fa/factors', token),
        deleteFactor: (factorId, token) =>
          del<void>(`/auth/2fa/factors/${encodeURIComponent(factorId)}`, token),
        totpEnroll: (token) => post<TotpEnrollResponse>('/auth/2fa/totp/enroll', undefined, token),
        totpActivate: (body, token) => post<FactorActivateResponse>('/auth/2fa/totp/activate', body, token),
        smsEnroll: (body, token) => post<SmsEnrollResponse>('/auth/2fa/sms/enroll', body, token),
        smsActivate: (body, token) => post<SmsActivateResponse>('/auth/2fa/sms/activate', body, token),
        passkeyRegisterOptions: (token) =>
          post<PublicKeyCredentialCreationOptionsJSON>('/auth/2fa/passkey/register/options', undefined, token),
        passkeyRegister: (body, token) => post<PasskeyRegisterResponse>('/auth/2fa/passkey/register', body, token),
        regenerateRecoveryCodes: (token) =>
          post<RecoveryCodesResponse>('/auth/2fa/recovery-codes/regenerate', undefined, token),
        recoveryCodesStatus: (token) => get<RecoveryCodesStatus>('/auth/2fa/recovery-codes/status', token),
      },
      passkey: {
        options: () => post<PublicKeyCredentialRequestOptionsJSON>('/auth/passkey/options', {}),
        login: (body) => post<AuthResponse>('/auth/passkey/login', body),
      },
      recovery: {
        request: (body) => post<RecoveryStatus>('/auth/recovery/request', body),
        status: (token) => get<RecoveryStatus>('/auth/recovery/status', token),
        cancel: (body) => post<RecoveryStatus>('/auth/recovery/cancel', body),
      },
      sessions: {
        list: (token) => get<SessionsResponse>('/auth/sessions', token),
        revoke: (id, token) => del<void>(`/auth/sessions/${encodeURIComponent(id)}`, token),
        revokeAll: (token) => del<void>('/auth/sessions', token),
      },
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
