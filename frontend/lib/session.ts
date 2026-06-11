import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const SESSION_COOKIE = "zen_compta_session";
const SESSION_DURATION_MS = 7 * 24 * 60 * 60 * 1000;

function requiredEnv(name: string) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

export function appPassword() {
  return requiredEnv("ZEN_COMPTA_APP_PASSWORD");
}

export function sessionSecret() {
  return requiredEnv("ZEN_COMPTA_SESSION_SECRET");
}

export function internalApiToken() {
  return requiredEnv("INTERNAL_API_TOKEN");
}

const encoder = new TextEncoder();

async function signingKey() {
  return crypto.subtle.importKey(
    "raw",
    encoder.encode(sessionSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

function signaturePayload(expiresAt: number) {
  return encoder.encode(`zen-compta:${expiresAt}`);
}

function toHex(buffer: ArrayBuffer) {
  return Array.from(new Uint8Array(buffer))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function fromHex(value: string) {
  if (value.length === 0 || value.length % 2 !== 0 || /[^0-9a-f]/.test(value)) {
    return null;
  }
  const bytes = new Uint8Array(value.length / 2);
  for (let index = 0; index < bytes.length; index += 1) {
    bytes[index] = Number.parseInt(value.slice(index * 2, index * 2 + 2), 16);
  }
  return bytes;
}

export async function isAuthenticated() {
  const cookieStore = await cookies();
  const value = cookieStore.get(SESSION_COOKIE)?.value;
  if (!value) {
    return false;
  }

  const [expiresAtRaw, signatureHex, extra] = value.split(".");
  if (!expiresAtRaw || !signatureHex || extra !== undefined) {
    return false;
  }

  const expiresAt = Number(expiresAtRaw);
  if (!Number.isInteger(expiresAt) || expiresAt <= Date.now()) {
    return false;
  }

  const signature = fromHex(signatureHex);
  if (!signature) {
    return false;
  }

  const key = await signingKey();
  return crypto.subtle.verify(
    "HMAC",
    key,
    signature,
    signaturePayload(expiresAt),
  );
}

export async function requireAuth() {
  if (!(await isAuthenticated())) {
    redirect("/login");
  }
}

export async function createSession() {
  const expiresAt = Date.now() + SESSION_DURATION_MS;
  const key = await signingKey();
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    signaturePayload(expiresAt),
  );

  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE, `${expiresAt}.${toHex(signature)}`, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: Math.floor(SESSION_DURATION_MS / 1000),
  });
}

export async function clearSession() {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE);
}
