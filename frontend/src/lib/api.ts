import axios from "axios";
import { API_URL } from '../config';
import {
  Competition,
  Participant,
  Challenge,
  ChallengeLeaderboard,
  LiftingResult,
  GolfCourse,
  GolfCourseSearchResult,
  GolfCreateCourseRequest,
  GolfHandicapHistoryRange,
  GolfHandicapHistoryResponse,
  GolfRoundDetailResponse,
  GolfRoundListResponse,
  GolfScoresUpdateRequest,
  GolfScoresUpdateResponse,
  BowlingResult,
} from './types';

// Collection of default challenge images for variety
const defaultChallengeImages = [
  'https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=800&auto=format&fit=crop&q=60', // Gym interior
  'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&auto=format&fit=crop&q=60', // Weight room
  'https://images.unsplash.com/photo-1526506118085-60ce8714f8c5?w=800&auto=format&fit=crop&q=60', // Man deadlifting
  'https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=800&auto=format&fit=crop&q=60', // Weights close-up
  'https://images.unsplash.com/photo-1605296867304-46d5465a13f1?w=800&auto=format&fit=crop&q=60', // Barbell on floor
];

// Function to get a consistent default image based on challenge ID
export const getDefaultChallengeImage = (id: string | number): string => {
  const idNum = typeof id === 'string' ? parseInt(id, 10) || 0 : id;
  const index = idNum % defaultChallengeImages.length;
  return defaultChallengeImages[index];
};

// Collection of Ghibli-style avatar URLs from a reliable CDN
const ghibliAvatars = [
  'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/54.png', // Psyduck (yellow)
  'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/39.png', // Jigglypuff (pink)
  'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png', // Pikachu (yellow)
  'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/7.png',  // Squirtle (blue)
  'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/133.png', // Eevee (brown)
  'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/94.png', // Gengar (purple)
  'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/143.png', // Snorlax (blue)
  'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/6.png'  // Charizard (orange)
];

// Function to get a consistent avatar based on user ID
export const getGhibliAvatar = (id: string | number): string => {
  const idString = id.toString();
  // Use the last character of the ID to get a consistent avatar for the same user
  const index = parseInt(idString.charAt(idString.length - 1), 10) % ghibliAvatars.length;
  return ghibliAvatars[index];
};

// Golf-feature avatars — uses DiceBear avataaars seeded by golfer name so
// two uploads of the same TOM/CHRIS share an avatar. Known names get hand-
// tuned presets; everyone else falls back to a stable seed-only avatar.
const AVATAAARS = "https://api.dicebear.com/7.x/avataaars/svg";
const KNOWN_GOLFER_AVATARS: Record<string, string> = {
  tom: `${AVATAAARS}?seed=tom-asian-guy&skinColor=fd9841&topType=shortHairShortFlat&hairColor=2c1b18&eyeType=squint&eyebrowType=default&mouthType=smile&clotheType=hoodie&clotheColor=3c4f5c`,
  chris: `${AVATAAARS}?seed=chris-white-dude&skinColor=edb98a&topType=shortHairShortCurly&hairColor=a55728&eyeType=default&eyebrowType=defaultNatural&mouthType=default&facialHairType=beardMedium&facialHairColor=a55728&clotheType=collarSweater&clotheColor=262e33`,
};

export const getGolfAvatar = (
  name?: string | null,
  fallbackId?: string | number,
): string => {
  const key = (name ?? "").trim().toLowerCase();
  if (key && KNOWN_GOLFER_AVATARS[key]) return KNOWN_GOLFER_AVATARS[key];
  const seed = encodeURIComponent(key || (fallbackId ?? "golfer").toString());
  return `${AVATAAARS}?seed=${seed}`;
};

// Transform backend data to frontend Competition type
export const transformCompetitionData = (backendData: any): Competition => {
  return {
    id: backendData.id,
    title: backendData.name,
    date: backendData.start_date,
    registrationDeadline: backendData.end_date,
    location: backendData.location || '',
    description: backendData.description || '',
    image: backendData.image || getDefaultChallengeImage(backendData.id),
    status: determineStatus(backendData.start_date, backendData.end_date),
    categories: getCategoriesFromMetadata(backendData),
    participants: [],
    prizePool: {
      first: 1000,
      second: 500,
      third: 250,
      total: 1750
    }
  };
};

