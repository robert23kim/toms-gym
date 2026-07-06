import React, { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { API_URL } from "../config";
import { setTokens } from "../auth/tokenUtils";

/**
 * Magic-link consume page (T15). Opening the emailed link lands here; we call
 * GET /auth/magic/:token, restore the localStorage session, and redirect to
 * the profile. The link is single-use and expires server-side, so a dead link
 * simply shows an error with a way to request a new one.
 */
const MagicLink: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [error, setError] = useState<string | null>(null);
  const ranRef = useRef(false);

  useEffect(() => {
    // Guard against React StrictMode double-invoke — the token is single-use,
    // so a second call would always fail. Only the first attempt counts.
    if (ranRef.current) return;
    ranRef.current = true;

    const run = async () => {
      if (!token) {
        setError("This sign-in link is invalid.");
        return;
      }
      try {
        const res = await axios.get(`${API_URL}/auth/magic/${encodeURIComponent(token)}`);
        const { user_id, access_token } = res.data || {};
        if (!user_id) {
          setError("This sign-in link is invalid or has expired.");
          return;
        }

        if (access_token) {
          // Account has real auth — store a full session (JWT + userId).
          setTokens(access_token, "", user_id);
        } else {
          // Passwordless account — just restore the userId.
          localStorage.setItem("userId", user_id);
        }

        // Full reload so AuthContext re-reads localStorage on mount.
        window.location.href = `/profile/${user_id}`;
      } catch {
        setError("This sign-in link is invalid or has expired.");
      }
    };

    run();
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      {error ? (
        <div className="max-w-md w-full text-center p-6 bg-background border border-border rounded-xl shadow-sm">
          <h1 className="text-xl font-semibold mb-2">Sign-in link expired</h1>
          <p className="text-muted-foreground mb-6">{error}</p>
          <a
            href="/signin"
            className="inline-flex px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Request a new link
          </a>
        </div>
      ) : (
        <div className="flex flex-col items-center">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="mt-4 text-lg">Signing you in…</p>
        </div>
      )}
    </div>
  );
};

export default MagicLink;
