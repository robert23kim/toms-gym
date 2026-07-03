import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import axios from "axios";
import { useGolfLeaderboard, apiErrorMessage } from "../queries";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do (see src/test-password.test.ts).
jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  // `import axios from "axios"` compiles to `axios.default` here (no
  // esModuleInterop), so the mock must expose `.default` too.
  const mocked = { ...actual, get: jest.fn(), isAxiosError: actual.isAxiosError };
  return { ...mocked, default: mocked };
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider
    client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
  >
    {children}
  </QueryClientProvider>
);

describe("useGolfLeaderboard", () => {
  it("returns leaderboard entries", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: {
        leaderboard: [
          {
            user_id: "u1",
            user_name: "Tom",
            rank: 1,
            handicap_index: 12.3,
            rounds_played: 4,
            best_differential: 10.1,
          },
        ],
      },
    });
    const { result } = renderHook(() => useGolfLeaderboard(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].user_name).toBe("Tom");
    expect((axios.get as jest.Mock).mock.calls[0][0]).toContain(
      "/golf/leaderboard?limit=50"
    );
  });

  it("surfaces request errors", async () => {
    (axios.get as jest.Mock).mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useGolfLeaderboard(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("apiErrorMessage", () => {
  it("unwraps Error messages", () => {
    expect(apiErrorMessage(new Error("boom"), "fallback")).toBe("boom");
  });

  it("falls back for unknown values", () => {
    expect(apiErrorMessage("weird", "fallback")).toBe("fallback");
  });
});
