# Frontend Auth Migration Guide — Password → OTP-Only

**Audience:** the frontend agent rewriting the existing customer web/mobile app.
**Status of backend:** OTP-only auth is already live. There is **no** password-based register/login endpoint for clients. Any password field, password input, password validator, "forgot password" screen, or `password` payload key in the current frontend is **dead code that maps to nothing on the server** and must be removed.

> The stale `CUSTOMER_API_GUIDE.md` (sections 1.1–1.4) describes a password flow that **does not exist in the codebase**. Trust this file and `FRONTEND_INTEGRATION.md §2`, not that one. `CUSTOMER_API_GUIDE.md` will be rewritten separately.

---

## 1. The rule

For users with `role = client` (i.e. every customer of this app):

- **Registration** = phone + name → OTP sent → OTP verified → session issued.
- **Login** = phone → OTP sent → OTP verified → session issued.
- **Phone change** (authenticated) = new phone → OTP sent → OTP verified → all sessions invalidated → user logs in again.
- **There is no password.** Not for register, not for login, not for profile update, not for "forgot password", not for re-auth before sensitive actions. There is nothing to hash, store, mask, validate length on, or "show/hide".

If you find a password field in the existing frontend, delete it. Do not migrate it. Do not keep it "for later". The User table has a `password` column reserved for staff (admin/manager/courier) accounts — the **client app must never read or write it**.

---

## 2. What to delete from the existing frontend

Search the codebase for these and remove every match:

| Pattern | Action |
|---|---|
| `password` field in any register form / DTO / state slice / form schema | Delete |
| `confirmPassword`, `password_confirmation`, `repeatPassword` | Delete |
| Password strength meter, min-length validator, "show password" eye toggle | Delete |
| `POST /api/auth/login` body containing `password` | Replace with `{phone}` (see §4.3) |
| `POST /api/auth/register` body containing `password` | Replace with `{phone, first_name, last_name?, language?, telegram_id?}` (see §4.1) |
| `PATCH /api/auth/me/update` body containing `password` | Drop the field; this endpoint accepts only `first_name`, `last_name`, `language` |
| Any "Change password" screen, button, route, modal, settings row | Delete |
| Any "Forgot password" screen / route / link | Delete (recovery is automatic — they just log in again with OTP) |
| `POST /api/auth/verify` and `POST /api/auth/resend-code` calls | Replace with the four OTP endpoints in §4 (these old ones do not exist on the server) |
| Login error mapping for `"Invalid credentials"` / `"User not found"` | Replace with the OTP error map in §6 |
| Schema-level password regex (e.g. `/^(?=.*\d)(?=.*[A-Z]).{8,}$/`) | Delete |

Test files, Storybook stories, mocks, MSW handlers — purge `password` from all of them. Leave nothing that could be re-imported.

---

## 3. What the new auth surface looks like

Six endpoints replace the old password pair. All live under `/api/auth/`. All are POST with JSON. None accept or return a password.

```
POST /api/auth/register             // start registration → SMS sent
POST /api/auth/register/verify      // confirm OTP → session_key issued
POST /api/auth/register/resend      // resend OTP for pending registration

POST /api/auth/login                // start login → SMS sent (enumeration-safe)
POST /api/auth/login/verify         // confirm OTP → session_key issued
POST /api/auth/login/resend         // resend OTP for pending login
```

Plus the existing session/profile endpoints (unchanged):

```
POST   /api/auth/logout
POST   /api/auth/logout-all
GET    /api/auth/me
PATCH  /api/auth/me/update          // first_name, last_name, language ONLY
POST   /api/auth/me/phone           // request phone change → OTP to NEW phone
POST   /api/auth/me/phone/verify    // confirm OTP → phone updated, all sessions killed
POST   /api/auth/me/delete
```

OTP code is **6 digits**, expires in **120 seconds**, **5 attempt limit** per code, and there is a **60-second cooldown** before the same phone can request a new code (enforced server-side, returns "Please wait before requesting another code").

Session lifetime is **720 hours (30 days)**. Bearer token in `Authorization: Bearer <session_key>`. 401 on any endpoint = wipe local session, redirect to `/auth/login`.

---

## 4. Endpoint contracts (authoritative)

All responses follow the standard envelope:
```json
{ "success": true,  "message": "...", "data": { ... } }
{ "success": false, "message": "..." }
```

Validation errors return `422` with `success: false`. Rate-limit errors return `429`. Auth errors return `401`. Generic client errors return `400`.

### 4.1 Register — start

