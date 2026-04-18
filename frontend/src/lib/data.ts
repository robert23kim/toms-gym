import { Competition, StoreItem } from './types';

// Mock data for development
export const competitions: Competition[] = [
  {
    id: '1',
    title: 'World Powerlifting Championship 2023',
    date: '2023-12-15',
    registrationDeadline: '2023-11-30',
    location: 'Stockholm, Sweden',
    description: 'The premier powerlifting event of the year featuring the strongest athletes from around the world. Compete in squat, bench press, and deadlift to determine the ultimate champions.',
    image: 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?q=80&w=1470&auto=format&fit=crop',
    status: 'upcoming',
    categories: ['Open', 'Junior', 'Master'],
    prizePool: {
      first: 5000,
      second: 2500,
      third: 1000,
      total: 10000
    },
    participants: [
      {
        id: 'p1',
        name: 'Tom Oka',
        avatar: 'https://randomuser.me/api/portraits/men/32.jpg',
        weightClass: '83kg',
        country: 'USA',
        totalWeight: 817,
        liftingDollars: 7500,
        attempts: {
          squat: [280, 290, 300],
          bench: [170, 180, 187],
          deadlift: [320, 330, 340],
        },
      },
      {
        id: 'p2',
        name: 'Jess Hum',
        avatar: 'https://randomuser.me/api/portraits/women/44.jpg',
        weightClass: '72kg',
        country: 'Canada',
        totalWeight: 602,
        liftingDollars: 3500,
        attempts: {
          squat: [210, 220, 230],
          bench: [120, 127, 132],
          deadlift: [240, 250, 260],
        },
      },
      {
        id: 'p3',
        name: 'Rob Kim',
        avatar: 'https://randomuser.me/api/portraits/men/22.jpg',
        weightClass: '93kg',
        country: 'USA',
        totalWeight: 855,
        liftingDollars: 5000,
        attempts: {
          squat: [300, 310, 320],
          bench: [180, 190, 195],
          deadlift: [340, 350, 360],
        },
      },
    ],
  },
  {
    id: '2',
    title: 'National Strength League Finals',
    date: '2023-11-28',
    registrationDeadline: '2023-11-15',
    location: 'Austin, TX, USA',
    description: 'The culmination of the National Strength League season, featuring the top qualified powerlifters in a head-to-head battle for the championship title.',
    image: 'https://images.unsplash.com/photo-1599058917212-d750089bc07e?q=80&w=1469&auto=format&fit=crop',
    status: 'upcoming',
    categories: ['Men', 'Women', 'Teams'],
    prizePool: {
      first: 3000,
      second: 1500,
      third: 750,
      total: 6000
    },
    participants: [
      {
        id: 'p4',
        name: 'Caleb Larson',
        avatar: 'https://randomuser.me/api/portraits/men/68.jpg',
        weightClass: '105kg',
        country: 'USA',
        totalWeight: 920,
        liftingDollars: 4500,
        attempts: {
          squat: [320, 330, 340],
          bench: [200, 210, 220],
          deadlift: [350, 360, 370],
        },
      },
      {
        id: 'p5',
        name: 'Sagar Patel',
        avatar: 'https://randomuser.me/api/portraits/men/75.jpg',
        weightClass: '93kg',
        country: 'USA',
        totalWeight: 880,
        liftingDollars: 2800,
        attempts: {
          squat: [310, 320, 330],
          bench: [190, 200, 210],
          deadlift: [330, 340, 350],
        },
      },
    ],
  },
  {
    id: '3',
    title: 'European Open Classic Championships',
    date: '2024-02-10',
    registrationDeadline: '2024-01-15',
    location: 'Berlin, Germany',
    description: 'Europe\'s largest raw powerlifting event. No supportive equipment allowed, just pure strength and technique compete for continental supremacy.',
    image: 'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=1470&auto=format&fit=crop',
    status: 'upcoming',
    categories: ['Open', 'Junior', 'Sub-Junior', 'Master'],
    participants: [
      {
        id: 'p6',
        name: 'Lukas Schmidt',
        avatar: 'https://randomuser.me/api/portraits/men/52.jpg',
        weightClass: '93kg',
        country: 'Germany',
        totalWeight: 830,
        attempts: {
          squat: [290, 305, 315],
          bench: [175, 185, 192],
          deadlift: [320, 335, 345],
        },
      },
      {
        id: 'p7',
        name: 'Elena Petrova',
        avatar: 'https://randomuser.me/api/portraits/women/29.jpg',
        weightClass: '84kg',
        country: 'Russia',
        totalWeight: 657,
        attempts: {
          squat: [230, 240, 247],
          bench: [130, 137, 142],
          deadlift: [250, 265, 280],
        },
      },
    ],
  },
  {
    id: '4',
    title: 'Pacific Rim Championship',
    date: '2024-01-20',
    registrationDeadline: '2024-01-05',
    location: 'Tokyo, Japan',
    description: 'The premier powerlifting event for the Asia-Pacific region, bringing together elite lifters from across the Pacific Rim nations.',
    image: 'https://images.unsplash.com/photo-1574680096145-d05b474e2155?q=80&w=1469&auto=format&fit=crop',
    status: 'upcoming',
    categories: ['Men', 'Women'],
    participants: [
      {
        id: 'p8',
        name: 'Taro Yamamoto',
        avatar: 'https://randomuser.me/api/portraits/men/42.jpg',
        weightClass: '74kg',
        country: 'Japan',
        totalWeight: 760,
        attempts: {
          squat: [260, 275, 285],
          bench: [170, 180, 185],
          deadlift: [300, 310, 315],
        },
      },
      {
        id: 'p9',
        name: 'Kim Min-ji',
        avatar: 'https://randomuser.me/api/portraits/women/39.jpg',
        weightClass: '57kg',
        country: 'South Korea',
        totalWeight: 480,
        attempts: {
          squat: [160, 170, 175],
          bench: [95, 100, 105],
          deadlift: [185, 195, 200],
        },
      },
    ],
  },
];

