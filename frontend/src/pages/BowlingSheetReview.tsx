import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import axios from "axios";
import { ArrowLeft, Plus, Trash2, X } from "lucide-react";
import Layout from "../components/Layout";
import FrameStrip, { frameErrors } from "../components/bowling/FrameStrip";
import { API_URL } from "../config";
import { scoreFrames, Roll } from "../lib/bowlingScore";
import {
  BowlingLinkedUser,
  BowlingSaveAs,
  BowlingSheet,
  BowlingSheetConfirmGame,
  BowlingSheetType,
  confirmBowlingSheet,
  deleteBowlingSheet,
  fetchBowlingSheet,
} from "../lib/api";

interface EditableGame {
  gameNumber: number;
  totalScore: number | null;
  frames: Roll[][] | null;
  flagged: boolean;
  flagReason: string | null;
  inferredFrames: number[];
}

interface EditablePlayer {
  name: string;
  hdcp: number | null;
  games: EditableGame[];
  saveAs: BowlingSaveAs;
  linkedUser: BowlingLinkedUser | null;
}

const NIGHT_GAMES = 3;

const emptyFrames = (): Roll[][] => Array.from({ length: 10 }, () => []);

const blankPlayer = (sheetType: BowlingSheetType): EditablePlayer => ({
  name: "",
  hdcp: null,
  saveAs: null,
  linkedUser: null,
  games:
    sheetType === "night"
      ? Array.from({ length: NIGHT_GAMES }, (_, i) => ({
          gameNumber: i + 1,
          totalScore: null,
          frames: null,
          flagged: false,
          flagReason: null,
          inferredFrames: [],
        }))
      : [
          {
            gameNumber: 1,
            totalScore: null,
            frames: emptyFrames(),
            flagged: false,
            flagReason: null,
            inferredFrames: [],
          },
        ],
});

const toEditable = (sheet: BowlingSheet, viewerId: string | null): EditablePlayer[] => {
  if (sheet.players.length === 0) return [blankPlayer(sheet.sheet_type)];
  return sheet.players.map((player) => ({
    name: player.name,
    hdcp: player.games.find((g) => g.hdcp !== null)?.hdcp ?? null,
    linkedUser: player.linked_user ?? null,
    // remembered from the last time this uploader saved that name
    saveAs: !player.linked_user ? null : player.linked_user.id === viewerId ? "me" : player.linked_user.id,
    games: player.games.map((g) => ({
      gameNumber: g.game_number,
      totalScore: g.total_score,
      frames: g.frames ? g.frames.map((f) => [...f]) : sheet.sheet_type === "game" ? emptyFrames() : null,
      flagged: g.flagged,
      flagReason: g.flag_reason,
      inferredFrames: g.inferred_frames ?? [],
    })),
  }));
};

const parseScore = (text: string): number | null => {
  if (text.trim() === "") return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
};

/** OCR names are printed in caps; match on the whole name or its first token. */
const matchesProfileName = (playerName: string, profileName: string): boolean => {
  const player = playerName.trim().toLowerCase();
  const profile = profileName.trim().toLowerCase();
  if (!player || !profile) return false;
  return player === profile || player === profile.split(/\s+/)[0];
};

const seriesScratch = (player: EditablePlayer): number =>
  player.games.reduce((sum, g) => sum + (g.totalScore ?? 0), 0);

const seriesTotal = (player: EditablePlayer): number =>
  seriesScratch(player) + (player.hdcp ?? 0) * player.games.length;

