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
    <div className="mb-20">
      <motion.div
        className="text-center mb-12"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <h2 className="text-3xl font-semibold mb-4">Top Lifts This Month</h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Celebrating the strongest performances across all competitions.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {categories.map((category, categoryIndex) => {
          const topLifters = getTopLifts(category.key);

          return (
            <motion.div
              key={category.key}
              className="glass p-6 rounded-lg"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: categoryIndex * 0.1 }}
            >
              <div className="flex items-center gap-3 mb-6">
                <span className="text-2xl">{category.icon}</span>
                <h3 className="text-xl font-semibold">{category.name}</h3>
              </div>

              <div className="space-y-4">
                {topLifters.map((lifter, index) => (
                  <motion.div
                    key={lifter.id}
                    className="flex items-center gap-4"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: categoryIndex * 0.1 + index * 0.1 }}
                  >
                    <div className="relative">
                      <img
                        src={lifter.avatar}
                        alt={lifter.name}
                        className="w-12 h-12 rounded-full"
                      />
                      <span className={`absolute -top-1 -right-1 w-6 h-6 flex items-center justify-center rounded-full text-sm font-bold ${
                        index === 0 ? 'bg-yellow-400' :
                        index === 1 ? 'bg-gray-300' :
                        'bg-amber-600'
                      } text-white`}>
                        {index + 1}
                      </span>
                    </div>
                    <div className="flex-1">
                      <h4 className="font-medium">{lifter.name}</h4>
                      <p className="text-sm text-muted-foreground">{lifter.weightClass} • {lifter.country}</p>
                    </div>
                    <div className="text-right">
                      <span className="font-bold text-lg">{lifter.bestLift}kg</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default TopLifts; 