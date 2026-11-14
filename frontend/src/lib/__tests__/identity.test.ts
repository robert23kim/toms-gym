const mockIsNative = jest.fn(() => false);
const mockPrefs = new Map<string, string>();
const mockPrefGet = jest.fn(async ({ key }: { key: string }) => ({ value: mockPrefs.get(key) ?? null }));
const mockPrefSet = jest.fn(async ({ key, value }: { key: string; value: string }) => {
  mockPrefs.set(key, value);
});
const mockPrefRemove = jest.fn(async ({ key }: { key: string }) => {
  mockPrefs.delete(key);
});

jest.mock("@capacitor/core", () => ({ Capacitor: { isNativePlatform: () => mockIsNative() } }));
jest.mock("@capacitor/preferences", () => ({
  Preferences: { get: mockPrefGet, set: mockPrefSet, remove: mockPrefRemove },
}));

import { forget, getEmail, getUserId, remember, restoreIdentity } from "../identity";

const store = new Map<string, string>();
const ls = window.localStorage as unknown as {
  getItem: jest.Mock;
  setItem: jest.Mock;
  removeItem: jest.Mock;
};

beforeEach(() => {
  store.clear();
  mockPrefs.clear();
  jest.clearAllMocks();
  mockIsNative.mockReturnValue(false);
  ls.getItem.mockImplementation((k: string) => store.get(k) ?? null);
  ls.setItem.mockImplementation((k: string, v: string) => {
    store.set(k, String(v));
  });
  ls.removeItem.mockImplementation((k: string) => {
    store.delete(k);
  });
});

describe("identity on the web", () => {
  test("reads the same localStorage key the app always used", () => {
    store.set("userId", "u-1");
    expect(getUserId()).toBe("u-1");
  });

  test("treats the stringified empties as no user", () => {
    store.set("userId", "undefined");
    expect(getUserId()).toBeNull();
    store.set("userId", "null");
    expect(getUserId()).toBeNull();
  });

  test("remember stores the id and the email; forget clears both", async () => {
    remember({ userId: "u-2", email: "a@example.com" });
    expect(store.get("userId")).toBe("u-2");
    expect(getEmail()).toBe("a@example.com");
    await forget();
    expect(getUserId()).toBeNull();
    expect(getEmail()).toBeNull();
  });

  test("remember with only an email keeps the stored id", () => {
    store.set("userId", "u-3");
    remember({ email: "b@example.com" });
    expect(getUserId()).toBe("u-3");
    expect(getEmail()).toBe("b@example.com");
  });

  test("getEmail ignores anything that is not an email", () => {
    store.set("userEmail", "u-1");
    expect(getEmail()).toBeNull();
  });

  test("never touches the native plugin on the web", async () => {
    remember({ userId: "u-4", email: "c@example.com" });
    await forget();
    await restoreIdentity();
    expect(mockPrefGet).not.toHaveBeenCalled();
    expect(mockPrefSet).not.toHaveBeenCalled();
    expect(mockPrefRemove).not.toHaveBeenCalled();
  });

  test("storage that throws reads as no user instead of crashing", () => {
    ls.getItem.mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(getUserId()).toBeNull();
    expect(getEmail()).toBeNull();
  });
});

describe("identity in the APK", () => {
  beforeEach(() => mockIsNative.mockReturnValue(true));

  test("remember writes through to Preferences", async () => {
    remember({ userId: "u-5", email: "d@example.com" });
    await Promise.resolve();
    await new Promise((r) => setTimeout(r, 0));
    expect(mockPrefs.get("userId")).toBe("u-5");
    expect(mockPrefs.get("userEmail")).toBe("d@example.com");
  });

  test("restore fills an empty localStorage from Preferences", async () => {
    mockPrefs.set("userId", "u-6");
    mockPrefs.set("userEmail", "e@example.com");
    await restoreIdentity();
    expect(getUserId()).toBe("u-6");
    expect(getEmail()).toBe("e@example.com");
  });

  test("restore never replaces an id already in localStorage", async () => {
    store.set("userId", "u-web");
    mockPrefs.set("userId", "u-native");
    await restoreIdentity();
    expect(getUserId()).toBe("u-web");
  });

  test("boot seeds Preferences for an athlete the WebView already knows", async () => {
    store.set("userId", "u-old");
    store.set("userEmail", "old@example.com");
    await restoreIdentity();
    expect(mockPrefs.get("userId")).toBe("u-old");
    expect(mockPrefs.get("userEmail")).toBe("old@example.com");
  });

  test("forget clears the native mirror before it resolves", async () => {
    mockPrefs.set("userId", "u-7");
    mockPrefs.set("userEmail", "f@example.com");
    store.set("userId", "u-7");
    await forget();
    expect(mockPrefs.has("userId")).toBe(false);
    expect(mockPrefs.has("userEmail")).toBe(false);
    await restoreIdentity();
    expect(getUserId()).toBeNull();
  });

  test("a failing plugin never blocks the restore", async () => {
    mockPrefGet.mockImplementationOnce(async () => {
      throw new Error("plugin missing");
    });
    await expect(restoreIdentity()).resolves.toBeUndefined();
    expect(getUserId()).toBeNull();
  });
});
