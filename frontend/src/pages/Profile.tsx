import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import Layout from "../components/Layout";
import { Calendar, ArrowLeft, User, Dumbbell, TrendingUp, CircleDot, Flag, Upload, Camera } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import axios from "axios";
import { API_URL } from "../config";
import LiftHistoryList from '../components/profile/LiftHistoryList';
import GhibliAvatar from '../components/GhibliAvatar';
import { fetchRounds, fetchBowlingResultsByUser, fetchBowlingGames, fetchChampions, Champion, BowlingGameRow } from "../lib/api";
import TrophyCase, { championTitle } from "../components/profile/TrophyCase";
import ChampionConfetti from "../components/profile/ChampionConfetti";
import AvatarPicker from "../components/profile/AvatarPicker";
import { GolfRoundListItem, BowlingResult } from "../lib/types";

// Interfaces for API response data
interface UserData {
  id: string;
  name: string;
  email: string;
  username?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: any; // To allow for additional fields
}

interface Competition {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  description: string;
  weight_class: string;
  status: string;
  total_weight: number;
  successful_lifts: number;
}

interface BestLift {
  type: string;
  best_weight: number;
  competition_name: string;
  competition_id: string;
}

interface Achievements {
  total_competitions: number;
  total_successful_lifts: number;
  heaviest_lift: number;
  best_snatch: number;
  best_clean_and_jerk: number;
}

interface UploadedVideo {
  attempt_id: string;
  lift_type: string;
  weight: number;
  video_url: string;
  created_at: string;
  status: string;
  competition_id: string;
  competition_name: string;
}

interface ProfileData {
  user: UserData;
  competitions: Competition[];
  best_lifts: BestLift[];
  achievements: Achievements;
  uploaded_videos?: UploadedVideo[];
}

type SportTab = "lift" | "bowl" | "golf";

