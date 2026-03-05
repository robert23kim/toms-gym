import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Participant } from '../lib/types';
import { Play } from 'lucide-react';
import { getTopLifts } from '../lib/api';
import GhibliAvatar from './GhibliAvatar';

// Category display configuration
const categoryConfig: Record<string, { name: string; icon: string }> = {
  squat: { name: 'Squat', icon: '🏋️‍♂️' },
  bench: { name: 'Bench Press', icon: '💪' },
  deadlift: { name: 'Deadlift', icon: '🏋️‍♀️' },
  curl: { name: 'Bicep Curl', icon: '💪' },
  snatch: { name: 'Snatch', icon: '🏋️' },
  clean: { name: 'Clean', icon: '🏋️' }
};

const TopLifts = () => {
  const [topLifts, setTopLifts] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTopLifts = async () => {
      try {
        setLoading(true);
        const lifts = await getTopLifts();
        setTopLifts(lifts);
      } catch (error) {
        console.error('Error fetching top lifts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTopLifts();
  }, []);

  // Get categories that have lifts, with proper display names
  const categories = Object.keys(topLifts).map(key => ({
    key,
    name: categoryConfig[key]?.name || key.charAt(0).toUpperCase() + key.slice(1),
    icon: categoryConfig[key]?.icon || '🏋️'
  }));

  return (
    <motion.div
      className="glass rounded-lg overflow-hidden"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <div className="p-4 border-b border-border/40">
        <h2 className="text-xl font-semibold">Top Lifts This Month</h2>
      </div>

      {loading ? (
        <div className="p-8 text-center">
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">Loading top lifts...</p>
        </div>
      ) : categories.length === 0 ? (
        <div className="p-8 text-center">
          <p className="text-sm text-muted-foreground">No lifts recorded yet this month</p>
        </div>
      ) : (
        <div className="divide-y divide-border/40">
          {categories.map((category, categoryIndex) => {
            const lifters = topLifts[category.key] || [];

            return (
              <div key={category.key} className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xl">{category.icon}</span>
                  <h3 className="font-medium">{category.name}</h3>
                </div>

                <div className="space-y-3">
                  {lifters.map((lifter, index) => (
                    <Link
                      key={`${lifter.id}-${lifter.liftId}`}
                      to={`/challenges/${lifter.competitionId}/participants/${lifter.id}/video/${lifter.liftId}`}
                    >
                      <motion.div
                        className="flex items-center gap-3 p-2 rounded-md hover:bg-secondary/50 transition-colors"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: categoryIndex * 0.1 + index * 0.1 }}
                      >
                        <div className="relative flex-shrink-0">
                          <GhibliAvatar
                            id={lifter.id}
                            name={lifter.name}
                            size="sm"
                            className="relative"
                          />
                          <span className={`absolute -top-1 -right-1 w-4 h-4 flex items-center justify-center rounded-full text-xs font-bold ${
                            index === 0 ? 'bg-yellow-400' :
                            index === 1 ? 'bg-gray-300' :
                            'bg-amber-600'
                          } text-white z-10`}>
                            {index + 1}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-sm truncate">{lifter.name}</h4>
                          <p className="text-xs text-muted-foreground">{lifter.weightClass}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm">{lifter.bestLift}kg</span>
                          <Play className="w-4 h-4 text-accent" />
                        </div>
                      </motion.div>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
};

export default TopLifts; 