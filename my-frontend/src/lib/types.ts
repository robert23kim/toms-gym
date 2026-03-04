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
  image: string;
  status: "upcoming" | "ongoing" | "completed";
  categories: string[];
  participants: number;
  prizePool: {
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
  created_at?: string;
  lane_edges_auto?: LaneEdges;
  lane_edges_manual?: LaneEdges;
  frame_url?: string;
}

export interface RepMetrics {
  rep_number: number;
  elbow_angle_range: [number, number];
  tempo_ratio: number;
  elbow_drift_pct: number;
  body_sway_pct: number;
  form_grade: string;
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