const Profile = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<SportTab>("lift");

  // Golf + bowling activity (per-sport sections of the unified hub)
  const [golfRounds, setGolfRounds] = useState<GolfRoundListItem[]>([]);
  const [golfHandicap, setGolfHandicap] = useState<number | null>(null);
  const [bowlingResults, setBowlingResults] = useState<BowlingResult[]>([]);
  const [sheetGames, setSheetGames] = useState<BowlingGameRow[]>([]);

  // Challenge championships (trophy case + title flair); non-fatal fetch.
  const [champions, setChampions] = useState<Champion[]>([]);
  // Chosen avatar (migration 015); overrides the deterministic GhibliAvatar.
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);

  const resolvedUserId = id || localStorage.getItem('userId') || null;
  const isOwner = resolvedUserId === localStorage.getItem('userId');

  const fetchProfileData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const userId = id || localStorage.getItem('userId');

      if (!userId) {
        setError("No user ID found");
        setLoading(false);
        return;
      }

      // User profile (lifting + competitions). Golf/bowling are fetched in
      // parallel and are non-fatal — a user may have activity in only one sport.
      const [profileRes, golfRes, bowlRes, sheetRes, champRes] = await Promise.all([
        axios.get(`${API_URL}/users/${userId}/profile`),
        fetchRounds(userId).catch(() => null),
        fetchBowlingResultsByUser(userId).catch(() => []),
        fetchBowlingGames(userId, 5).catch(() => null),
        fetchChampions(userId).catch(() => []),
      ]);

      setProfileData(profileRes.data);
      if (golfRes) {
        setGolfRounds(golfRes.rounds || []);
        setGolfHandicap(golfRes.handicap_index ?? null);
      }
      setBowlingResults(bowlRes || []);
      setSheetGames(sheetRes?.games || []);
      setChampions(champRes || []);
      setAvatarUrl(profileRes.data?.user?.avatar_url ?? null);
    } catch (err: any) {
      console.error('Error fetching profile data:', err);
      const errorMessage = err.response?.data?.error || 'Failed to load profile data';
      setError(`${errorMessage} (${err.message})`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!authLoading) {
      const userId = id || localStorage.getItem('userId');
      if (userId || isAuthenticated) {
        fetchProfileData();
      }
    }
  }, [id, isAuthenticated, authLoading, fetchProfileData]);

  const getJoinDate = (createdAt?: string) => {
    if (!createdAt) return "N/A";
    const date = new Date(createdAt);
    return `${date.toLocaleString('default', { month: 'long' })} ${date.getFullYear()}`;
  };

  if (authLoading || loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-[60vh]">
          <p>Loading profile...</p>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="flex flex-col justify-center items-center h-[60vh]">
          <p className="text-red-500 mb-4">{error}</p>
          <button
            onClick={() => fetchProfileData()}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Try Again
          </button>
        </div>
      </Layout>
    );
  }

  // Check if we have any way to identify a user (via URL, localStorage, or auth)
  const hasUserId = id || localStorage.getItem('userId');
  if (!isAuthenticated && !hasUserId) {
    return (
      <Layout>
        <div className="flex flex-col justify-center items-center h-[60vh]">
          <p className="text-muted-foreground mb-4">No profile found. Upload a video to create your profile!</p>
          <div className="flex gap-3">
            <Link
              to="/upload"
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Upload
            </Link>
            <Link
              to="/find-profile"
              className="px-4 py-2 border border-border rounded-md hover:bg-secondary/50"
            >
              Find my profile
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  if (!profileData) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-[60vh]">
          <p>No profile data found</p>
        </div>
      </Layout>
    );
  }

  const userId = profileData.user.id;
  const videoCount = profileData.uploaded_videos?.length ?? 0;
  const golfCount = golfRounds.length;
  const bowlCount = bowlingResults.length;

  const tabs: { key: SportTab; label: string; icon: React.ReactNode; count: number }[] = [
    { key: "lift", label: "Lift", icon: <Dumbbell size={16} />, count: videoCount },
    { key: "bowl", label: "Bowl", icon: <CircleDot size={16} />, count: bowlCount },
    { key: "golf", label: "Golf", icon: <Flag size={16} />, count: golfCount },
  ];

  return (
    <Layout>
      <div className="mb-6 flex items-center">
        <button
          onClick={() => navigate("/")}
          className="mr-4 flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={16} className="mr-1" /> Back
        </button>
        <h1 className="text-2xl font-semibold">Profile</h1>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto"
      >
        {/* Profile Header */}
        <div className="bg-card rounded-xl p-6 mb-6 shadow-sm">
          <div className="flex items-center gap-6">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt=""
                className="h-24 w-24 rounded-full object-cover bg-secondary"
              />
            ) : (
              <GhibliAvatar
                id={profileData.user.id}
                name={profileData.user.name}
                size="xl"
              />
            )}
            <div>
              <h1 className="text-3xl font-bold mb-2">{profileData.user.name}</h1>
              {champions.length > 0 && (
                <p className="inline-block text-sm font-medium text-amber-600 dark:text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-full px-3 py-1 mb-2">
                  {championTitle(champions[0])}
                </p>
              )}
              {isOwner && (
                <p className="text-muted-foreground">{profileData.user.email}</p>
              )}
              {isOwner && (
                <button
                  type="button"
                  onClick={() => setShowAvatarPicker((v) => !v)}
                  className="mt-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showAvatarPicker ? "Hide avatars" : "Change avatar"}
                </button>
              )}
            </div>
          </div>
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar size={18} />
              <span>Joined {getJoinDate(profileData.user.created_at)}</span>
            </div>
            {profileData.user.username && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <User size={18} />
                <span>@{profileData.user.username}</span>
              </div>
            )}
          </div>
        </div>

        {champions.length > 0 && (
          <ChampionConfetti
            competitionId={champions[0].competition_id}
            userId={champions[0].user_id}
          />
        )}

        {showAvatarPicker && resolvedUserId && (
          <AvatarPicker userId={resolvedUserId} onSelected={setAvatarUrl} />
        )}

        <TrophyCase champions={champions} />

        {/* Sport tabs — one unified identity across Lift / Bowl / Golf */}
        <div className="flex gap-2 mb-6 border-b border-border">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.key
                  ? "border-accent text-accent"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.count > 0 && (
                <span className="text-xs bg-secondary text-secondary-foreground rounded-full px-2 py-0.5">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ---- LIFT ---- */}
        {activeTab === "lift" && (
          <div>
            {videoCount > 0 ? (
              <>
                <div className="flex justify-end mb-3">
                  <Link to="/lift/upload" className="text-accent hover:underline text-sm">
                    Upload a lift →
                  </Link>
                </div>
                {userId && <LiftHistoryList userId={userId} />}
              </>
            ) : (
              <div className="bg-card rounded-xl p-6 mb-6 shadow-sm text-center">
                <p className="text-muted-foreground mb-4">No lifts yet</p>
                <Link
                  to="/lift/upload"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90"
                >
                  <Upload size={18} />
                  Upload your first lift
                </Link>
              </div>
            )}

            <div className="mb-6">
              <Link
                to={`/profile/${userId}/weekly-lifts`}
                className="flex items-center justify-between bg-card rounded-xl p-4 shadow-sm hover:bg-secondary/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <TrendingUp className="text-accent" size={24} />
                  <div>
                    <h2 className="text-lg font-semibold">Track Weekly Lifts</h2>
                    <p className="text-sm text-muted-foreground">Log your weekly max bench, squat, deadlift & more</p>
                  </div>
                </div>
                <ArrowLeft size={20} className="rotate-180 text-muted-foreground" />
              </Link>
            </div>
          </div>
        )}

        {/* ---- BOWL ---- */}
        {activeTab === "bowl" && (
          <div className="space-y-6">
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Camera className="text-accent" size={24} />
                <h2 className="text-xl font-semibold">Score sheets</h2>
              </div>
              {resolvedUserId && sheetGames.length > 0 && (
                <Link
                  to={`/bowling/insights/${resolvedUserId}`}
                  className="text-accent hover:underline text-sm"
                >
                  Insights →
                </Link>
              )}
            </div>

            {sheetGames.length > 0 ? (
              <div className="space-y-2">
                {sheetGames.map((game) => (
                  <Link
                    key={game.id}
                    to={`/bowling/scoresheet/${game.sheet_id}`}
                    className="flex items-center gap-3 p-3 bg-background rounded-lg hover:bg-secondary/50 transition-colors"
                  >
                    <span className="text-sm text-muted-foreground w-24 shrink-0">
                      {game.played_on}
                    </span>
                    <span className="flex-1 text-sm text-muted-foreground">
                      Game {game.game_number}
                    </span>
                    <span className="text-lg font-semibold tabular-nums">
                      {game.total_score ?? "—"}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-muted-foreground mb-4">No games banked yet</p>
                <Link
                  to="/bowling/snap"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90"
                >
                  <Camera size={18} />
                  Snap a sheet
                </Link>
              </div>
            )}
          </div>

          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <CircleDot className="text-accent" size={24} />
                <h2 className="text-xl font-semibold">Bowling Attempts</h2>
                {bowlCount > 0 && (
                  <span className="text-sm text-muted-foreground">({bowlCount})</span>
                )}
              </div>
              <Link to="/bowling/upload" className="text-accent hover:underline text-sm">
                Upload new →
              </Link>
            </div>

            {bowlingResults.length > 0 ? (
              <div className="space-y-2">
                {bowlingResults.map((r) => (
                  <Link
                    key={r.id}
                    to={`/bowling/result/${r.attempt_id}`}
                    className="flex items-center justify-between p-3 bg-background rounded-lg hover:bg-secondary/50 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 bg-accent/10 rounded flex items-center justify-center flex-shrink-0">
                        <CircleDot size={18} className="text-accent" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-sm truncate">
                          {r.competition_name || "Bowling attempt"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {r.created_at ? new Date(r.created_at).toLocaleDateString() : ""}
                          {r.entry_board != null && ` • entry board ${r.entry_board.toFixed(1)}`}
                        </p>
                      </div>
                    </div>
                    <span className={`ml-auto text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${
                      r.processing_status === 'completed' ? 'bg-green-100 text-green-800' :
                      r.processing_status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {r.processing_status}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-muted-foreground mb-4">No bowling attempts yet</p>
                <Link
                  to="/bowling/upload"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90"
                >
                  <Upload size={18} />
                  Upload a Bowling Video
                </Link>
              </div>
            )}
          </div>
          </div>
        )}

        {/* ---- GOLF ---- */}
        {activeTab === "golf" && (
          <div className="space-y-6">
            <div className="bg-card rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Flag className="text-accent" size={24} />
                  <div>
                    <h2 className="text-xl font-semibold">Golf</h2>
                    <p className="text-sm text-muted-foreground">
                      Handicap index{" "}
                      <span className="font-medium text-foreground">
                        {golfHandicap !== null ? golfHandicap.toFixed(1) : "—"}
                      </span>
                    </p>
                  </div>
                </div>
                {/* Cross-link into the dedicated golf profile surface */}
                <Link
                  to={`/golf/profile/${userId}`}
                  className="text-accent hover:underline text-sm"
                >
                  Full golf profile →
                </Link>
              </div>
            </div>

            <div className="bg-card rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Rounds</h2>
                <Link to="/golf/upload" className="text-accent hover:underline text-sm">
                  Upload scorecard →
                </Link>
              </div>

              {golfRounds.length > 0 ? (
                <div className="space-y-2">
                  {golfRounds.map((round) => (
                    <Link
                      key={round.id}
                      to={`/golf/round/${round.id}`}
                      className="flex items-center justify-between p-3 bg-background rounded-lg hover:bg-secondary/50 transition-colors"
                    >
                      <div className="min-w-0">
                        <p className="font-medium text-sm truncate">
                          {round.course?.name ?? "Unknown course"}
                        </p>
                        <p className="text-xs text-muted-foreground">{round.played_on}</p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="font-bold">{round.total_score ?? "-"}</div>
                        {round.score_differential !== null && (
                          <div className="text-xs text-green-600">
                            {round.score_differential.toFixed(1)}
                          </div>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground mb-4">No golf rounds yet</p>
                  <Link
                    to="/golf/upload"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90"
                  >
                    <Upload size={18} />
                    Upload a Scorecard
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </motion.div>
    </Layout>
  );
};

export default Profile;
