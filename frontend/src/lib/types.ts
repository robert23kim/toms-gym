export interface Competition {
  id: string;
  title: string;
  date: string;
  registrationDeadline: string;
  location: string;
  description: string;
  image: string;
  status: 'upcoming' | 'ongoing' | 'completed';
  categories: string[];
  participants: Participant[];
  prizePool: {
    first: number;
    second: number;
    third: number;
    total: number;
  };
}

export interface Participant {
  id: string;
  name: string;
  avatar: string;
  weightClass: string;
  country: string;
  totalWeight?: number;
  liftingDollars: number;
  attempts?: {
    squat: number[];
    bench: number[];
    deadlift: number[];
  };
  lifts?: Lift[];
}

export interface Lift {
  id: string;
  participantId: string;
  competitionId: string;
  type: 'squat' | 'bench' | 'deadlift';
  weight: number;
  success: boolean;
  videoUrl: string;
  timestamp: string;
}

export interface StoreItem {
  id: string;
  name: string;
  description: string;
  price: number;
  image: string;
  category: 'gear' | 'supplements' | 'apparel' | 'accessories';
  inStock: boolean;
}

export interface Purchase {
  id: string;
  userId: string;
  itemId: string;
  date: string;
  price: number;
}

export interface Challenge {
  id: number | string;
  title: string;
  date: string;
  registrationDeadline: string;
  location: string;
  description: string;
  image?: string;
  status: "upcoming" | "ongoing" | "completed";
  categories: string[];
  lifttypes?: string[];
  participants: number;
  prizePool?: {
    first: number;
    second: number;
    third: number;
    total: number;
  };
}

export interface LaneEdges {
  top_left: [number, number];
  top_right: [number, number];
  bottom_left: [number, number];
  bottom_right: [number, number];
  left_edge_points?: [number, number][];
  right_edge_points?: [number, number][];
}

export interface BowlingResult {
  id: string;
  attempt_id: string;
  processing_status: 'queued' | 'processing' | 'completed' | 'failed';
  debug_video_url?: string;
  trajectory_png_url?: string;
  board_at_pins?: number;
  entry_board?: number;
  detection_rate?: number;
  processing_time_s?: number;
  error_message?: string;
  user_name?: string;
  user_email?: string;
  competition_id?: string | null;
  competition_name?: string | null;
  created_at?: string;
  lane_edges_auto?: LaneEdges;
  lane_edges_manual?: LaneEdges;
  frame_url?: string;
}

export interface MetricFeedback {
  key: string;
  label: string;
  value: number;
  unit: string;
  target: string;
  status: 'pass' | 'warn' | 'fail';
  description?: string;
  best_time_s?: number;
  worst_time_s?: number;
  clip_url?: string;
}

export interface RepMetrics {
  rep_number: number;
  elbow_angle_range: [number, number];
  tempo_ratio: number;
  elbow_drift_pct: number;
  body_sway_pct: number;
  momentum_score?: number;
  rom_score?: number;
  shoulder_flexion_avg?: number;
  form_grade: string;
  form_score: number;
  metrics?: MetricFeedback[];
}

export interface PlankPerSecond {
  t: number;
  state: string;
  body_line_deg: number;
  elbow_deg: number;
  form_score: number;
}

export interface LiftingReport {
  camera_view: string;
  active_arm: string;
  total_reps: number;
  overall_grade: string;
  overall_score: number;
  rep_metrics: RepMetrics[];
  insights: string[];
  lift_type?: string;

  // Plank-specific fields (only present when lift_type === 'plank').
  // The bicep_curl-style fields above are not meaningful for plank.
  total_in_plank_s?: number;
  longest_run_s?: number;
  overall_form_score?: number;
  plank_type?: 'forearm' | 'high' | 'transitioning';
  pose_detection_rate?: number;
  forearm_s?: number;
  high_s?: number;
  body_line_median_deg?: number;
  body_line_stdev_deg?: number;
  per_second?: PlankPerSecond[];
}

export interface LiftingResult {
  id: string;
  attempt_id: string;
  processing_status: 'queued' | 'processing' | 'completed' | 'failed';
  annotated_video_url?: string;
  summary_url?: string;
  report?: LiftingReport;
  processing_time_s?: number;
  error_message?: string;
  created_at?: string;
  updated_at?: string;
}

export type CompetitionStatus = 'upcoming' | 'ongoing' | 'completed';

/** Ball annotation. x, y = contact point where ball touches lane surface. */
export interface BallAnnotation {
  x: number;
  y: number;
  radius: number;
}

export interface FrameMarkers {
  pin_hit?: number;
  breakpoint?: number;
  ball_down?: number;
  ball_off_deck?: number;
}

export interface VideoMetadata {
  fps: number;
  total_frames: number;
  width: number;
  height: number;
}

export interface Annotation {
  version: string;
  video_metadata: VideoMetadata;
  lane_edges?: LaneEdges;
  frame_lane_edges?: Record<string, LaneEdges>;
  frame_markers: FrameMarkers;
  ball_annotations: Record<string, BallAnnotation | null>;
}

export interface FrameData {
  frames_prefix: string;
  total_frames: number;
  fps: number;
  width: number;
  height: number;
}

/**
 * Golf API types — Phase B nested Course/Tee/Round shapes.
 * Mirrors backend `/golf/*` response contracts in
 * `backend/toms_gym/routes/golf_routes.py` (commit e5500d6).
 */

