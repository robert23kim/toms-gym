// react-query hooks for server data. New pages should fetch through hooks in
// this module instead of ad-hoc axios calls inside useEffect.
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { API_URL } from "../config";
import { GolfLeaderboardEntry } from "./types";

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as { error?: string } | undefined;
    return body?.error ?? error.message;
  }
  return error instanceof Error ? error.message : fallback;
}

export function useGolfLeaderboard(limit = 50) {
  return useQuery({
    queryKey: ["golf", "leaderboard", limit],
    queryFn: async (): Promise<GolfLeaderboardEntry[]> => {
      const res = await axios.get(`${API_URL}/golf/leaderboard?limit=${limit}`);
      return res.data.leaderboard ?? [];
    },
    staleTime: 30_000,
  });
}
