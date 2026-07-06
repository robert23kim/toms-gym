import axios from "axios";
import { API_URL } from "../config";

// Shared ShortLink creation used by the Share buttons on lift / bowling / golf
// results (T13). The returned URL points at the BACKEND origin `/s/<code>` so
// that link crawlers (Slack, Facebook, …) reach the server-side OG meta route
// and the pasted link unfurls with a card. Human browsers hitting that URL are
// 302-redirected by the backend to the frontend result page.

export interface ShareMeta {
  /** The frontend result page URL a human should land on. */
  targetUrl: string;
  /** OG card title (e.g. "Tom's Squat"). */
  ogTitle?: string;
  /** OG card + unfurl description (e.g. "3 reps · 225 lbs"). */
  ogDescription?: string;
  /** Big punch stat/grade rendered on the card (e.g. "A", "82", "Pocket"). */
  ogStat?: string;
  /** Optional source still image URL (reserved; card is template-rendered). */
  ogImageSource?: string;
}

export async function createShareLink(meta: ShareMeta): Promise<string> {
  const res = await axios.post(`${API_URL}/short-link`, {
    target_url: meta.targetUrl,
    og_title: meta.ogTitle,
    og_description: meta.ogDescription,
    og_stat: meta.ogStat,
    og_image_source: meta.ogImageSource,
  });
  return `${API_URL}/s/${res.data.short_code}`;
}

/**
 * Create a share short link and copy it to the clipboard. Returns the URL on
 * success. Throws on network/clipboard failure so callers can surface a toast.
 */
export async function createAndCopyShareLink(meta: ShareMeta): Promise<string> {
  const shortUrl = await createShareLink(meta);
  await navigator.clipboard.writeText(shortUrl);
  return shortUrl;
}
