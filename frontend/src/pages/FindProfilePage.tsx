import React, { useState } from "react";
import { motion } from "framer-motion";
import { Search, User } from "lucide-react";
import { Link } from "react-router-dom";
import axios from "axios";
import Layout from "../components/Layout";
import GhibliAvatar from "../components/GhibliAvatar";
import { API_URL } from "../config";
import { LastLift, lastLiftCopy, sinceCopy } from "../lib/welcome";

interface Found {
  id: string;
  name: string | null;
  lastLift: LastLift | null;
}

/**
 * T14 — full-page "Who am I?" recovery surface. Reuses the same email lookup
 * as the FindProfile dialog (GET /users/by-email/:email), but reachable via a
 * dedicated route so a user who lost their localStorage session has a page to
 * land on, not just a modal.
 */
const FindProfilePage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [found, setFound] = useState<Found | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      setError("Please enter your email address");
      return;
    }

    setLoading(true);
    setError(null);
    setNotFound(false);

    try {
      const response = await axios.get(
        `${API_URL}/users/by-email/${encodeURIComponent(email)}`,
      );

      if (response.data && response.data.id) {
        localStorage.setItem("userId", response.data.id);
        const lastLift: LastLift | null = await axios
          .get(`${API_URL}/users/${response.data.id}/lifts?limit=1`)
          .then((r) => r.data?.lifts?.[0] ?? null)
          .catch(() => null);
        setFound({ id: response.data.id, name: response.data.name ?? null, lastLift });
      }
    } catch (err) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr.response?.status === 404) {
        setNotFound(true);
      } else {
        setError("Failed to look up profile. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-md mx-auto py-12"
      >
        {found ? (
          <section aria-label="Welcome back" className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <GhibliAvatar id={found.id} name={found.name || "you"} size="lg" />
              <div className="min-w-0">
                <h1 className="text-2xl font-semibold">
                  Welcome back{found.name ? `, ${found.name.split(/\s+/)[0]}` : ""}
                </h1>
                {found.lastLift ? (
                  <p className="text-sm text-muted-foreground mt-1">
                    {["Last lift", sinceCopy(found.lastLift.created_at)].filter(Boolean).join(" · ")}
                    <br />
                    {lastLiftCopy(found.lastLift)}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground mt-1">Your profile is ready.</p>
                )}
              </div>
            </div>
            <div className="mt-5 flex flex-col gap-2">
              <Link
                to={`/profile/${found.id}`}
                className="w-full text-center px-4 py-2.5 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90"
              >
                Open my profile
              </Link>
              <Link
                to="/lift/upload"
                className="w-full text-center px-4 py-2.5 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
              >
                Upload a new lift →
              </Link>
            </div>
          </section>
        ) : (
        <>
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Search className="w-5 h-5 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold">Who am I?</h1>
        </div>

        <p className="text-muted-foreground mb-6">
          Lost your session? Enter the email address you used when uploading a
          lift, bowl, or round and we'll take you straight to your profile — no
          password needed.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setError(null);
                setNotFound(false);
              }}
              placeholder="your@email.com"
              className="w-full px-3 py-2 rounded-md border border-border bg-background"
              autoFocus
            />
          </div>

          {error && (
            <div className="bg-red-100 text-red-700 p-3 rounded text-sm">{error}</div>
          )}

          {notFound && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded">
              <p className="font-medium mb-2">No profile found with that email</p>
              <p className="text-sm mb-3">
                Upload something and your profile is created automatically — no
                signup required.
              </p>
              <Link
                to="/upload"
                className="inline-block px-3 py-2 bg-primary text-primary-foreground rounded text-sm hover:bg-primary/90"
              >
                Upload something
              </Link>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !email}
            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              "Searching..."
            ) : (
              <>
                <User size={18} />
                Find my profile
              </>
            )}
          </button>
        </form>
        </>
        )}

        <p className="text-sm text-muted-foreground text-center mt-6">
          On a new device?{" "}
          <Link to="/signin" className="text-primary hover:underline">
            Email me a sign-in link
          </Link>{" "}
          instead.
        </p>
      </motion.div>
    </Layout>
  );
};

export default FindProfilePage;
