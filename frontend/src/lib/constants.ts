export const APP_NAME = "Tom's Gym";

export const NAV_LINKS = [
  { label: "Home", href: "/" },
  { label: "Challenges", href: "/challenges" },
  { label: "Athletes", href: "/athletes" },
  { label: "Leaderboard", href: "/leaderboard" },
  { label: "Store", href: "/store" },
  { label: "About", href: "/about" },
] as const;

export const CHALLENGE_CATEGORIES = [
  { id: "all", name: "All Challenges" },
  { id: "upcoming", name: "Upcoming" },
  { id: "ongoing", name: "Ongoing" },
  { id: "completed", name: "Completed" },
] as const;

export const LIFT_TYPES = [
  "Squat",
  "Bench Press",
  "Deadlift",
] as const;

export const WEIGHT_CLASSES = [
  "59kg",
  "66kg",
  "74kg",
  "83kg",
  "93kg",
  "105kg",
  "120kg",
  "120kg+",
] as const;

export const GENDER_OPTIONS = [
  { value: "M", label: "Men" },
  { value: "F", label: "Women" },
] as const;

export const DEFAULT_PRIZE_POOL = {
  first: 1000,
  second: 500,
  third: 250,
  total: 1750,
} as const; 