// 'M' → ['Men'], 'F' → ['Women'], anything else (e.g. 'MF', 'all', missing) → both.
function genderToCategories(gender: string | null | undefined): string[] {
  if (gender === 'F') return ['Women'];
  if (gender === 'M') return ['Men'];
  return ['Men', 'Women'];
}

// Get competition categories from metadata
const getCategoriesFromMetadata = (data: any) => {
  if (data.lifttypes || data.weightclasses || data.gender) {
    return [
      ...(data.lifttypes || []),
      ...(data.weightclasses || []),
      ...genderToCategories(data.gender),
    ];
  } else if (data.description && data.description.includes(' - ')) {
    try {
      // Extract the JSON part from the description
      const metadataString = data.description.split(' - ')[1];
      const metadata = JSON.parse(metadataString);

      // Add categories from metadata
      return [
        ...(metadata.lifttypes || []),
        ...(metadata.weightclasses || []),
        ...genderToCategories(metadata.gender),
      ];
    } catch (err) {
      console.warn('Failed to parse competition metadata from description', err);
      return ['Powerlifting', 'Open'];
    }
  }
  return ['Powerlifting', 'Open'];
};

// Get competition status based on dates
export const determineStatus = (startDate: string, endDate: string): "upcoming" | "ongoing" | "completed" => {
  const now = new Date();
  const start = new Date(startDate);
  const end = new Date(endDate);

  if (now < start) return "upcoming";
  if (now > end) return "completed";
  return "ongoing";
};

// API Functions
export const getCompetitions = async (): Promise<Competition[]> => {
  try {
    const response = await axios.get(`${API_URL}/competitions`);
    const competitions = response.data.competitions || [];
    
    return await Promise.all(
      competitions.map(async (comp: any) => {
        const competition = transformCompetitionData(comp);
        
        // Get participants for each competition
        try {
          const participantsResponse = await axios.get(`${API_URL}/competitions/${comp.id}/participants`);
          competition.participants = participantsResponse.data.participants || [];
        } catch (error) {
          console.error(`Error fetching participants for competition ${comp.id}:`, error);
          competition.participants = [];
        }
        
        return competition;
      })
    );
  } catch (error) {
    console.error('Error fetching competitions:', error);
    return [];
  }
};

export const getCompetitionById = async (id: string): Promise<Competition | null> => {
  try {
    const [competitionResponse, participantsResponse, liftsResponse] = await Promise.all([
      axios.get(`${API_URL}/competitions/${id}`),
      axios.get(`${API_URL}/competitions/${id}/participants`),
      axios.get(`${API_URL}/competitions/${id}/lifts`)
    ]);
    
    const backendData = competitionResponse.data.competition;
    const participantsData = participantsResponse.data.participants || [];
    const liftsData = liftsResponse.data.lifts || [];
    
    // Transform data to match frontend types
    const competition = transformCompetitionData(backendData);
    
    // Process participants with their attempts
    competition.participants = participantsData.map((participant: any) => {
      // Get all lifts for this participant
      const participantLifts = liftsData.filter(
        (lift: any) => lift.participant_id === participant.id
      );
      
      // Group lifts by type (squat, bench, deadlift)
      const attempts: any = {
        squat: [],
        bench: [],
        deadlift: []
      };
      
      // Add all successful lifts to attempts
      participantLifts.forEach((lift: any) => {
        if (lift.status === 'success' && lift.lift_type in attempts) {
          attempts[lift.lift_type].push(lift.weight);
        }
      });
      
      // Calculate total weight (sum of highest successful attempts)
      const totalWeight = Object.values(attempts).reduce((total: number, lifts: any) => {
        return total + (lifts.length > 0 ? Math.max(...lifts) : 0);
      }, 0);
      
      return {
        id: participant.id,
        name: participant.name || 'Unknown Athlete',
        avatar: participant.avatar || getGhibliAvatar(participant.id),
        weightClass: participant.weight_class || 'Unknown',
        country: participant.country || 'Unknown',
        totalWeight,
        liftingDollars: participant.lifting_dollars || 0,
        attempts
      };
    });
    
    return competition;
  } catch (error) {
    console.error(`Error fetching competition ${id}:`, error);
    return null;
  }
};

