export type TabKey = "home" | "lift" | "bowl" | "golf" | "champions" | "me";

const PREFIXES: [TabKey, string[]][] = [
  ["lift", ["/lift", "/upload", "/challenges", "/video-player"]],
  ["champions", ["/champions"]],
  ["bowl", ["/bowl", "/bowling"]],
  ["golf", ["/golf"]],
  ["me", ["/profile", "/find-profile", "/signin", "/auth"]],
];

export const activeTab = (pathname: string): TabKey | null => {
  if (pathname === "/") return "home";
  for (const [key, prefixes] of PREFIXES) {
    if (prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return key;
  }
  return null;
};

export const meTarget = (userId: string | null): string =>
  userId ? `/profile/${userId}` : "/find-profile";
