import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Participant } from '../lib/types';
import { Play } from 'lucide-react';
import { getTopLifts } from '../lib/api';

const TopLifts = () => {
  const [topLifts, setTopLifts] = useState<Record<string, any[]>>({
    squat: [],
    bench: [],
    deadlift: []
  });
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

  const categories = [
    { name: 'Squat', key: 'squat' as const, icon: '🏋️‍♂️' },
    { name: 'Bench Press', key: 'bench' as const, icon: '💪' },
    { name: 'Deadlift', key: 'deadlift' as const, icon: '🏋️‍♀️' }
  ];

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
                  {lifters.length > 0 ? (
                    lifters.map((lifter, index) => (
                      <Link
                        key={lifter.id}
                        to={`/challenges/${lifter.competitionId}`}
                      >
                        <motion.div
                          className="flex items-center gap-3 p-2 rounded-md hover:bg-secondary/50 transition-colors"
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.3, delay: categoryIndex * 0.1 + index * 0.1 }}
                        >
                          <div className="relative flex-shrink-0">
                            <img
                              src={lifter.avatar}
                              alt={lifter.name}
                              className="w-8 h-8 rounded-full"
                            />
                            <span className={`absolute -top-1 -right-1 w-4 h-4 flex items-center justify-center rounded-full text-xs font-bold ${
                              index === 0 ? 'bg-yellow-400' :
                              index === 1 ? 'bg-gray-300' :
                              'bg-amber-600'
                            } text-white`}>
                              {index + 1}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-sm truncate">{lifter.name}</h4>
                            <p className="text-xs text-muted-foreground">{lifter.weightClass}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm">{lifter.bestLift}kg</span>
                            <Play className="w-4 h-4 text-muted-foreground" />
                          </div>
                        </motion.div>
                      </Link>
                    ))
                  ) : (
                    <div className="text-center py-2 text-sm text-muted-foreground">
                      No {category.name.toLowerCase()} records found
                    </div>
                  )}
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