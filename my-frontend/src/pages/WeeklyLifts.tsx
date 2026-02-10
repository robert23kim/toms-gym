import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, TrendingUp } from 'lucide-react';
import axios from 'axios';
import Layout from '../components/Layout';
import WeeklyLiftsTable from '../components/WeeklyLiftsTable';
import WeeklyLiftsChart from '../components/WeeklyLiftsChart';
import { API_URL } from '../config';

interface WeekData {
  week_start_date: string;
  label: string;
  lifts: Record<string, number>;
  lift_ids: Record<string, string>;
  total: number;
}

const WeeklyLifts: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [weeks, setWeeks] = useState<WeekData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userName, setUserName] = useState<string>('');

  // Use the id from URL params or localStorage
  const userId = id || localStorage.getItem('userId');

  const fetchWeeklyLifts = useCallback(async () => {
    if (!userId) return;

    try {
      setLoading(true);
      setError(null);

      const response = await axios.get(`${API_URL}/users/${userId}/weekly-lifts`);
      setWeeks(response.data.weeks || []);
    } catch (err: any) {
      console.error('Error fetching weekly lifts:', err);
      setError(err.response?.data?.error || 'Failed to load weekly lifts');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const fetchUserName = useCallback(async () => {
    if (!userId) return;

    try {
      const response = await axios.get(`${API_URL}/users/${userId}/profile`);
      setUserName(response.data.user?.name || '');
    } catch (err) {
      console.error('Error fetching user name:', err);
    }
  }, [userId]);

  useEffect(() => {
    if (userId) {
      fetchWeeklyLifts();
      fetchUserName();
    }
  }, [userId, fetchWeeklyLifts, fetchUserName]);

  const handleAddWeek = async (date: string) => {
    if (!userId) return;

    // Adding a week just means we'll be ready to add lifts for that week
    // The actual entries are created when the user enters weights
    // For now, we'll create a placeholder by adding one lift type
    try {
      await axios.post(`${API_URL}/users/${userId}/weekly-lifts`, {
        week_start_date: date,
        lift_type: 'bench',
        weight_lbs: 0,
      });
      await fetchWeeklyLifts();
    } catch (err: any) {
      console.error('Error adding week:', err);
      setError(err.response?.data?.error || 'Failed to add week');
    }
  };

  const handleUpdateLift = async (weekDate: string, liftType: string, weight: number) => {
    if (!userId) return;

    try {
      await axios.post(`${API_URL}/users/${userId}/weekly-lifts`, {
        week_start_date: weekDate,
        lift_type: liftType,
        weight_lbs: weight,
      });
      await fetchWeeklyLifts();
    } catch (err: any) {
      console.error('Error updating lift:', err);
      setError(err.response?.data?.error || 'Failed to update lift');
    }
  };

  const handleDeleteLift = async (liftId: string) => {
    if (!userId) return;

    try {
      await axios.delete(`${API_URL}/users/${userId}/weekly-lifts/${liftId}`);
      await fetchWeeklyLifts();
    } catch (err: any) {
      console.error('Error deleting lift:', err);
      setError(err.response?.data?.error || 'Failed to delete lift');
    }
  };

  if (!userId) {
    return (
      <Layout>
        <div className="flex flex-col justify-center items-center h-[60vh]">
          <p className="text-muted-foreground mb-4">No user profile found</p>
          <button
            onClick={() => navigate('/upload')}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Upload a Video to Create Profile
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mb-6 flex items-center">
        <button
          onClick={() => navigate(`/profile/${userId}`)}
          className="mr-4 flex items-center text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={16} className="mr-1" /> Back to Profile
        </button>
        <div className="flex items-center gap-2">
          <TrendingUp className="text-accent" size={24} />
          <h1 className="text-2xl font-semibold">Weekly Max Lifts</h1>
        </div>
      </div>

      {userName && (
        <p className="text-muted-foreground mb-6">Tracking progress for {userName}</p>
      )}

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
          {error}
          <button
            onClick={() => setError(null)}
            className="float-right font-bold"
          >
            &times;
          </button>
        </div>
      )}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-6xl mx-auto space-y-6"
      >
        <WeeklyLiftsTable
          weeks={weeks}
          onAddWeek={handleAddWeek}
          onUpdateLift={handleUpdateLift}
          onDeleteLift={handleDeleteLift}
          isLoading={loading}
        />

        <WeeklyLiftsChart weeks={weeks} />
      </motion.div>
    </Layout>
  );
};

export default WeeklyLifts;
