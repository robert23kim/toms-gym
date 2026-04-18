import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Trophy, Upload } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import FairwayScope from "../components/FairwayScope";
import { API_URL } from "../config";
import { getGhibliAvatar } from "../lib/api";
import { GolfLeaderboardEntry } from "../lib/types";

const GolfLeaderboard: React.FC = () => {
  const [entries, setEntries] = useState<GolfLeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        setLoading(true);
        const response = await axios.get(
          `${API_URL}/golf/leaderboard?limit=50`
        );
        setEntries(response.data.leaderboard || []);
      } catch (err: any) {
        console.error("Error fetching golf leaderboard:", err);
        setError(
          err.response?.data?.error ||
            err.message ||
            "Failed to load leaderboard"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, []);

  if (loading) {
    return (
      <Layout>
        <FairwayScope>
          <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--fw-info)]"></div>
              </div>
            </div>
          </div>
        </FairwayScope>
      </Layout>
    );
  }

  return (
    <Layout>
      <FairwayScope>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
        >
          <div className="max-w-3xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="fw-h1">Handicap leaderboard</h1>
                <p className="fw-text-secondary text-sm">Lowest handicap index first.</p>
              </div>
              <Link
                to="/golf/upload"
                className="h-9 px-4 rounded-md bg-[var(--fw-info)] text-white text-sm inline-flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Log round
              </Link>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500 mb-6">
                {error}
              </div>
            )}

            {entries.length === 0 ? (
              <div className="fw-surface p-12 text-center">
                <Trophy className="w-12 h-12 fw-text-secondary mx-auto mb-4" />
                <h2 className="text-xl font-semibold mb-2">No handicaps yet</h2>
                <p className="fw-text-secondary mb-6">
                  Be the first to establish a handicap. Upload 3 or more rounds to
                  get your handicap index.
                </p>
                <Link
                  to="/golf/upload"
                  className="h-9 px-6 rounded-md bg-[var(--fw-info)] text-white text-sm inline-flex items-center gap-2"
                >
                  <Upload className="w-4 h-4" />
                  Upload Scorecard
                </Link>
              </div>
            ) : (
              <div data-testid="leaderboard-list" className="fw-surface overflow-hidden">
                {entries.map((entry, index) => (
                  <Link
                    key={entry.user_id}
                    to={`/golf/profile/${entry.user_id}`}
                    className={`flex items-center gap-4 p-3 hover:bg-[var(--fw-bg-secondary)] transition-colors ${
                      index !== entries.length - 1
                        ? "border-b-[0.5px] border-[var(--fw-border-tertiary)]"
                        : ""
                    }`}
                  >
                    <div className="w-6 text-center font-medium text-sm fw-text-secondary">
                      {entry.rank}
                    </div>
                    <img
                      src={getGhibliAvatar(entry.user_id)}
                      alt={entry.user_name}
                      className="w-10 h-10 rounded-full bg-[var(--fw-bg-secondary)]"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{entry.user_name}</div>
                      <div className="text-xs fw-text-secondary">
                        {entry.rounds_played} round{entry.rounds_played !== 1 ? "s" : ""}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-medium text-[var(--fw-text-success)]">
                        {entry.handicap_index.toFixed(1)}
                      </div>
                      <div className="text-xs fw-text-secondary">
                        Best {entry.best_differential !== null ? entry.best_differential.toFixed(1) : "—"}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}

            {/* Quick links */}
            <div className="mt-8 flex justify-center gap-4">
              {localStorage.getItem("userId") && (
                <Link
                  to={`/golf/profile/${localStorage.getItem("userId")}`}
                  className="text-sm text-[var(--fw-text-info)] hover:underline"
                >
                  My Golf Profile
                </Link>
              )}
            </div>
          </div>
        </motion.div>
      </FairwayScope>
    </Layout>
  );
};

export default GolfLeaderboard;