const BowlingSheetReview: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [sheet, setSheet] = useState<BowlingSheet | null>(null);
  const [players, setPlayers] = useState<EditablePlayer[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const sheetType: BowlingSheetType = sheet?.sheet_type ?? "night";

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    fetchBowlingSheet(id)
      .then((data) => {
        if (cancelled) return;
        setSheet(data);
        setPlayers(toEditable(data, localStorage.getItem("userId")));
      })
      .catch(() => {
        if (!cancelled) setLoadError("Could not load this score sheet.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    const userId = localStorage.getItem("userId");
    if (!userId || players.length === 0 || players.some((p) => p.saveAs === "me")) return;
    let cancelled = false;
    axios
      .get(`${API_URL}/users/${userId}/profile`)
      .then((res) => {
        const profileName = (res.data as { user?: { name?: string } })?.user?.name;
        if (cancelled || !profileName) return;
        const match = players.findIndex((p) => matchesProfileName(p.name, profileName));
        if (match >= 0) setSaveAs(match, "me");
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // Runs once the parsed roster arrives; re-running on every selection change
    // would fight the user's own choice.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [players.length]);

  useEffect(() => {
    if (!lightboxOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightboxOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [lightboxOpen]);

  const updatePlayer = useCallback(
    (index: number, patch: Partial<EditablePlayer>) => {
      setPlayers((current) =>
        current.map((player, i) => (i === index ? { ...player, ...patch } : player)),
      );
    },
    [],
  );

  const setSaveAs = useCallback((index: number, saveAs: BowlingSaveAs) => {
    setPlayers((current) =>
      current.map((player, i) => {
        if (i === index) return { ...player, saveAs };
        // only one row can be the signed-in bowler
        return saveAs === "me" && player.saveAs === "me" ? { ...player, saveAs: null } : player;
      }),
    );
  }, []);

  const updateGame = useCallback(
    (playerIndex: number, gameIndex: number, patch: Partial<EditableGame>) => {
      setPlayers((current) =>
        current.map((player, i) =>
          i === playerIndex
            ? {
                ...player,
                games: player.games.map((game, g) =>
                  g === gameIndex ? { ...game, ...patch } : game,
                ),
              }
            : player,
        ),
      );
    },
    [],
  );

  const blockingError = useMemo(() => {
    for (const player of players) {
      for (const game of player.games) {
        if (!game.frames) continue;
        const problem = frameErrors(game.frames).find((e) => e !== null);
        if (problem) return problem;
      }
    }
    return null;
  }, [players]);

  const handleSave = async () => {
    if (!id || blockingError) return;
    setSaving(true);
    setSaveError(null);
    try {
      const body = {
        players: players
          .filter((player) => player.name.trim() !== "")
          .map((player) => ({
            name: player.name.trim(),
            save_as: player.saveAs,
            games: player.games.map((game): BowlingSheetConfirmGame => {
              const scored = game.frames ? scoreFrames(game.frames) : null;
              const usableFrames = scored && scored.valid && scored.complete;
              return {
                game_number: game.gameNumber,
                total_score: usableFrames ? scored.total : game.totalScore,
                hdcp: player.hdcp,
                frames: usableFrames ? game.frames : null,
              };
            }),
          })),
      };
      await confirmBowlingSheet(id, body);
      const userId = localStorage.getItem("userId");
      const savedMe = players.some((p) => p.saveAs === "me");
      navigate(savedMe && userId ? `/bowling/insights/${userId}?sheet=${id}` : "/bowl");
    } catch {
      setSaveError("Could not save these scores. Try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      return;
    }
    try {
      await deleteBowlingSheet(id);
      navigate("/bowl");
    } catch {
      setSaveError("Could not delete this sheet.");
      setConfirmingDelete(false);
    }
  };

  if (loadError) {
    return (
      <Layout>
        <div className="max-w-2xl mx-auto py-10 px-4 text-center">
          <p className="text-muted-foreground">{loadError}</p>
        </div>
      </Layout>
    );
  }

  if (!sheet) {
    return (
      <Layout>
        <div className="max-w-2xl mx-auto py-10 px-4 text-center text-muted-foreground">
          Reading your score sheet…
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-3xl mx-auto py-6 px-4"
      >
        <Link
          to="/bowl"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6"
        >
          <ArrowLeft className="mr-2" size={16} />
          Back to Bowl
        </Link>

        <div className="glass rounded-2xl p-6 space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold">Check the scores</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {sheet.team_name ? `${sheet.team_name} · ` : ""}
                {sheet.played_on}
                {sheet.sheet_type === "night" ? " · night results" : " · single game"}
              </p>
            </div>
            {sheet.image_url && (
              <button
                type="button"
                onClick={() => setLightboxOpen(true)}
                aria-label="View the score sheet photo"
                className="shrink-0 rounded-lg overflow-hidden border border-input hover:opacity-90"
              >
                <img
                  src={sheet.image_url}
                  alt="Score sheet"
                  className="h-16 w-24 object-cover"
                />
              </button>
            )}
          </div>

          {sheet.processing_status === "failed" && (
            <div className="text-sm rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2">
              We couldn&apos;t read this photo{sheet.error_message ? ` (${sheet.error_message})` : ""}.
              Type the scores in below, or go back and retake it.
            </div>
          )}

          {sheet.flagged_count > 0 && (
            <p className="text-sm text-muted-foreground">
              {sheet.flagged_count} number{sheet.flagged_count === 1 ? "" : "s"} need a second look —
              they are highlighted below.
            </p>
          )}

          <div className="space-y-3">
            {players.map((player, playerIndex) => {
              const rowFlagged = player.games.some((g) => g.flagged);
              const reasons = Array.from(
                new Set(player.games.map((g) => g.flagReason).filter((r): r is string => !!r)),
              );
              return (
                <div
                  key={playerIndex}
                  data-testid={`player-${player.name || playerIndex}`}
                  className={`rounded-xl border p-4 space-y-3 ${
                    rowFlagged ? "border-amber-500/50 bg-amber-500/5" : "border-input"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="text"
                      aria-label={`Player name ${playerIndex + 1}`}
                      value={player.name}
                      onChange={(e) => updatePlayer(playerIndex, { name: e.target.value })}
                      placeholder="Name on the sheet"
                      className="flex-1 min-w-0 h-9 px-2 rounded-md bg-background border border-input text-sm font-medium focus:outline-none focus:ring-2 focus:ring-accent"
                    />
                    <select
                      aria-label={`Save ${player.name || `player ${playerIndex + 1}`} to`}
                      value={player.saveAs ?? ""}
                      onChange={(e) => setSaveAs(playerIndex, e.target.value === "" ? null : e.target.value)}
                      className="h-9 max-w-[45%] px-2 rounded-md bg-background border border-input text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                    >
                      <option value="">Don't save</option>
                      <option value="me">Me</option>
                      {player.linkedUser && player.linkedUser.id !== localStorage.getItem("userId") ? (
                        <option value={player.linkedUser.id}>{player.linkedUser.name}'s profile</option>
                      ) : (
                        <option value="new">New profile{player.name ? ` for ${player.name}` : ""}</option>
                      )}
                    </select>
                  </div>

                  {reasons.length > 0 && (
                    <p className="text-xs text-amber-600 dark:text-amber-400">{reasons.join(" · ")}</p>
                  )}

                  {sheetType === "night" ? (
                    <>
                      <div className="grid grid-cols-4 gap-2">
                        {player.games.map((game, gameIndex) => (
                          <label key={game.gameNumber} className="block">
                            <span className="block text-[11px] text-muted-foreground mb-0.5">
                              G{game.gameNumber}
                            </span>
                            <input
                              type="number"
                              inputMode="numeric"
                              aria-label={`${player.name} game ${game.gameNumber}`}
                              value={game.totalScore ?? ""}
                              onChange={(e) =>
                                updateGame(playerIndex, gameIndex, {
                                  totalScore: parseScore(e.target.value),
                                })
                              }
                              className={`w-full h-9 px-2 rounded-md bg-background border text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-accent ${
                                game.flagged ? "border-amber-500" : "border-input"
                              }`}
                            />
                          </label>
                        ))}
                        <label className="block">
                          <span className="block text-[11px] text-muted-foreground mb-0.5">
                            Hdcp / game
                          </span>
                          <input
                            type="number"
                            inputMode="numeric"
                            aria-label={`${player.name} handicap`}
                            value={player.hdcp ?? ""}
                            onChange={(e) =>
                              updatePlayer(playerIndex, { hdcp: parseScore(e.target.value) })
                            }
                            className="w-full h-9 px-2 rounded-md bg-background border border-input text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-accent"
                          />
                        </label>
                      </div>
                      <div className="flex gap-4 text-sm">
                        <span className="text-muted-foreground">
                          Scratch{" "}
                          <span data-testid="scratch" className="font-medium text-foreground tabular-nums">
                            {seriesScratch(player)}
                          </span>
                        </span>
                        <span className="text-muted-foreground">
                          Total{" "}
                          <span data-testid="total" className="font-medium text-foreground tabular-nums">
                            {seriesTotal(player)}
                          </span>
                        </span>
                      </div>
                    </>
                  ) : (
                    player.games.map((game, gameIndex) => (
                      <FrameStrip
                        key={game.gameNumber}
                        playerName={player.name}
                        frames={game.frames ?? emptyFrames()}
                        inferred={game.inferredFrames}
                        onChange={(frames) => updateGame(playerIndex, gameIndex, { frames })}
                      />
                    ))
                  )}
                </div>
              );
            })}
          </div>

          <p className="text-xs text-muted-foreground">
            Each name saves to the profile you pick; the app remembers it for next time.
          </p>

          <button
            type="button"
            onClick={() => setPlayers((current) => [...current, blankPlayer(sheetType)])}
            className="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-input text-sm hover:bg-secondary/40"
          >
            <Plus className="w-4 h-4" />
            Add player
          </button>

          {(saveError || blockingError) && (
            <div className="text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-lg px-3 py-2">
              {saveError || blockingError}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || blockingError !== null}
              className="flex-1 h-11 rounded-lg bg-accent text-accent-foreground font-medium text-sm hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? "Saving…" : "Save these scores"}
            </button>
            <button
              type="button"
              onClick={handleDelete}
              onBlur={() => setConfirmingDelete(false)}
              className={`inline-flex items-center gap-2 h-11 px-4 rounded-lg border text-sm ${
                confirmingDelete
                  ? "border-destructive text-destructive"
                  : "border-input text-muted-foreground hover:text-foreground"
              }`}
            >
              <Trash2 className="w-4 h-4" />
              {confirmingDelete ? "Really delete?" : "Delete sheet"}
            </button>
          </div>
        </div>

        <AnimatePresence>
          {lightboxOpen && sheet.image_url && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={() => setLightboxOpen(false)}
              className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4"
              role="dialog"
              aria-modal="true"
              aria-label="Score sheet preview"
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setLightboxOpen(false);
                }}
                className="absolute top-4 right-4 h-9 w-9 rounded-full bg-black/60 text-white inline-flex items-center justify-center hover:bg-black/80"
                aria-label="Close preview"
              >
                <X className="w-5 h-5" />
              </button>
              <img
                src={sheet.image_url}
                alt="Score sheet full size"
                onClick={(e) => e.stopPropagation()}
                className="max-w-[95vw] max-h-[90vh] object-contain rounded shadow-2xl"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </Layout>
  );
};

export default BowlingSheetReview;