export interface GolfHole {
  hole_number: number;
  par: number;
  strokes: number | null;
  ocr_confidence: number | null;
  manually_corrected?: boolean;
  /** OCR checksum/strikeover suspicion — review UI highlights these. */
  flagged?: boolean;
}

/** Tee rating/slope read off the card's printed table by the grid parser. */
export interface GolfDetectedTee {
  name: string;
  rating: number;
  slope: number;
}

export interface GolfDetectedPlayer {
  name: string;
  holes: GolfHole[];
}

export type GolfCourseStatus = "verified" | "pending";

export interface GolfCourse {
  id: string;
  name: string;
  city: string | null;
  state: string | null;
  country: string | null;
  latitude: number | null;
  longitude: number | null;
  holes: number;
  status: GolfCourseStatus;
}

export interface GolfTee {
  id: string | null;
  name: string | null;
  color_hex: string | null;
  rating_18: number | null;
  slope_18: number | null;
  rating_9_front: number | null;
  slope_9_front: number | null;
  rating_9_back: number | null;
  slope_9_back: number | null;
  yardage: number | null;
  par: number | null;
  hole_pars: number[] | null;
  hole_yardages: number[] | null;
  hole_handicaps: number[] | null;
}

export type GolfProcessingStatus =
  | "pending"
  | "ocr_complete"
  | "confirmed"
  | "failed";

export interface GolfRoundDetail {
  id: string;
  user_id: string;
  played_on: string | null;
  holes: number;
  course: GolfCourse | null;
  tee: GolfTee;
  hole_scores: GolfHole[];
  scores: number[] | null;
  total_score: number | null;
  front_nine: number | null;
  back_nine: number | null;
  score_differential: number | null;
  scorecard_image_url: string | null;
  ocr_confidence: number | null;
  processing_status: GolfProcessingStatus;
  needs_tee: boolean;
  needs_course?: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export type GolfRoundListItem = GolfRoundDetail;

export interface GolfRoundDetailResponse {
  round: GolfRoundDetail;
  detected_players: GolfDetectedPlayer[];
  detected_tees?: GolfDetectedTee[];
  needs_tee?: boolean;
  needs_course?: boolean;
}

export interface GolfRoundListResponse {
  rounds: GolfRoundListItem[];
  handicap_index: number | null;
  rounds_used: number;
}

export interface GolfScoresUpdateRequest {
  user_id: string;
  holes: Array<{ hole_number: number; par: number; strokes: number }>;
}

export interface GolfScoresUpdateResponse {
  round_id: string;
  user_id: string;
  adjusted_gross_score: number;
  total_score: number;
  score_differential: number | null;
  processing_status: GolfProcessingStatus;
  handicap_index: number | null;
}

export interface GolfHandicap {
  user_id: string;
  handicap_index: number | null;
  rounds_used: number;
  differentials_used: number[];
  created_at: string | null;
}

export type GolfHandicapHistoryRange = "6m" | "12m" | "24m" | "all";

export interface GolfHandicapHistoryPoint {
  handicap_index: number | null;
  rounds_used: number;
  created_at: string | null;
}

export interface GolfHandicapHistoryResponse {
  history: GolfHandicapHistoryPoint[];
  range: GolfHandicapHistoryRange;
}

export interface GolfCourseSearchResult {
  id: string;
  name: string;
  city: string | null;
  state: string | null;
  country: string | null;
  latitude: number | null;
  longitude: number | null;
  holes: number;
  status: GolfCourseStatus;
  similarity?: number;
  distance_km?: number;
}

export interface GolfCreateCourseRequest {
  name: string;
  city?: string;
  state?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  holes?: 9 | 18;
  user_id?: string;
}

/**
 * Per-challenge leaderboard — mirrors
 * `GET /competitions/<id>/leaderboard` in
 * `backend/toms_gym/routes/competition_routes.py` +
 * `backend/toms_gym/services/challenge_leaderboard.py`.
 */
export type ChallengeMetric = "time" | "weight";

export interface ChallengeLeaderboardHistoryPoint {
  /** held seconds (time) or weight_kg (weight). */
  score: number;
  date: string | null;
}

export interface ChallengeLeaderboardRow {
  rank: number;
  user_id: string;
  name: string | null;
  /** time: best hold seconds; weight: best-lift total. */
  score: number;
  /** weight: {lift_type: max}; time: {"Plank": best_hold}. */
  best_by_lift: Record<string, number>;
  /** time only; null otherwise. */
  form_score: number | null;
  /** id of the score-setting attempt; null when the athlete has no qualifying attempt. */
  attempt_id: string | null;
  clip_url: string | null;
  thumbnail_url: string | null;
  /** ISO date of the best attempt. */
  date: string | null;
  weight_class: string | null;
  gender: string | null;
  attempt_count: number;
  /** chronological qualifying attempts — powers the (step 3) sparkline. */
  history: ChallengeLeaderboardHistoryPoint[];
}

export interface ChallengeLeaderboardMomentum {
  joined: number;
  uploaded_today: number;
}

export interface ChallengeLeaderboard {
  competition_id: string;
  metric: ChallengeMetric;
  lift_types: string[];
  momentum: ChallengeLeaderboardMomentum;
  rows: ChallengeLeaderboardRow[];
}

export interface GolfLeaderboardEntry {
  rank: number;
  user_id: string;
  user_name: string;
  handicap_index: number;
  monthly_delta: number | null;
  rounds_played: number;
  rounds_used: number;
  best_differential: number | null;
  latest_snapshot_at: string | null;
}
