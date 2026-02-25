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

export type CompetitionStatus = 'upcoming' | 'ongoing' | 'completed';