```
POST /api/auth/register
Content-Type: application/json
```
Body:
```json
{
  "phone": "+998901234567",
  "first_name": "Aziza",
  "last_name": "Umarova",
  "language": "uz",
  "telegram_id": 123456789
}
```
Required: `phone`, `first_name`. Optional: `last_name` (default `""`), `language` (`"uz"` or `"ru"`, default `"uz"`), `telegram_id`.

Success `200`:
```json
{
  "success": true,
  "message": "Verification code sent",
  "data": {
    "message": "Verification code sent",
    "phone": "+998901234567",
    "verification_sent": true,
    "expires_in": 120
  }
}
```
On success, navigate to the OTP verify screen with `phone` carried in route state. Start a 60-second resend countdown.

Errors (`400`):
- `"Phone number already registered"` → suggest "Already a member? Log in"
- `"Telegram account already registered"` → only relevant when launched from a Telegram WebApp
- `"Invalid language. Must be one of: uz, ru"`

Errors (`422`):
- `"Missing required fields: phone, first_name"`

Errors (`429`):
- `"Rate limit exceeded"` — 3 register starts per 60s per IP. Show countdown using the `Retry-After` header if present.

### 4.2 Register — verify OTP

```
POST /api/auth/register/verify
```
Body:
```json
{
  "phone": "+998901234567",
  "code": "123456",
  "device": "iPhone 15"
}
```
Required: `phone`, `code`. Optional: `device` (free-form string, used for session display).