// Get featured challenges for the home page
export const getFeaturedChallenges = async (limit = 2): Promise<Challenge[]> => {
  try {
    const response = await axios.get(`${API_URL}/competitions`);
    const dbChallenges = response.data.competitions || [];

    // Transform and take just the first few challenges for the featured section
    const transformedChallenges = dbChallenges
      .slice(0, limit)
      .map((challenge: any) => ({
        id: challenge.id,
        title: challenge.name,
        date: challenge.start_date,
        registrationDeadline: challenge.end_date,
        location: challenge.location || (challenge.description?.split(' - ')[0]) || '',
        description: challenge.description || '',
        image: challenge.image || getDefaultChallengeImage(challenge.id),
        status: determineStatus(challenge.start_date, challenge.end_date),
        categories: getCategoriesFromMetadata(challenge),
        participants: 0, // Will be updated when we get participant counts
        prizePool: {
          first: 1000,
          second: 500,
          third: 250,
          total: 1750
        }
      }));

    // Fetch participant counts for each challenge
    for (const challenge of transformedChallenges) {
      try {
        const participantsResponse = await axios.get(`${API_URL}/competitions/${challenge.id}/participants`);
        challenge.participants = (participantsResponse.data.participants || []).length;
      } catch (error) {
        console.error(`Error fetching participants for challenge ${challenge.id}:`, error);
      }
    }

    return transformedChallenges;
  } catch (error) {
    console.error("Error fetching featured challenges:", error);
    return [];
  }
};

// Normalize lift type to standard category
const normalizeLiftType = (liftType: string): string => {
  const type = liftType?.toLowerCase().trim() || '';
  if (type.includes('squat')) return 'squat';
  if (type.includes('bench')) return 'bench';
  if (type.includes('deadlift')) return 'deadlift';
  if (type.includes('curl') || type.includes('bicep')) return 'curl';
  if (type.includes('snatch')) return 'snatch';
  if (type.includes('clean')) return 'clean';
  return type;
};

// Get top lifts for each category with video links
export const getTopLifts = async (): Promise<Record<string, any[]>> => {
  try {
    // Fetch all competitions
    const competitionsResponse = await axios.get(`${API_URL}/competitions`);
    const competitions = competitionsResponse.data.competitions || [];

    // Collect all lifts with their competition and participant info
    const allLifts: any[] = [];

    for (const competition of competitions) {
      try {
        const [participantsResponse, liftsResponse] = await Promise.all([
          axios.get(`${API_URL}/competitions/${competition.id}/participants`),
          axios.get(`${API_URL}/competitions/${competition.id}/lifts`)
        ]);

        const participants = participantsResponse.data.participants || [];
        const lifts = liftsResponse.data.lifts || [];

        // Create a map of participant IDs to participant data
        const participantMap = new Map(
          participants.map((p: any) => [p.id, p])
        );

        // Add each lift with full context (include all lifts with videos)
        for (const lift of lifts) {
          if (lift.video_url) {
            const participant = participantMap.get(lift.participant_id);
            if (participant) {
              allLifts.push({
                id: participant.id,
                name: participant.name || 'Unknown Athlete',
                avatar: participant.avatar || getGhibliAvatar(participant.id),
                weightClass: participant.weight_class || 'Unknown',
                country: participant.country || 'Unknown',
                competitionId: competition.id,
                liftId: lift.id,
                liftType: normalizeLiftType(lift.lift_type),
                bestLift: parseFloat(lift.weight) || 0,
                videoUrl: lift.video_url
              });
            }
          }
        }
      } catch (error) {
        console.error(`Error fetching data for competition ${competition.id}:`, error);
      }
    }

    // Group by lift type and get top 3 for each category
    // Include categories that have lifts in the database
    const categories = ['squat', 'bench', 'deadlift', 'curl', 'snatch', 'clean'];
    const topLifts: Record<string, any[]> = {};

    for (const category of categories) {
      const liftsInCategory = allLifts
        .filter(lift => lift.liftType === category)
        .sort((a, b) => b.bestLift - a.bestLift)
        .slice(0, 3);

      // Only include categories that have lifts
      if (liftsInCategory.length > 0) {
        topLifts[category] = liftsInCategory;
      }
    }

    return topLifts;
  } catch (error) {
    console.error('Error fetching top lifts:', error);
    return { squat: [], bench: [], deadlift: [] };
  }
};

// Per-challenge leaderboard (podium + ranked table). Server ranks by the
// challenge's single metric; the frontend renders whatever it returns.
export async function getChallengeLeaderboard(id: string): Promise<ChallengeLeaderboard> {
  const response = await axios.get(`${API_URL}/competitions/${id}/leaderboard`);
  return response.data;
}

