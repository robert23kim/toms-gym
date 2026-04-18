import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Calendar, MapPin, TrendingDown } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import { API_URL } from "../config";
import { GolfRound as GolfRoundType, GolfHoleScore } from "../lib/types";

const GolfRound: React.FC = () => {
  const { roundId } = useParams<{ roundId: string }>();
  const navigate = useNavigate();
  const [round, setRound] = useState<GolfRoundType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageExpanded, setImageExpanded] = useState(false);

  useEffect(() => {
    const fetchRound = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_URL}/golf/round/${roundId}`);
        setRound(response.data);
      } catch (err: any) {
        console.error("Error fetching round:", err);
        setError(
          err.response?.data?.error || err.message || "Failed to load round"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchRound();
  }, [roundId]);

  const getHoleBgClass = (hole: GolfHoleScore) => {
    if (hole.strokes === null) return "border-input";
    const diff = hole.strokes - hole.par;
    if (diff <= -1) return "bg-green-500/20 border-green-500/50";
    if (diff === 0) return "bg-card border-input";
    if (diff === 1) return "bg-yellow-500/20 border-yellow-500/50";
    return "bg-red-500/20 border-red-500/50";
  };

  if (loading) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !round) {
    return (
      <Layout>
        <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500">
              {error || "Round not found"}
            </div>
            <Link to="/golf/leaderboard" className="text-primary hover:underline mt-4 inline-block">
              Back to Golf
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  const holes = round.holes || [];
  const front9 = holes.filter((h) => h.hole_number <= 9).sort((a, b) => a.hole_number - b.hole_number);
  const back9 = holes.filter((h) => h.hole_number > 9).sort((a, b) => a.hole_number - b.hole_number);

  const sumStrokes = (holeSet: GolfHoleScore[]) =>
    holeSet.reduce((acc, h) => acc + (h.strokes || 0), 0);
  const sumPar = (holeSet: GolfHoleScore[]) =>
    holeSet.reduce((acc, h) => acc + h.par, 0);

  // Count stats
  const birdies = holes.filter((h) => h.strokes !== null && h.strokes < h.par).length;
  const pars = holes.filter((h) => h.strokes !== null && h.strokes === h.par).length;
  const bogeys = holes.filter((h) => h.strokes !== null && h.strokes === h.par + 1).length;
  const doubles = holes.filter((h) => h.strokes !== null && h.strokes >= h.par + 2).length;

  const renderHoleGrid = (holeSet: GolfHoleScore[], label: string) => (
    <div>
      <h3 className="text-lg font-semibold mb-3">{label}</h3>
      <div className="grid grid-cols-3 sm:grid-cols-3 md:grid-cols-9 gap-2">
        {holeSet.map((hole) => (
          <div
            key={hole.hole_number}
            className={`border rounded-lg p-2 ${getHoleBgClass(hole)}`}
          >
            <div className="text-xs text-muted-foreground text-center">
              #{hole.hole_number}
            </div>
            <div className="text-xs text-muted-foreground text-center">
              Par {hole.par}
            </div>
            <div className="text-2xl font-bold text-center">
              {hole.strokes !== null ? hole.strokes : "-"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
      >
        <div className="max-w-4xl mx-auto">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back
          </button>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8 space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-bold flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-green-500" />
                    {round.course_name}
                  </h1>
                  <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      {round.played_at}
                    </span>
                    <span>Slope: {round.slope_rating}</span>
                    <span>Rating: {round.course_rating}</span>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="bg-primary/5 rounded-lg px-4 py-2 text-center">
                    <div className="text-2xl font-bold text-primary">
                      {round.adjusted_gross_score || sumStrokes(holes)}
                    </div>
                    <div className="text-xs text-muted-foreground">Score</div>
                  </div>
                  {round.differential !== null && (
                    <div className="bg-green-500/10 rounded-lg px-4 py-2 text-center">
                      <div className="text-2xl font-bold text-green-500 flex items-center gap-1">
                        <TrendingDown className="w-4 h-4" />
                        {round.differential.toFixed(1)}
                      </div>
                      <div className="text-xs text-muted-foreground">Differential</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Hole grids */}
              {renderHoleGrid(front9, "Front 9")}
              {renderHoleGrid(back9, "Back 9")}

              {/* Totals */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-primary/5 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-primary">
                    {sumStrokes(front9)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Front 9 (Par {sumPar(front9)})
                  </div>
                </div>
                <div className="bg-primary/5 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-primary">
                    {sumStrokes(back9)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Back 9 (Par {sumPar(back9)})
                  </div>
                </div>
                <div className="bg-primary/5 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-primary">
                    {sumStrokes(holes)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Total (Par {sumPar(holes)})
                  </div>
                </div>
              </div>

              {/* Summary stats */}
              <div className="grid grid-cols-4 gap-3">
                <div className="bg-green-500/10 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-green-500">{birdies}</div>
                  <div className="text-xs text-muted-foreground">Birdies</div>
                </div>
                <div className="bg-primary/5 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-primary">{pars}</div>
                  <div className="text-xs text-muted-foreground">Pars</div>
                </div>
                <div className="bg-yellow-500/10 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-yellow-500">{bogeys}</div>
                  <div className="text-xs text-muted-foreground">Bogeys</div>
                </div>
                <div className="bg-red-500/10 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-red-500">{doubles}</div>
                  <div className="text-xs text-muted-foreground">Double+</div>
                </div>
              </div>

              {/* Scorecard image */}
              {round.scorecard_image_url && (
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">
                    Scorecard Photo
                  </h3>
                  <img
                    src={round.scorecard_image_url}
                    alt="Scorecard"
                    onClick={() => setImageExpanded(!imageExpanded)}
                    className={`rounded-lg border border-input cursor-pointer transition-all ${
                      imageExpanded
                        ? "w-full max-h-none"
                        : "w-full max-h-48 object-contain bg-black/5"
                    }`}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default GolfRound;
