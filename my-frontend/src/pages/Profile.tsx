import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import Layout from "../components/Layout";
import { Calendar, MapPin, Trophy, Activity, Award, ArrowLeft, Users, BarChart2, User, Dumbbell } from "lucide-react";

// Mock data
const mockProfile = {
  user: {
    userid: 1,
    name: "John Smith",
    email: "john.smith@example.com",
    gender: "M"
  },
  competitions: [
    {
      id: 1,
      name: "Summer Powerlifting Championship 2024",
      start_date: "2024-06-15",
      end_date: "2024-06-16",
      location: "New York, NY",
      weight_class: "93kg",
      status: "completed",
      total_weight: 750,
      successful_lifts: 8
    },
    {
      id: 2,
      name: "Spring Open 2024",
      start_date: "2024-03-20",
      end_date: "2024-03-21",
      location: "Los Angeles, CA",
      weight_class: "93kg",
      status: "upcoming",
      total_weight: 0,
      successful_lifts: 0
    },
    {
      id: 3,
      name: "Winter Classic 2023",
      start_date: "2023-12-10",
      end_date: "2023-12-11",
      location: "Chicago, IL",
      weight_class: "93kg",
      status: "completed",
      total_weight: 725,
      successful_lifts: 7
    }
  ],
  best_lifts: [
    {
      type: "Squat",
      best_weight: 280,
      competition_name: "Summer Powerlifting Championship 2024",
      competition_id: 1
    },
    {
      type: "Bench Press",
      best_weight: 180,
      competition_name: "Summer Powerlifting Championship 2024",
      competition_id: 1
    },
    {
      type: "Deadlift",
      best_weight: 290,
      competition_name: "Summer Powerlifting Championship 2024",
      competition_id: 1
    }
  ],
  achievements: {
    total_competitions: 3,
    total_successful_lifts: 15,
    heaviest_lift: 290,
    best_squat: 280,
    best_bench: 180,
    best_deadlift: 290
  },
  joinDate: "January 2024",
  location: "New York, USA",
  stats: {
    competitions: 5,
    wins: 2,
    totalLifts: 150,
    personalBests: {
      squat: "225kg",
      bench: "180kg",
      deadlift: "280kg"
    }
  },
  recentActivity: [
    {
      date: "2024-03-15",
      type: "Competition",
      name: "Spring Powerlifting Meet",
      result: "1st Place"
    },
    {
      date: "2024-03-10",
      type: "Training",
      name: "Heavy Squat Day",
      result: "New PR: 230kg"
    },
    {
      date: "2024-03-05",
      type: "Competition",
      name: "Winter Classic",
      result: "2nd Place"
    }
  ]
};

const Profile = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const profile = mockProfile; // Use mock data instead of state

  const formatDate = (dateString: string) => {
    const options: Intl.DateTimeFormatOptions = {
      year: "numeric",
      month: "long",
      day: "numeric",
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

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
            <div className="w-24 h-24 rounded-full bg-accent/10 flex items-center justify-center">
              <User size={48} className="text-accent" />
            </div>
            <div>
              <h1 className="text-3xl font-bold mb-2">{profile.user.name}</h1>
              <p className="text-muted-foreground">{profile.user.email}</p>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar size={18} />
              <span>Joined {profile.joinDate}</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <MapPin size={18} />
              <span>{profile.location}</span>
            </div>
          </div>
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Trophy className="text-accent" size={24} />
              <h2 className="text-xl font-semibold">Competition Stats</h2>
            </div>
            <div className="space-y-2">
              <p>Total Competitions: {profile.stats.competitions}</p>
              <p>Wins: {profile.stats.wins}</p>
            </div>
          </div>
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Dumbbell className="text-accent" size={24} />
              <h2 className="text-xl font-semibold">Personal Bests</h2>
            </div>
            <div className="space-y-2">
              <p>Squat: {profile.stats.personalBests.squat}</p>
              <p>Bench: {profile.stats.personalBests.bench}</p>
              <p>Deadlift: {profile.stats.personalBests.deadlift}</p>
            </div>
          </div>
          <div className="bg-card rounded-xl p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <Dumbbell className="text-accent" size={24} />
              <h2 className="text-xl font-semibold">Activity</h2>
            </div>
            <div className="space-y-2">
              <p>Total Lifts: {profile.stats.totalLifts}</p>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-card rounded-xl p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
          <div className="space-y-4">
            {profile.recentActivity.map((activity, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 bg-background rounded-lg"
              >
                <div>
                  <p className="font-medium">{activity.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {activity.type} • {activity.date}
                  </p>
                </div>
                <span className="text-accent font-medium">{activity.result}</span>
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </Layout>
  );
};

export default Profile; 