export async function triggerLiftingAnalysis(attemptId: string): Promise<{ lifting_result_id: string; status: string }> {
  const response = await axios.post(`${API_URL}/lifting/analyze/${attemptId}`);
  return response.data;
}

export async function getLiftingResult(attemptId: string): Promise<LiftingResult> {
  const response = await axios.get(`${API_URL}/lifting/result/${attemptId}`);
  return response.data;
}

// ---------------------------------------------------------------------------
// Golf — Phase B nested Course/Tee/Round shapes.
// Contracts mirror backend/toms_gym/routes/golf_routes.py (commit e5500d6).
// ---------------------------------------------------------------------------

export async function fetchRound(roundId: string): Promise<GolfRoundDetailResponse> {
  const response = await axios.get(`${API_URL}/golf/round/${roundId}`);
  return response.data;
}

export async function fetchRounds(
  userId: string,
  options: { limit?: number; offset?: number } = {},
): Promise<GolfRoundListResponse> {
  const params = new URLSearchParams({ user_id: userId });
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  if (options.offset !== undefined) params.set("offset", String(options.offset));
  const response = await axios.get(`${API_URL}/golf/rounds?${params.toString()}`);
  return response.data;
}

// T14 profile hub — a user's bowling attempts (GET /bowling/results?user_id=)
export async function fetchBowlingResultsByUser(
  userId: string,
): Promise<BowlingResult[]> {
  const response = await axios.get(
    `${API_URL}/bowling/results?user_id=${encodeURIComponent(userId)}`,
  );
  return Array.isArray(response.data) ? response.data : [];
}

export async function updateRoundScores(
  roundId: string,
  body: GolfScoresUpdateRequest,
): Promise<GolfScoresUpdateResponse> {
  const response = await axios.put(`${API_URL}/golf/round/${roundId}/scores`, body);
  return response.data;
}

export async function searchCourses(
  q: string,
  options: { near?: [number, number]; limit?: number } = {},
): Promise<GolfCourseSearchResult[]> {
  if (!q.trim()) return [];
  const params = new URLSearchParams({ q });
  if (options.near) params.set("near", `${options.near[0]},${options.near[1]}`);
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  const response = await axios.get(`${API_URL}/golf/courses?${params.toString()}`);
  return response.data.courses || [];
}

export async function createCourse(
  body: GolfCreateCourseRequest,
): Promise<GolfCourse> {
  const response = await axios.post(`${API_URL}/golf/courses`, body);
  return response.data.course;
}

export async function getHandicapHistory(
  userId: string,
  range: GolfHandicapHistoryRange = "12m",
): Promise<GolfHandicapHistoryResponse> {
  const response = await axios.get(
    `${API_URL}/golf/users/${userId}/handicap/history?range=${range}`,
  );
  return response.data;
}

// ---------------------------------------------------------------------------
// Tickets — bug reports & feature requests.
// Mirrors backend/toms_gym/routes/ticket_routes.py.
// ---------------------------------------------------------------------------

export type TicketType = "bug" | "feature";
export type TicketStatus = "open" | "in_progress" | "closed";

export interface Ticket {
  id: string;
  type: TicketType;
  title: string;
  description: string;
  page_url: string | null;
  contact_email: string | null;
  user_id: string | null;
  status: TicketStatus;
  created_at: string;
  updated_at: string;
}

export interface CreateTicketInput {
  type: TicketType;
  title: string;
  description: string;
  page_url?: string;
  email?: string;
  user_id?: string;
}

export async function createTicket(
  input: CreateTicketInput,
): Promise<{ ticket_id: string }> {
  const response = await axios.post(`${API_URL}/tickets`, input);
  return response.data;
}

export async function fetchTickets(
  filters: { status?: TicketStatus; type?: TicketType } = {},
): Promise<Ticket[]> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.type) params.set("type", filters.type);
  const query = params.toString();
  const response = await axios.get(
    `${API_URL}/tickets${query ? `?${query}` : ""}`,
  );
  return response.data.tickets || [];
}

export async function updateTicketStatus(
  id: string,
  status: TicketStatus,
): Promise<Ticket> {
  const response = await axios.put(`${API_URL}/tickets/${id}/status`, { status });
  return response.data;
}
