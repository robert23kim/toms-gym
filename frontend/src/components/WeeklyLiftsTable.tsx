import React, { useState } from 'react';
import { Plus, Trash2, Check, X } from 'lucide-react';

interface WeekData {
  week_start_date: string;
  label: string;
  lifts: Record<string, number>;
  lift_ids: Record<string, string>;
  total: number;
}

interface WeeklyLiftsTableProps {
  weeks: WeekData[];
  onAddWeek: (date: string) => void;
  onUpdateLift: (weekDate: string, liftType: string, weight: number) => void;
  onDeleteLift: (liftId: string) => void;
  isLoading?: boolean;
}

const LIFT_TYPES = [
  { key: 'bench', label: 'Bench Press' },
  { key: 'squat', label: 'Squat' },
  { key: 'deadlift', label: 'Deadlift' },
  { key: 'sitting_press', label: 'Sitting Press' },
];

const WeeklyLiftsTable: React.FC<WeeklyLiftsTableProps> = ({
  weeks,
  onAddWeek,
  onUpdateLift,
  onDeleteLift,
  isLoading = false,
}) => {
  const [editingCell, setEditingCell] = useState<{ weekDate: string; liftType: string } | null>(null);
  const [editValue, setEditValue] = useState('');
  const [showAddWeek, setShowAddWeek] = useState(false);
  const [newWeekDate, setNewWeekDate] = useState('');

  const handleCellClick = (weekDate: string, liftType: string, currentValue?: number) => {
    setEditingCell({ weekDate, liftType });
    setEditValue(currentValue?.toString() || '');
  };

  const handleSaveEdit = () => {
    if (editingCell && editValue) {
      const weight = parseFloat(editValue);
      if (!isNaN(weight) && weight >= 0) {
        onUpdateLift(editingCell.weekDate, editingCell.liftType, weight);
      }
    }
    setEditingCell(null);
    setEditValue('');
  };

  const handleCancelEdit = () => {
    setEditingCell(null);
    setEditValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  const handleAddWeek = () => {
    if (newWeekDate) {
      onAddWeek(newWeekDate);
      setNewWeekDate('');
      setShowAddWeek(false);
    }
  };

  // Get the Monday of the current week as the default for new weeks
  const getDefaultWeekDate = () => {
    const today = new Date();
    const day = today.getDay();
    const diff = today.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(today.setDate(diff));
    return monday.toISOString().split('T')[0];
  };

  // Sort weeks by date (oldest first, so newer weeks appear on the right)
  const sortedWeeks = [...weeks].sort((a, b) =>
    new Date(a.week_start_date).getTime() - new Date(b.week_start_date).getTime()
  );

  return (
    <div className="bg-card rounded-xl p-4 shadow-sm overflow-x-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Weekly Max Lifts (lbs)</h3>
        {!showAddWeek ? (
          <button
            onClick={() => {
              setNewWeekDate(getDefaultWeekDate());
              setShowAddWeek(true);
            }}
            className="flex items-center gap-1 px-3 py-1.5 bg-accent text-white rounded-lg hover:bg-accent/90 text-sm"
          >
            <Plus size={16} />
            Add Week
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={newWeekDate}
              onChange={(e) => setNewWeekDate(e.target.value)}
              className="px-2 py-1 border rounded text-sm bg-background"
            />
            <button
              onClick={handleAddWeek}
              className="p-1.5 bg-green-500 text-white rounded hover:bg-green-600"
            >
              <Check size={14} />
            </button>
            <button
              onClick={() => setShowAddWeek(false)}
              className="p-1.5 bg-gray-400 text-white rounded hover:bg-gray-500"
            >
              <X size={14} />
            </button>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
        </div>
      ) : sortedWeeks.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p>No weekly lifts recorded yet.</p>
          <p className="text-sm mt-1">Click "Add Week" to start tracking your progress!</p>
        </div>
      ) : (
        <div className="min-w-[500px]">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-3 font-medium text-muted-foreground">Lift</th>
                {sortedWeeks.map((week) => (
                  <th key={week.week_start_date} className="text-center py-2 px-3 font-medium">
                    <div className="text-sm">{week.label}</div>
                    <div className="text-xs text-muted-foreground">{week.week_start_date}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {LIFT_TYPES.map((lift) => (
                <tr key={lift.key} className="border-b border-border/50 hover:bg-secondary/30">
                  <td className="py-3 px-3 font-medium">{lift.label}</td>
                  {sortedWeeks.map((week) => {
                    const isEditing = editingCell?.weekDate === week.week_start_date && editingCell?.liftType === lift.key;
                    const weight = week.lifts[lift.key];
                    const liftId = week.lift_ids[lift.key];

                    return (
                      <td key={`${week.week_start_date}-${lift.key}`} className="py-2 px-3 text-center">
                        {isEditing ? (
                          <div className="flex items-center justify-center gap-1">
                            <input
                              type="number"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onKeyDown={handleKeyDown}
                              className="w-20 px-2 py-1 border rounded text-center text-sm bg-background"
                              autoFocus
                              min="0"
                              step="0.5"
                            />
                            <button
                              onClick={handleSaveEdit}
                              className="p-1 text-green-500 hover:bg-green-100 rounded"
                            >
                              <Check size={14} />
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="p-1 text-gray-500 hover:bg-gray-100 rounded"
                            >
                              <X size={14} />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-center gap-1 group">
                            <button
                              onClick={() => handleCellClick(week.week_start_date, lift.key, weight)}
                              className="min-w-[60px] py-1 px-2 rounded hover:bg-secondary transition-colors"
                            >
                              {weight !== undefined ? (
                                <span className="font-semibold">{weight}</span>
                              ) : (
                                <span className="text-muted-foreground text-sm">--</span>
                              )}
                            </button>
                            {liftId && (
                              <button
                                onClick={() => onDeleteLift(liftId)}
                                className="p-1 text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Delete this entry"
                              >
                                <Trash2 size={12} />
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
              {/* Totals row */}
              <tr className="bg-secondary/50 font-semibold">
                <td className="py-3 px-3">Total</td>
                {sortedWeeks.map((week) => (
                  <td key={`total-${week.week_start_date}`} className="py-3 px-3 text-center">
                    {week.total > 0 ? week.total : '--'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default WeeklyLiftsTable;
