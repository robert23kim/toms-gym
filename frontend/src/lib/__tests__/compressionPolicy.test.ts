import { shouldCompress, COMPRESS_MAX_BYTES } from "../compressionPolicy";

const MB = 1024 * 1024;

const IPHONE_UA =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";
const IPAD_UA =
  "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1";
// iPadOS 13+ reports a desktop-Mac UA; only maxTouchPoints betrays it.
const IPADOS_DESKTOP_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15";
const MAC_SAFARI_UA = IPADOS_DESKTOP_UA; // same string; distinguished by touch points
const ANDROID_UA =
  "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36";
const DESKTOP_CHROME_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

describe("shouldCompress", () => {
  test("skips compression on iPhone (WebKit memory budget)", () => {
    const d = shouldCompress(50 * MB, IPHONE_UA, 5);
    expect(d.compress).toBe(false);
    expect(d.reason).toBe("ios-webkit");
  });

  test("skips compression on iPad", () => {
    const d = shouldCompress(50 * MB, IPAD_UA, 5);
    expect(d.compress).toBe(false);
    expect(d.reason).toBe("ios-webkit");
  });

  test("skips compression on iPadOS masquerading as desktop Mac (touch points)", () => {
    const d = shouldCompress(50 * MB, IPADOS_DESKTOP_UA, 5);
    expect(d.compress).toBe(false);
    expect(d.reason).toBe("ios-webkit");
  });

  test("allows compression on a real desktop Mac (no touch points)", () => {
    const d = shouldCompress(50 * MB, MAC_SAFARI_UA, 0);
    expect(d.compress).toBe(true);
    expect(d.reason).toBe("ok");
  });

  test("skips compression above the size cap on any platform", () => {
    const d = shouldCompress(COMPRESS_MAX_BYTES + 1, DESKTOP_CHROME_UA, 0);
    expect(d.compress).toBe(false);
    expect(d.reason).toBe("file-too-large");
  });

  test("allows compression at exactly the size cap", () => {
    const d = shouldCompress(COMPRESS_MAX_BYTES, ANDROID_UA, 5);
    expect(d.compress).toBe(true);
    expect(d.reason).toBe("ok");
  });

  test("allows compression on Android under the cap", () => {
    const d = shouldCompress(120 * MB, ANDROID_UA, 5);
    expect(d.compress).toBe(true);
    expect(d.reason).toBe("ok");
  });

  test("iOS check wins over the size cap in the reported reason", () => {
    const d = shouldCompress(COMPRESS_MAX_BYTES + 1, IPHONE_UA, 5);
    expect(d.compress).toBe(false);
    expect(d.reason).toBe("ios-webkit");
  });
});