Success `201`:
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "session_key": "a1b2c3...",
    "user": {
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "phone": "+998901234567",
      "first_name": "Aziza",
      "last_name": "Umarova",
      "language": "uz",
      "is_phone_verified": true,
      "created_at": "2026-05-09T12:00:00+05:00"
    },
    "expires_at": "2026-06-08T12:00:00+05:00"
  }
}
```
On success: persist `session_key` + `expires_at` + `user` in secure storage, push to `/home`. If a referral code was held in app state from §2.3 of `FRONTEND_INTEGRATION.md`, fire `POST /api/referral/apply` after this — do **not** block navigation on it.

Errors (`400`):
- `"Invalid or expired verification code"` — wrong code, or 5+ failed attempts (server self-invalidates the code). Clear the input, surface inline message, do **not** auto-resend.
- `"Registration expired. Please register again."` — pending entry timed out (>120s). Push back to `/auth/register` with phone prefilled.
- `"Phone number already registered"` — race with another device finishing registration first.

Errors (`422`):
- `"phone and code are required"`

### 4.3 Register — resend

```
POST /api/auth/register/resend
```
Body:
```json
{ "phone": "+998901234567" }
```
Success `200`: `data.expires_in = 120`. Restart the 60s countdown.

Errors (`400`):
- `"No pending registration for this phone. Please register again."` → push back to `/auth/register`.
- `"Please wait before requesting another code"` (server-side cooldown) → keep countdown, do not retry.

Errors (`429`):
- 1 resend per 60s per IP.

### 4.4 Login — start

```
POST /api/auth/login
```
Body:
```json
{ "phone": "+998901234567" }
```
Success `200` (**always** the same response whether or not the phone is registered — this is enumeration-safe by design; do **not** branch on it):
```json
{
  "success": true,
  "message": "Verification code sent",
  "data": {
    "message": "If an account exists for this phone, a verification code has been sent",
    "phone": "+998901234567",
    "expires_in": 120
  }
}
```
Always navigate to `/auth/login/verify`. If the phone is unregistered, the user will fail at the verify step (no pending login in cache).

Errors:
- `422` `"phone is required"`
- `429` rate limit (3 / 60s).

### 4.5 Login — verify OTP

```
POST /api/auth/login/verify
```
Body:
```json
{
  "phone": "+998901234567",
  "code": "123456",
  "device": "iPhone 15"
}
```
Success `200`: same `{ session_key, user, expires_at }` shape as register/verify.

Errors (`400`):
- `"No pending login for this phone. Please request a code first."` — user opened verify directly or pending key expired. Push to `/auth/login`.
- `"Invalid or expired verification code"` — clear input, allow retry / resend.

Errors (`401`):
- `"No account found with this phone number"` — fired only after a valid OTP (rare: SMS arrived but no user exists). Push to `/auth/register` with phone prefilled.
- `"Account is deactivated"` — admin disabled the user. Surface message; no recovery flow in-app.

### 4.6 Login — resend

```
POST /api/auth/login/resend
```
Body: `{ "phone": "..." }`. Same error model as register/resend (`400` "No pending login..." / "Please wait...", `429` rate limit).

---

## 5. UI flows (replace the old password screens)

### 5.1 Login screen — phone only

Inputs:
- Phone, masked `+998 (__) ___ __ __`, validates `^\+998\d{9}$` (13 chars total).

Buttons:
- "Send code" — disabled until phone is valid; shows spinner while in-flight.
- "Don't have an account? Register" — link to `/auth/register`.

There is **no** password field on this screen. There is **no** "Forgot password" link. Recovery = log in again.

Submit → `POST /api/auth/login` → on any 200 navigate to `/auth/login/verify?phone=...`.

### 5.2 Register screen — name + phone

Inputs:
- First name (required, min 1 char trimmed).
- Last name (optional).
- Phone (validated as above).
- Language picker (optional — defaults to current app language).
- Optional collapsible "Have a referral code?" — text input held in app state, applied **after** registration via `POST /api/referral/apply`.

Buttons:
- "Send verification code".
- "Already have an account? Log in".

There is **no** password field. There is **no** confirm-password field.

Submit → `POST /api/auth/register` → navigate to `/auth/register/verify?phone=...`.

### 5.3 OTP verify screen (shared shape for register / login / phone change)

Inputs:
- 6 separated single-digit inputs. Auto-advance on type, auto-back on backspace, paste of a 6-digit string fills all six.
- `inputmode="numeric"`, `autocomplete="one-time-code"` so iOS/Android offer SMS autofill.

Behaviors:
- Resend countdown starting at 60s; "Resend code" link disabled until 0.
- "Use a different phone" link → back to the entry screen.
- On 6th digit, auto-submit verify.
- On `"Invalid or expired verification code"`: clear all six inputs, show inline error below the boxes, focus the first input.
- On `"Registration expired"` / `"No pending login..."`: bounce back to entry screen (with phone prefilled in register's case).

### 5.4 Phone change (authenticated)

Already specified in `FRONTEND_INTEGRATION.md §9.3–9.4`. Confirm the implementation:
- `POST /api/auth/me/phone` body is `{ "new_phone": "..." }` (note the field name — **not** `phone`).
- `POST /api/auth/me/phone/verify` body is `{ "code": "..." }` only — phone is inferred server-side from the pending entry keyed by `user_id`.
- After verify success, the server invalidates **all** sessions including the current one. Wipe local session, show "Phone updated. Please log in again.", route to `/auth/login` with the new phone prefilled.

### 5.5 Profile update

`PATCH /api/auth/me/update` accepts only:
```json
{ "first_name": "...", "last_name": "...", "language": "uz" }
```
Send only fields the user actually changed. The endpoint **silently ignores** any other key (including `password` and `phone`) — but you should not send them in the first place. Phone changes go through 5.4.

---

## 6. Error → UI mapping cheat sheet

| HTTP | message contains | UI behavior |
|---|---|---|
| 400 | `"Invalid or expired verification code"` | Clear OTP input, inline error, keep user on verify screen. Allow Resend. |
| 400 | `"Registration expired"` | Toast + redirect to `/auth/register` with phone prefilled. |
| 400 | `"No pending login"` | Toast + redirect to `/auth/login`. |
| 400 | `"No pending registration"` (on resend) | Redirect to `/auth/register`. |
| 400 | `"Phone number already registered"` (register) | Inline "Already a member? Log in" with link. |
| 400 | `"Telegram account already registered"` | Inline error; only reachable from Telegram WebApp. |
| 400 | `"Phone number already in use"` (phone change) | Inline error on the new-phone field. |
| 400 | `"New phone is the same as current"` | Inline error. |
| 400 | `"Please wait before requesting another code"` | Disable Resend, keep countdown running. |
| 401 | `"No account found with this phone number"` | Toast + redirect to `/auth/register` prefilled. |
| 401 | `"Account is deactivated"` | Full-screen blocking message. |
| 401 | `"Invalid or expired session"` (any endpoint) | Wipe session, redirect to `/auth/login`. |
| 422 | any | Field-level inline errors from `data.errors` if present, else toast `data.message`. |
| 429 | any | Inline error with countdown using `Retry-After` if header present, else 60s. |

Do **not** map `"Invalid credentials"` or `"User not found"` — those messages do not exist in the new flow.

---

## 7. Session lifecycle

- After register/verify or login/verify, the response carries `session_key` + `expires_at`. Persist both. Persist the user payload too — splash uses it to skip the `GET /api/auth/me` round-trip.
- On every request, set `Authorization: Bearer <session_key>`. No cookies, no CSRF token, no refresh-token dance — sessions are server-side and there is no refresh endpoint.
- On 401 from any endpoint: wipe local state, redirect to `/auth/login`, toast "Session expired, please log in again".
- "Logout" → `POST /api/auth/logout` (no body) → wipe local state.
- "Logout from all devices" → `POST /api/auth/logout-all` → wipe local state.
- "Delete account" → `POST /api/auth/me/delete` → wipe local state, return to onboarding.

There is no "remember me" toggle — sessions are always 30 days.

---

## 8. Splash / bootstrap (revisit)

```
1. Read session_key from secure storage.
2. If missing or past expires_at → onboarding/login.
3. Else GET /api/auth/me:
     200 → home
     401 → wipe, go to /auth/login
     network fail → retry once after 1s, then "Connection problem — retry".
