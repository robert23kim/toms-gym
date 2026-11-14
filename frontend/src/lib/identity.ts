import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";

const USER_ID_KEY = "userId";
const EMAIL_KEY = "userEmail";
const RESTORE_TIMEOUT_MS = 1500;

const read = (key: string): string | null => {
  try {
    if (typeof localStorage === "undefined") return null;
    const v = localStorage.getItem(key);
    return v && v !== "undefined" && v !== "null" ? v : null;
  } catch {
    return null;
  }
};

const write = (key: string, value: string) => {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage full or blocked: the caller's action still stands.
  }
};

const drop = (key: string) => {
  try {
    localStorage.removeItem(key);
  } catch {
    // Nothing stored to drop.
  }
};

const isNative = (): boolean => {
  try {
    return Capacitor.isNativePlatform();
  } catch {
    return false;
  }
};

export const getUserId = (): string | null => read(USER_ID_KEY);

export const getEmail = (): string | null => {
  const v = read(EMAIL_KEY);
  return v && v.includes("@") ? v : null;
};

export interface Identity {
  userId?: string | number | null;
  email?: string | null;
}

/** Stores whatever part of the identity is known; mirrors it to native Preferences in the APK. */
export const remember = ({ userId, email }: Identity): void => {
  const id = userId != null && userId !== "" ? String(userId) : null;
  const mail = email && email.includes("@") ? email.trim() : null;
  if (id) write(USER_ID_KEY, id);
  if (mail) write(EMAIL_KEY, mail);
  if (!isNative()) return;
  if (id) Preferences.set({ key: USER_ID_KEY, value: id }).catch(() => {});
  if (mail) Preferences.set({ key: EMAIL_KEY, value: mail }).catch(() => {});
};

/** Clears identity everywhere; await it before reloading or the APK restores it on boot. */
export const forget = async (): Promise<void> => {
  drop(USER_ID_KEY);
  drop(EMAIL_KEY);
  if (!isNative()) return;
  await Promise.all([
    Preferences.remove({ key: USER_ID_KEY }).catch(() => {}),
    Preferences.remove({ key: EMAIL_KEY }).catch(() => {}),
  ]);
};

/** APK boot: refills an emptied WebView localStorage from Preferences. Never rejects. */
export const restoreIdentity = async (): Promise<void> => {
  if (!isNative() || getUserId()) return;
  const restore = async () => {
    const [id, mail] = await Promise.all([
      Preferences.get({ key: USER_ID_KEY }),
      Preferences.get({ key: EMAIL_KEY }),
    ]);
    if (getUserId()) return;
    if (id.value) write(USER_ID_KEY, id.value);
    if (mail.value && !getEmail()) write(EMAIL_KEY, mail.value);
  };
  try {
    await Promise.race([restore(), new Promise<void>((r) => setTimeout(r, RESTORE_TIMEOUT_MS))]);
  } catch {
    // Plugin missing or failing: boot as a new visitor.
  }
};
