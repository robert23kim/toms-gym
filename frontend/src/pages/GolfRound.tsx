import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Calendar, MapPin, TrendingDown } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import FairwayScope from "../components/FairwayScope";
import HighlightsGrid from "../components/golf/HighlightsGrid";
import HoleBarChart from "../components/golf/HoleBarChart";
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
    if (hole.strokes === null) return "fw-cell";
    const diff = hole.strokes - hole.par;
    if (diff <= -1) return "fw-cell fw-cell-birdie";
    if (diff === 0)  return "fw-cell fw-cell-par";
    return "fw-cell fw-cell-bogey-plus";
  };

  if (loading) {
    return (
      <Layout>
        <FairwayScope>
          <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--fw-info)]"></div>
              </div>
            </div>
          </div>
        </FairwayScope>
      </Layout>
    );
  }

  if (error || !round) {
    return (
      <Layout>
        <FairwayScope>
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
        </FairwayScope>
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
      <FairwayScope>
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

            <div className="fw-surface p-6 sm:p-8 space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div>
                  <h1 className="fw-h1 flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-[var(--fw-text-success)]" />
                    {round.course_name}
                  </h1>
                  <div className="flex items-center gap-4 mt-2 text-sm fw-text-secondary">
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {round.played_at}
                    </span>
                    <span>Slope {round.slope_rating}</span>
                    <span>Rating {round.course_rating}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <div className="fw-surface px-4 py-2 text-center">
                    <div className="text-2xl font-medium">
                      {round.adjusted_gross_score || sumStrokes(holes)}
                    </div>
                    <div className="text-xs fw-text-secondary">Score</div>
                  </div>
                  {round.differential !== null && (
                    <div className="fw-surface px-4 py-2 text-center">
                      <div className="text-2xl font-medium text-[var(--fw-text-success)] inline-flex items-center gap-1">
                        <TrendingDown className="w-4 h-4" />
                        {round.differential.toFixed(1)}
                      </div>
                      <div className="text-xs fw-text-secondary">Differential</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Hole grids */}
              {renderHoleGrid(front9, "Front 9")}
              {renderHoleGrid(back9, "Back 9")}

              <HoleBarChart holes={holes} />

              {/* Totals */}
              <div className="grid grid-cols-3 gap-2">
                <div className="fw-surface p-3 text-center">
                  <div className="text-xl font-medium">{sumStrokes(front9)}</div>
                  <div className="text-xs fw-text-secondary">Front 9 (Par {sumPar(front9)})</div>
                </div>
                <div className="fw-surface p-3 text-center">
                  <div className="text-xl font-medium">{sumStrokes(back9)}</div>
                  <div className="text-xs fw-text-secondary">Back 9 (Par {sumPar(back9)})</div>
                </div>
                <div className="fw-surface p-3 text-center">
                  <div className="text-xl font-medium">{sumStrokes(holes)}</div>
                  <div className="text-xs fw-text-secondary">Total (Par {sumPar(holes)})</div>
                </div>
              </div>

              {/* Summary stats */}
              <HighlightsGrid birdies={birdies} pars={pars} bogeys={bogeys} doublesOrWorse={doubles} />

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
        </motion.div>
      </FairwayScope>
    </Layout>
  );
};

export default GolfRound;