// Store items
export const storeItems: StoreItem[] = [
  {
    id: 'si1',
    name: 'Premium Lifting Belt',
    description: 'Professional grade leather belt for maximum support during heavy lifts.',
    price: 2000,
    image: 'https://images.unsplash.com/photo-1620188467120-5042ed1eb5da?q=80&w=1932&auto=format&fit=crop',
    category: 'gear',
    inStock: true
  },
  {
    id: 'si2',
    name: 'Competition Knee Sleeves',
    description: 'IPF approved knee sleeves for optimal support and performance.',
    price: 1500,
    image: 'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=1470&auto=format&fit=crop',
    category: 'gear',
    inStock: true
  },
  {
    id: 'si3',
    name: "Tom's Gym Premium T-Shirt",
    description: 'High-quality cotton blend t-shirt with the official Tom\'s Gym logo.',
    price: 500,
    image: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?q=80&w=1480&auto=format&fit=crop',
    category: 'apparel',
    inStock: true
  },
  {
    id: 'si4',
    name: 'Pre-Workout Formula',
    description: 'Competition-approved pre-workout supplement for maximum performance.',
    price: 1000,
    image: 'https://images.unsplash.com/photo-1579722820308-d74e571900a9?q=80&w=1470&auto=format&fit=crop',
    category: 'supplements',
    inStock: true
  },
  {
    id: 'si5',
    name: 'Lifting Straps',
    description: 'Heavy-duty cotton straps for secure grip during pulls.',
    price: 300,
    image: 'https://images.unsplash.com/photo-1517344368193-41552b6ad3f5?q=80&w=1470&auto=format&fit=crop',
    category: 'accessories',
    inStock: true
  }
];

// Sample lifts with videos (mock data)
export const sampleLifts = [
  {
    id: 'l1',
    participantId: 'p1',
    competitionId: '1',
    type: 'squat',
    weight: 300,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
    timestamp: '2023-12-15T14:30:00Z',
  },
  {
    id: 'l2',
    participantId: 'p1',
    competitionId: '1',
    type: 'bench',
    weight: 187,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
    timestamp: '2023-12-15T15:15:00Z',
  },
  {
    id: 'l3',
    participantId: 'p1',
    competitionId: '1',
    type: 'deadlift',
    weight: 340,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4',
    timestamp: '2023-12-15T16:00:00Z',
  },
  {
    id: 'l4',
    participantId: 'p3',
    competitionId: '1',
    type: 'squat',
    weight: 320,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
    timestamp: '2023-12-15T14:45:00Z',
  },
  {
    id: 'l5',
    participantId: 'p3',
    competitionId: '1',
    type: 'bench',
    weight: 195,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
    timestamp: '2023-12-15T15:30:00Z',
  },
  {
    id: 'l6',
    participantId: 'p3',
    competitionId: '1',
    type: 'deadlift',
    weight: 360,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4',
    timestamp: '2023-12-15T16:15:00Z',
  },
  {
    id: 'l7',
    participantId: 'p4',
    competitionId: '2',
    type: 'squat',
    weight: 340,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
    timestamp: '2023-11-28T14:30:00Z',
  },
  {
    id: 'l8',
    participantId: 'p4',
    competitionId: '2',
    type: 'bench',
    weight: 220,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
    timestamp: '2023-11-28T15:15:00Z',
  },
  {
    id: 'l9',
    participantId: 'p4',
    competitionId: '2',
    type: 'deadlift',
    weight: 370,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4',
    timestamp: '2023-11-28T16:00:00Z',
  },
  {
    id: 'l10',
    participantId: 'p5',
    competitionId: '2',
    type: 'squat',
    weight: 330,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
    timestamp: '2023-11-28T14:45:00Z',
  },
  {
    id: 'l11',
    participantId: 'p5',
    competitionId: '2',
    type: 'bench',
    weight: 210,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
    timestamp: '2023-11-28T15:30:00Z',
  },
  {
    id: 'l12',
    participantId: 'p5',
    competitionId: '2',
    type: 'deadlift',
    weight: 350,
    success: true,
    videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4',
    timestamp: '2023-11-28T16:15:00Z',
  }
];

// Get competition by ID
export const getCompetitionById = (id: string): Competition | undefined => {
  return competitions.find(competition => competition.id === id);
};

// Get lifts by participant ID
export const getLiftsByParticipantId = (participantId: string) => {
  return sampleLifts.filter(lift => lift.participantId === participantId);
};

