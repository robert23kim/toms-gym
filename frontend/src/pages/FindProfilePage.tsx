import React, { useState } from "react";
import { motion } from "framer-motion";
import { Search, User } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";

/**
 * T14 — full-page "Who am I?" recovery surface. Reuses the same email lookup
 * as the FindProfile dialog (GET /users/by-email/:email), but reachable via a
 * dedicated route so a user who lost their localStorage session has a page to
 * land on, not just a modal.
 */
const FindProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

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
        navigate(`/profile/${response.data.id}`);
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
      </motion.div>
    </Layout>
  );
};

export default FindProfilePage;
