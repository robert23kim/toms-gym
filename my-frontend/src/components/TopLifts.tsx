import React from 'react';
import { motion } from 'framer-motion';
import { competitions } from '../lib/data';
import { Participant } from '../lib/types';

const TopLifts = () => {
  // Get all participants
  const allParticipants = competitions.flatMap(c => c.participants);

  // Get top lifts for each category
  const getTopLifts = (category: 'squat' | 'bench' | 'deadlift') => {
    return allParticipants
      .map(participant => ({
        ...participant,
        bestLift: participant.attempts?.[category]?.reduce((max, current) => Math.max(max, current), 0) || 0
      }))
      .sort((a, b) => b.bestLift - a.bestLift)
      .slice(0, 3);
  };

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

      <div className="divide-y divide-border/40">
        {categories.map((category, categoryIndex) => {
          const topLifters = getTopLifts(category.key);

          return (
            <div key={category.key} className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{category.icon}</span>
                <h3 className="font-medium">{category.name}</h3>
              </div>

              <div className="space-y-3">
                {topLifters.map((lifter, index) => (
                  <motion.div
                    key={lifter.id}
                    className="flex items-center gap-3"
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
                    <div className="text-right">
                      <span className="font-bold text-sm">{lifter.bestLift}kg</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
};

export default TopLifts; 