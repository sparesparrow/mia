# 0024. MIA account, vehicle and Pi identity boundaries

- Status: Accepted
- Date: 2026-11-20
- Requirements: REQ-VOICE-008, REQ-VOICE-030, REQ-VOICE-031, REQ-VOICE-032, REQ-VOICE-033, REQ-VOICE-034

## Context

MIA's current Pi and voice software has no central account registry, vehicle registry, device enrollment service or
billing backend. A future central MIA service needs stable identity boundaries for accounts, vehicles and Pi installs
without coupling them to one another or to a payment provider. Local speech recognition must remain usable without a
paid speech provider.

## Decision

- **Account ID.** A future central MIA service assigns each account an opaque MIA account ID. It is not derived from
  a VIN, a Pi identity or other account metadata. The ID identifies an account; possession of the ID alone does not
  authenticate a user or device.
- **Billing ID.** The central service manages the payment processor's customer ID and maps it to the MIA account ID.
  This processor customer ID is distinct from the MIA account ID and is not an identity credential. The processor
  choice remains open. Billing IDs and processor credentials are managed server-side, not by the Pi.
- **Vehicle metadata.** A VIN is stored separately as vehicle metadata linked to an MIA account. It is never used to
  derive an account ID and is not included in the Pi hostname.
- **Pi installation identity.** Each Pi installation has a dedicated key pair registered to an MIA account. The
  server records the fingerprint of the public key and verifies a signed challenge using the corresponding public key
  after confirming its fingerprint. Authentication therefore proves possession of the private key; the fingerprint
  by itself is not proof. The key lifecycle supports rotation and revocation.
- **Speech provider boundary.** Local Whisper remains the default speech-to-text path. A paid speech provider is an
  optional, separately enabled service; creating an account or billing ID does not enable it. Processor choice and
  speech-provider choice are independent.
- **Scope.** This ADR records identity and provider boundaries only. It does not implement account registration,
  billing, a vehicle registry, Pi enrollment or key lifecycle services.

## Consequences

- Account, billing, vehicle and Pi identities can be managed independently by a future central service.
- A VIN is not exposed through an account identifier or the Pi's network hostname.
- A copied public-key fingerprint cannot authenticate a Pi without proof of private-key possession.
- Implementations must define secure private-key storage and the protocol for enrollment, rotation and revocation.
- The default voice path remains local; optional paid speech processing requires a separate explicit configuration.

## Sources

`spec/requirements/voice.yaml` (REQ-VOICE-008, REQ-VOICE-030 through REQ-VOICE-034),
`apps/rpi-backend/py-api/services/stt_service.py`.
