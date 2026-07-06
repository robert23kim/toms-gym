import React, { useState } from "react";
import { Mail, Send } from "lucide-react";
import axios from "axios";
import { API_URL } from "../config";

/**
 * Request a magic sign-in link (T15). Minimal entry point to the passwordless
 * recovery flow: enter your email, get a one-time link. The backend never
 * reveals whether the email exists, so the success copy is deliberately
 * generic ("if an account exists…").
 */
const SignIn: React.FC = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError("Please enter your email address");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await axios.post(`${API_URL}/auth/magic-link`, { email });
      setSent(true);
    } catch {
      // The endpoint returns 200 for real emails; a network/500 lands here.
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-md w-full p-6 bg-background border border-border rounded-xl shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Mail className="w-5 h-5 text-primary" />
          </div>
          <h1 className="text-xl font-semibold">Sign in by email</h1>
        </div>

        {sent ? (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded">
            <p className="font-medium mb-1">Check your inbox</p>
            <p className="text-sm">
              If an account exists for that email, we've sent a one-time sign-in
              link. It works once and expires in 15 minutes.
            </p>
          </div>
        ) : (
          <>
            <p className="text-muted-foreground mb-4">
              No password needed. Enter your email and we'll send you a one-time
              link to get back into your profile on this device.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError(null);
                  }}
                  placeholder="your@email.com"
                  className="w-full px-3 py-2 rounded-md border border-border bg-background"
                  autoFocus
                />
              </div>

              {error && (
                <div className="bg-red-100 text-red-700 p-3 rounded text-sm">{error}</div>
              )}

              <button
                type="submit"
                disabled={loading || !email}
                className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  "Sending…"
                ) : (
                  <>
                    <Send size={18} />
                    Email me a sign-in link
                  </>
                )}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};

export default SignIn;
