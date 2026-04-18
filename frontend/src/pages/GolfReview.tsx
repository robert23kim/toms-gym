import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, AlertTriangle, Check, Trophy, Users } from "lucide-react";
import axios from "axios";
import Layout from "../components/Layout";
import FairwayScope from "../components/FairwayScope";
import ReviewBanner from "../components/golf/ReviewBanner";
import { API_URL } from "../config";
import { GolfRound, GolfHoleScore, GolfDetectedPlayer } from "../lib/types";

const buildFullHoles = (partial: GolfHoleScore[] | undefined): GolfHoleScore[] => {
  const src = partial || [];
  const out: GolfHoleScore[] = [];
  for (let i = 1; i <= 18; i++) {
    const existing = src.find((h) => h.hole_number === i);
    out.push(
      existing || { hole_number: i, par: 4, strokes: null, ocr_confidence: 0 }
    );
  }
  return out;
};

const GolfReview: React.FC = () => {
  const { roundId } = useParams<{ roundId: string }>();
  const navigate = useNavigate();
  const [round, setRound] = useState<GolfRound | null>(null);
  const [detectedPlayers, setDetectedPlayers] = useState<GolfDetectedPlayer[]>([]);
  const [selectedPlayerName, setSelectedPlayerName] = useState<string | null>(null);
  const [holes, setHoles] = useState<GolfHoleScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingHole, setEditingHole] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [resultData, setResultData] = useState<{
    differential: number | null;
    handicap_index: number | null;
    adjusted_gross_score: number;
  } | null>(null);

  useEffect(() => {
    const fetchRound = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_URL}/golf/round/${roundId}`);
        setRound(response.data);
        const players: GolfDetectedPlayer[] = response.data.detected_players || [];
        setDetectedPlayers(players);
        setHoles(buildFullHoles(response.data.holes));
        if (players.length > 0) {
          setSelectedPlayerName(players[0].name);
        }
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

  const handlePlayerPick = (name: string) => {
    const player = detectedPlayers.find((p) => p.name === name);
    if (!player) return;
    setSelectedPlayerName(name);
    setHoles(buildFullHoles(player.holes));
  };

  const updateHoleStrokes = (holeNumber: number, strokes: number | null) => {
    setHoles((prev) =>
      prev.map((h) =>
        h.hole_number === holeNumber ? { ...h, strokes, manually_corrected: true } : h
      )
    );
  };

  const updateHolePar = (holeNumber: number, par: number) => {
    setHoles((prev) =>
      prev.map((h) =>
        h.hole_number === holeNumber ? { ...h, par } : h
      )
    );
  };

  const allHolesComplete = holes.every(
    (h) => h.strokes !== null && h.strokes >= 1
  );

  const needsReviewCount = holes.filter(
    (h) => h.ocr_confidence !== undefined && h.ocr_confidence < 0.85 && h.strokes !== null
  ).length;

  const front9 = holes.filter((h) => h.hole_number <= 9);
  const back9 = holes.filter((h) => h.hole_number > 9);

  const sumStrokes = (holeSet: GolfHoleScore[]) =>
    holeSet.reduce((acc, h) => acc + (h.strokes || 0), 0);
  const sumPar = (holeSet: GolfHoleScore[]) =>
    holeSet.reduce((acc, h) => acc + h.par, 0);

  const front9Total = sumStrokes(front9);
  const back9Total = sumStrokes(back9);
  const grandTotal = front9Total + back9Total;
  const front9Par = sumPar(front9);
  const back9Par = sumPar(back9);
  const totalPar = front9Par + back9Par;

  const getHoleBgClass = (hole: GolfHoleScore) => {
    if (hole.strokes === null) return "fw-cell";
    const diff = hole.strokes - hole.par;
    if (diff <= -1) return "fw-cell fw-cell-birdie";
    if (diff === 0)  return "fw-cell fw-cell-par";
    return "fw-cell fw-cell-bogey-plus";
  };

  const handleConfirm = async () => {
    if (!allHolesComplete) return;
    setConfirming(true);
    setError(null);

    try {
      const response = await axios.put(
        `${API_URL}/golf/round/${roundId}/scores`,
        {
          holes: holes.map((h) => ({
            hole_number: h.hole_number,
            par: h.par,
            strokes: h.strokes,
          })),
        }
      );

      setResultData({
        differential: response.data.differential,
        handicap_index: response.data.handicap_index,
        adjusted_gross_score: response.data.adjusted_gross_score,
      });
      setConfirmed(true);
    } catch (err: any) {
      console.error("Confirm error:", err);
      setError(
        err.response?.data?.error || "Failed to confirm scores"
      );
    } finally {
      setConfirming(false);
    }
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

  if (error && !round) {
    return (
      <Layout>
        <FairwayScope>
          <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-500">
                {error}
              </div>
            </div>
          </div>
        </FairwayScope>
      </Layout>
    );
  }

  if (confirmed && resultData) {
    const userId = round?.user_id || localStorage.getItem("userId");
    return (
      <Layout>
        <FairwayScope>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
        >
          <div className="max-w-2xl mx-auto text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.2 }}
              className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6"
            >
              <Check className="w-10 h-10 text-green-500" />
            </motion.div>

            <h1 className="text-3xl font-bold mb-2">Scores Confirmed!</h1>
            <p className="text-muted-foreground mb-8">
              {round?.course_name} - {round?.played_at}
            </p>

            <div className="grid grid-cols-2 gap-4 mb-8">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-card rounded-lg p-6 border border-input"
              >
                <div className="text-3xl font-bold text-primary">
                  {resultData.adjusted_gross_score}
                </div>
                <div className="text-sm text-muted-foreground">Total Score</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="bg-card rounded-lg p-6 border border-input"
              >
                <div className="text-3xl font-bold text-green-500">
                  {resultData.differential !== null
                    ? resultData.differential.toFixed(1)
                    : "N/A"}
                </div>
                <div className="text-sm text-muted-foreground">Differential</div>
              </motion.div>
            </div>

            {resultData.handicap_index !== null && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.7 }}
                className="bg-card rounded-lg p-6 border border-input mb-8"
              >
                <div className="flex items-center justify-center gap-3">
                  <Trophy className="w-6 h-6 text-green-500" />
                  <div>
                    <div className="text-4xl font-bold text-green-500">
                      {resultData.handicap_index.toFixed(1)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Handicap Index
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            <div className="flex gap-4 justify-center">
              <Link
                to={userId ? `/golf/profile/${userId}` : "/golf/profile"}
                className="bg-primary text-primary-foreground py-2 px-6 rounded-lg hover:bg-primary/90"
              >
                View Profile
              </Link>
              <Link
                to={`/golf/round/${roundId}`}
                className="bg-card text-foreground py-2 px-6 rounded-lg border border-input hover:bg-muted"
              >
                View Round
              </Link>
            </div>
          </div>
        </motion.div>
        </FairwayScope>
      </Layout>
    );
  }

  const renderHoleGrid = (holeSet: GolfHoleScore[], label: string) => (
    <div>
      <h3 className="text-lg font-semibold mb-3">{label}</h3>
      <div className="grid grid-cols-3 sm:grid-cols-3 md:grid-cols-9 gap-2">
        {holeSet.map((hole) => (
          <div
            key={hole.hole_number}
            data-testid={`scorecard-cell-${hole.hole_number}`}
            onClick={() => setEditingHole(hole.hole_number)}
            className={`relative p-2 cursor-pointer transition-colors ${getHoleBgClass(
              hole
            )} ${editingHole === hole.hole_number ? "fw-selected" : ""} ${
              hole.ocr_confidence !== undefined &&
              hole.ocr_confidence < 0.85 &&
              hole.strokes !== null
                ? "fw-cell-needs-review"
                : ""
            }`}
          >
            <div className="text-xs text-muted-foreground text-center">
              #{hole.hole_number}
            </div>
            <div className="text-xs text-muted-foreground text-center">
              Par {hole.par}
            </div>
            {editingHole === hole.hole_number ? (
              <div className="space-y-1">
                <input
                  type="number"
                  min="1"
                  max="15"
                  value={hole.strokes ?? ""}
                  onChange={(e) => {
                    const val = e.target.value
                      ? parseInt(e.target.value, 10)
                      : null;
                    updateHoleStrokes(hole.hole_number, val);
                  }}
                  onBlur={() => setEditingHole(null)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") setEditingHole(null);
                  }}
                  autoFocus
                  className="w-full text-center text-lg font-bold bg-background border border-input rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <input
                  type="number"
                  min="3"
                  max="6"
                  value={hole.par}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (val >= 3 && val <= 6) updateHolePar(hole.hole_number, val);
                  }}
                  className="w-full text-center text-xs bg-background border border-input rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Par"
                />
              </div>
            ) : (
              <div className="text-2xl font-bold text-center min-h-[2rem] flex items-center justify-center">
                {hole.strokes !== null ? hole.strokes : "-"}
              </div>
            )}
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
          <Link
            to="/golf/upload"
            className="inline-flex items-center text-muted-foreground hover:text-foreground mb-8"
          >
            <ArrowLeft className="mr-2" size={16} />
            Back to Upload
          </Link>

          <div className="bg-card rounded-lg shadow-lg overflow-hidden">
            <div className="p-6 sm:p-8 space-y-6">
              <div>
                <h1 className="text-2xl font-bold">Review Scores</h1>
                <p className="text-muted-foreground mt-1">
                  {round?.course_name} - {round?.played_at}
                </p>
                {round?.ocr_confidence !== null && round?.ocr_confidence !== undefined && (
                  <p className="text-xs text-muted-foreground mt-1">
                    OCR confidence: {(round.ocr_confidence * 100).toFixed(0)}%
                    {" - "}Tap any cell to edit scores and par
                  </p>
                )}
              </div>

              <ReviewBanner needsReviewCount={needsReviewCount} />

              {/* Scorecard image */}
              {round?.scorecard_image_url && (
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">
                    Scorecard Reference
                  </h3>
                  <img
                    src={round.scorecard_image_url}
                    alt="Scorecard"
                    className="w-full rounded-lg border border-input max-h-64 object-contain bg-black/5"
                  />
                </div>
              )}

              {/* Detected players picker */}
              {detectedPlayers.length > 0 && (
                <div
                  data-testid="detected-players"
                  className="bg-primary/5 border border-primary/20 rounded-lg p-4"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Users className="w-4 h-4 text-primary" />
                    <h3 className="text-sm font-semibold">
                      {detectedPlayers.length === 1
                        ? "Detected player"
                        : `Detected ${detectedPlayers.length} players — pick your row`}
                    </h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {detectedPlayers.map((p) => {
                      const total = p.holes.reduce(
                        (acc, h) => acc + (h.strokes || 0),
                        0
                      );
                      const active = selectedPlayerName === p.name;
                      return (
                        <button
                          key={p.name}
                          type="button"
                          data-testid={`player-pill-${p.name}`}
                          onClick={() => handlePlayerPick(p.name)}
                          className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                            active
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-background text-foreground border-input hover:border-primary/60"
                          }`}
                        >
                          <span className="font-semibold">{p.name}</span>
                          <span className="opacity-70 ml-2">total {total}</span>
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    The selected player's scores are loaded below. Tap any cell to
                    correct a value.
                  </p>
                </div>
              )}

              {/* Hole grids */}
              {renderHoleGrid(front9, "Front 9")}
              {renderHoleGrid(back9, "Back 9")}

              {/* Running totals */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-primary/5 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-primary">
                    {front9Total}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Front 9 (Par {front9Par})
                  </div>
                </div>
                <div className="bg-primary/5 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-primary">
                    {back9Total}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Back 9 (Par {back9Par})
                  </div>
                </div>
                <div className="bg-primary/5 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-primary">
                    {grandTotal}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Total (Par {totalPar})
                  </div>
                </div>
              </div>

              {error && (
                <div className="text-red-500 text-sm">{error}</div>
              )}

              {/* Confirm button */}
              <button
                onClick={handleConfirm}
                disabled={!allHolesComplete || confirming}
                title={
                  !allHolesComplete
                    ? "All 18 holes must have a score of 1 or more"
                    : undefined
                }
                className="w-full bg-primary text-primary-foreground py-3 px-4 rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
              >
                {confirming ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground"></div>
                    Confirming...
                  </span>
                ) : (
                  "Confirm Scores"
                )}
              </button>

              {!allHolesComplete && (
                <p className="text-xs text-muted-foreground text-center">
                  {holes.filter((h) => h.strokes === null || h.strokes < 1).length}{" "}
                  hole(s) still need scores. Tap the cell to enter a score.
                </p>
              )}
            </div>
          </div>
        </div>
      </motion.div>
      </FairwayScope>
    </Layout>
  );
};

export default GolfReview;
