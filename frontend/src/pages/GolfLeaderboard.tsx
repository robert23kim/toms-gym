import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Trophy, Upload } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
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

  const getRankColor = (rank: number) => {
    if (rank === 1) return "text-yellow-500";
    if (rank === 2) return "text-gray-400";
    if (rank === 3) return "text-amber-600";
    return "text-muted-foreground";
  };

  const getRankBg = (rank: number) => {
    if (rank === 1) return "bg-yellow-500/10";
    if (rank === 2) return "bg-gray-400/10";
    if (rank === 3) return "bg-amber-600/10";
    return "";
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <Trophy className="w-6 h-6 text-green-500" />
              </div>
              <h1 className="text-2xl font-bold">Golf Handicap Leaderboard</h1>
            </div>
            <Link
              to="/golf/upload"
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 text-sm"
            >
              <Upload className="w-4 h-4" />
              Upload Round
            </Link>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500 mb-6">
              {error}
            </div>
          )}

          {entries.length === 0 ? (
            <div className="bg-card rounded-lg border border-input p-12 text-center">
              <Trophy className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">No handicaps yet</h2>
              <p className="text-muted-foreground mb-6">
                Be the first to establish a handicap! Upload 3 or more rounds to
                get your handicap index.
              </p>
              <Link
                to="/golf/upload"
                className="inline-flex items-center gap-2 bg-primary text-primary-foreground py-2 px-6 rounded-lg hover:bg-primary/90"
              >
                <Upload className="w-4 h-4" />
                Upload Scorecard
              </Link>
            </div>
          ) : (
            <div className="bg-card rounded-lg border border-input overflow-hidden">
              {entries.map((entry, index) => (
                <Link
                  key={entry.user_id}
                  to={`/golf/profile/${entry.user_id}`}
                  className={`flex items-center gap-4 p-4 hover:bg-muted/50 transition-colors ${
                    index !== entries.length - 1
                      ? "border-b border-input"
                      : ""
                  } ${getRankBg(entry.rank)}`}
                >
                  {/* Rank */}
                  <div
                    className={`w-8 text-center font-bold text-lg ${getRankColor(
                      entry.rank
                    )}`}
                  >
                    {entry.rank}
                  </div>

                  {/* Avatar */}
                  <img
                    src={getGhibliAvatar(entry.user_id)}
                    alt={entry.user_name}
                    className="w-10 h-10 rounded-full bg-muted"
                  />

                  {/* Name + rounds */}
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold truncate">
                      {entry.user_name}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {entry.rounds_played} round
                      {entry.rounds_played !== 1 ? "s" : ""}
                    </div>
                  </div>

                  {/* Handicap */}
                  <div className="text-right">
                    <div className="text-xl font-bold text-green-500">
                      {entry.handicap_index.toFixed(1)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Best: {entry.best_differential !== null ? entry.best_differential.toFixed(1) : 'N/A'}
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
                className="text-sm text-primary hover:underline"
              >
                My Golf Profile
              </Link>
            )}
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default GolfLeaderboard;
