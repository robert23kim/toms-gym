import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Upload, ChevronDown, ChevronUp, Calendar, MapPin } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { getGhibliAvatar } from "../lib/api";
import { GolfRound, GolfHoleScore } from "../lib/types";

const GolfProfile: React.FC = () => {
  const { userId: paramUserId } = useParams<{ userId: string }>();
  const userId = paramUserId || localStorage.getItem("userId") || "";
  const [rounds, setRounds] = useState<GolfRound[]>([]);
  const [handicapIndex, setHandicapIndex] = useState<number | null>(null);
  const [userName, setUserName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRound, setExpandedRound] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setError("No user ID found. Please upload a round first.");
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        const [roundsRes, profileRes] = await Promise.all([
          axios.get(`${API_URL}/golf/rounds?user_id=${userId}`),
          axios.get(`${API_URL}/users/${userId}/profile`).catch(() => null),
        ]);

        setRounds(roundsRes.data.rounds || []);
        setHandicapIndex(roundsRes.data.handicap_index ?? null);

        if (profileRes?.data) {
          setUserName(profileRes.data.name || profileRes.data.email || "Golfer");
        }
      } catch (err: any) {
        console.error("Error fetching golf profile:", err);
        setError(
          err.response?.data?.error || err.message || "Failed to load profile"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId]);

  const getHoleBgClass = (hole: GolfHoleScore) => {
    if (hole.strokes === null) return "border-input";
    const diff = hole.strokes - hole.par;
    if (diff <= -1) return "bg-green-500/20 border-green-500/50";
    if (diff === 0) return "bg-card border-input";
    if (diff === 1) return "bg-yellow-500/20 border-yellow-500/50";
    return "bg-red-500/20 border-red-500/50";
  };

  const getRoundStats = (round: GolfRound) => {
    const holes = round.holes || [];
    const birdies = holes.filter((h) => h.strokes !== null && h.strokes < h.par).length;
    const bogeys = holes.filter((h) => h.strokes !== null && h.strokes === h.par + 1).length;
    const doubles = holes.filter((h) => h.strokes !== null && h.strokes >= h.par + 2).length;
    return { birdies, bogeys, doubles };
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

  if (error) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500 mb-4">
              {error}
            </div>
            <Link
              to="/golf/upload"
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90"
            >
              <Upload className="w-4 h-4" />
              Upload a Round
            </Link>
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
          <Link
            to="/golf/leaderboard"
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Leaderboard
          </Link>

          {/* Profile Header */}
          <div className="text-center mb-8">
            <img
              src={getGhibliAvatar(userId)}
              alt="Avatar"
              className="w-20 h-20 rounded-full mx-auto mb-3 bg-card border-2 border-input"
            />
            <h1 className="text-2xl font-bold">{userName || "Golfer"}</h1>

            {/* Handicap badge */}
            <div className="mt-4">
              {handicapIndex !== null ? (
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-green-500/20 border-2 border-green-500/50"
                >
                  <div>
                    <div className="text-3xl font-bold text-green-500">
                      {handicapIndex.toFixed(1)}
                    </div>
                    <div className="text-xs text-green-400">Handicap</div>
                  </div>
                </motion.div>
              ) : (
                <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-muted border-2 border-input">
                  <div>
                    <div className="text-2xl font-bold text-muted-foreground">N/A</div>
                    <div className="text-xs text-muted-foreground">Handicap</div>
                  </div>
                </div>
              )}
            </div>

            {handicapIndex === null && (
              <p className="text-sm text-muted-foreground mt-2">
                Play 3+ rounds to get your handicap
              </p>
            )}

            <p className="text-sm text-muted-foreground mt-2">
              {rounds.length} round{rounds.length !== 1 ? "s" : ""} played
            </p>
          </div>

          {/* Upload button */}
          <div className="text-center mb-8">
            <Link
              to="/golf/upload"
              className="inline-flex items-center gap-2 bg-primary text-primary-foreground py-2 px-6 rounded-lg hover:bg-primary/90"
            >
              <Upload className="w-4 h-4" />
              Upload Round
            </Link>
          </div>

          {/* Rounds feed */}
          {rounds.length === 0 ? (
            <div className="bg-card rounded-lg border border-input p-8 text-center">
              <p className="text-muted-foreground mb-4">No rounds yet.</p>
              <Link
                to="/golf/upload"
                className="text-primary hover:underline"
              >
                Upload your first scorecard
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {rounds.map((round) => {
                const stats = getRoundStats(round);
                const isExpanded = expandedRound === round.id;
                return (
                  <div key={round.id} className="bg-card rounded-lg border border-input overflow-hidden">
                    <button
                      onClick={() =>
                        setExpandedRound(isExpanded ? null : round.id)
                      }
                      className="w-full p-4 text-left"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <MapPin className="w-4 h-4 text-green-500 flex-shrink-0" />
                            <span className="font-semibold truncate">
                              {round.course_name}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                            <Calendar className="w-3 h-3" />
                            <span>{round.played_at}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          <div className="text-right">
                            <div className="text-xl font-bold">
                              {round.adjusted_gross_score || "-"}
                            </div>
                            {round.differential !== null && (
                              <div className="text-xs text-green-500">
                                {round.differential.toFixed(1)}
                              </div>
                            )}
                          </div>
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-muted-foreground" />
                          )}
                        </div>
                      </div>

                      {/* Stat pills */}
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {stats.birdies > 0 && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-500">
                            {stats.birdies} birdie{stats.birdies !== 1 ? "s" : ""}
                          </span>
                        )}
                        {stats.bogeys > 0 && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-500">
                            {stats.bogeys} bogey{stats.bogeys !== 1 ? "s" : ""}
                          </span>
                        )}
                        {stats.doubles > 0 && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-500">
                            {stats.doubles} double{stats.doubles !== 1 ? "s" : ""}+
                          </span>
                        )}
                      </div>
                    </button>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-4 pb-4 space-y-3">
                            {/* Mini hole grid */}
                            <div className="grid grid-cols-9 gap-1">
                              {(round.holes || [])
                                .sort((a, b) => a.hole_number - b.hole_number)
                                .slice(0, 9)
                                .map((hole) => (
                                  <div
                                    key={hole.hole_number}
                                    className={`border rounded p-1 text-center text-xs ${getHoleBgClass(
                                      hole
                                    )}`}
                                  >
                                    <div className="text-muted-foreground">{hole.hole_number}</div>
                                    <div className="font-bold">
                                      {hole.strokes ?? "-"}
                                    </div>
                                  </div>
                                ))}
                            </div>
                            <div className="grid grid-cols-9 gap-1">
                              {(round.holes || [])
                                .sort((a, b) => a.hole_number - b.hole_number)
                                .slice(9, 18)
                                .map((hole) => (
                                  <div
                                    key={hole.hole_number}
                                    className={`border rounded p-1 text-center text-xs ${getHoleBgClass(
                                      hole
                                    )}`}
                                  >
                                    <div className="text-muted-foreground">{hole.hole_number}</div>
                                    <div className="font-bold">
                                      {hole.strokes ?? "-"}
                                    </div>
                                  </div>
                                ))}
                            </div>

                            {/* Scorecard thumbnail */}
                            {round.scorecard_image_url && (
                              <img
                                src={round.scorecard_image_url}
                                alt="Scorecard"
                                className="w-full max-h-32 object-contain rounded border border-input bg-black/5"
                              />
                            )}

                            <Link
                              to={`/golf/round/${round.id}`}
                              className="block text-center text-sm text-primary hover:underline"
                            >
                              View Full Round
                            </Link>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </motion.div>
    </Layout>
  );
};

export default GolfProfile;