```
Do **not** verify the session by calling any password-flavored endpoint — there are none.

---

## 9. Concrete migration checklist (per file)

For each existing frontend module touching auth, the agent should:

1. **Login form module**
   - Remove the password input + its validator + its state.
   - Submit body becomes `{ phone }`.
   - Replace post-success navigation: route to `/auth/login/verify` with `phone`, instead of straight to home.
   - Add a parallel "verify" screen if the app doesn't already have one for register.

2. **Register form module**
   - Remove `password`, `confirmPassword`, related validators, related "show/hide" state.
   - Submit body becomes `{ phone, first_name, last_name?, language?, telegram_id? }`.
   - Post-success navigation: `/auth/register/verify` with `phone`.

3. **OTP verify screen** (likely needs to be created)
   - 6-box code input, auto-advance, paste support, resend countdown, "Use a different phone" link.
   - Two callsites: `register/verify` and `login/verify`. Phone-change verify reuses the same component but submits `{ code }` only.

4. **Auth API client**
   - Drop helpers: `loginWithPassword`, `registerWithPassword`, `verifyPhone`, `resendCode`.
   - Add helpers: `startRegistration`, `verifyRegistration`, `resendRegistrationCode`, `startLogin`, `verifyLogin`, `resendLoginCode`, `requestPhoneChange`, `verifyPhoneChange`.

5. **Profile module**
   - Remove "Change password" row and its screen.
   - Profile update form sends only `first_name`, `last_name`, `language`.
   - Phone change kicks off the OTP flow described in §5.4.

6. **Routing**
   - Delete: `/auth/forgot-password`, `/auth/reset-password`, `/profile/change-password` (and their lazy-loaded chunks).
   - Add: `/auth/login/verify`, `/auth/register/verify`. (Profile phone change routes from `FRONTEND_INTEGRATION.md §9.3–9.4` already cover the third OTP flow.)

7. **Validation schemas** (zod / yup / formik / etc.)
   - Strip every `password*` field. Keep the phone regex (`^\+998\d{9}$`). Add `code` field with `^\d{6}$`.

8. **i18n strings**
   - Remove keys: `auth.password`, `auth.passwordPlaceholder`, `auth.passwordTooShort`, `auth.confirmPassword`, `auth.passwordsDoNotMatch`, `auth.forgotPassword`, `auth.changePassword`, `auth.invalidCredentials`, etc.
   - Add: `auth.codeSent`, `auth.codePlaceholder`, `auth.invalidCode`, `auth.codeExpired`, `auth.resendIn`, `auth.resend`, `auth.useDifferentPhone`, `auth.phoneAlreadyRegistered`, `auth.noAccountForPhone`.

9. **Tests / mocks**
   - Replace any `loginWithPassword` test fixture with the two-step OTP flow (mock `POST /api/auth/login` then `POST /api/auth/login/verify`).
   - Remove password-related test cases entirely; do not "skip" them.

10. **Analytics / events**
    - Rename `auth_login_submitted` to `auth_login_phone_submitted` and add `auth_login_otp_verified`.
    - Drop `auth_password_reset_*` events entirely.

---

## 10. Quick reference card (pin at top of agent context)

```
Client auth = OTP. No passwords. Anywhere. Ever.

Register flow:
  POST /api/auth/register          {phone, first_name, last_name?, language?, telegram_id?}
  POST /api/auth/register/verify   {phone, code, device?}        → {session_key, user, expires_at}
  POST /api/auth/register/resend   {phone}

Login flow:
  POST /api/auth/login             {phone}
  POST /api/auth/login/verify      {phone, code, device?}        → {session_key, user, expires_at}
  POST /api/auth/login/resend      {phone}

Phone change (authed):
  POST /api/auth/me/phone          {new_phone}
  POST /api/auth/me/phone/verify   {code}     // wipes all sessions on success

Profile:
  GET    /api/auth/me                                            // returns user
  PATCH  /api/auth/me/update       {first_name?, last_name?, language?}
  POST   /api/auth/logout                                         // current device
  POST   /api/auth/logout-all
  POST   /api/auth/me/delete

Auth header: Authorization: Bearer <session_key>
Session TTL: 720h (30d). 401 = wipe + /auth/login.
OTP: 6 digits, 120s expiry, 5 attempts, 60s resend cooldown.
```
