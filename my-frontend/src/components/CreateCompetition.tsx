import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import { Competition, CompetitionStatus } from '../lib/types';
import axios from 'axios';

interface CreateCompetitionProps {
  onClose: () => void;
  onSubmit: (competition: Omit<Competition, 'id' | 'participants'>) => void;
}

const CreateCompetition: React.FC<CreateCompetitionProps> = ({ onClose, onSubmit }) => {
  const [formData, setFormData] = useState({
    name: '',
    location: '',
    lifttypes: ['Squat', 'Bench Press', 'Deadlift'],
    weightclasses: ['59kg', '66kg', '74kg', '83kg', '93kg', '105kg', '120kg', '120kg+'],
    gender: 'M',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 7 days from now
  });

  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      console.log('Sending competition data:', formData);
      const response = await axios.post('https://my-app-834341357827.us-east1.run.app/create_competition', formData, {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });
      console.log('API Response:', response.data);
      setMessage('Competition created successfully!');
      setError('');
      onSubmit({
        title: formData.name,
        date: formData.start_date,
        registrationDeadline: formData.end_date,
        location: formData.location,
        description: `Competition for ${formData.gender} athletes with ${formData.lifttypes.join(', ')} lifts and ${formData.weightclasses.join(', ')} weight classes`,
        image: '',
        status: 'upcoming' as CompetitionStatus,
        categories: [...formData.lifttypes, ...formData.weightclasses],
        prizePool: {
          first: 1000,
          second: 500,
          third: 250,
          total: 1750
        }
      });
      onClose();
    } catch (err) {
      console.error('Error creating competition:', err);
      if (axios.isAxiosError(err)) {
        setError(`Failed to create competition: ${err.response?.data?.error || err.message}`);
      } else {
        setError('Failed to create competition. Please try again.');
      }
      setMessage('');
    }
  };

  const handleAddLiftType = (e: React.FormEvent) => {
    e.preventDefault();
    const input = e.target as HTMLFormElement;
    const liftType = (input.elements.namedItem('liftType') as HTMLInputElement).value;
    if (liftType && !formData.lifttypes.includes(liftType)) {
      setFormData(prev => ({
        ...prev,
        lifttypes: [...prev.lifttypes, liftType]
      }));
      (input.elements.namedItem('liftType') as HTMLInputElement).value = '';
    }
  };

  const handleAddWeightClass = (e: React.FormEvent) => {
    e.preventDefault();
    const input = e.target as HTMLFormElement;
    const weightClass = (input.elements.namedItem('weightClass') as HTMLInputElement).value;
    if (weightClass && !formData.weightclasses.includes(weightClass)) {
      setFormData(prev => ({
        ...prev,
        weightclasses: [...prev.weightclasses, weightClass]
      }));
      (input.elements.namedItem('weightClass') as HTMLInputElement).value = '';
    }
  };

  const removeLiftType = (liftType: string) => {
    setFormData(prev => ({
      ...prev,
      lifttypes: prev.lifttypes.filter(l => l !== liftType)
    }));
  };

  const removeWeightClass = (weightClass: string) => {
    setFormData(prev => ({
      ...prev,
      weightclasses: prev.weightclasses.filter(w => w !== weightClass)
    }));
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0.95 }}
        className="bg-background rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold">Create New Competition</h2>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <X size={24} />
            </button>
          </div>

          {message && <div className="bg-green-100 text-green-700 p-3 rounded mb-4">{message}</div>}
          {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Name</label>
                <input
                  type="text"
                  name="name"
                  required
                  value={formData.name}
                  onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Competition name"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Location</label>
                <input
                  type="text"
                  name="location"
                  required
                  value={formData.location}
                  onChange={e => setFormData(prev => ({ ...prev, location: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Competition location"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Gender</label>
                <select
                  name="gender"
                  required
                  value={formData.gender}
                  onChange={e => setFormData(prev => ({ ...prev, gender: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  <option value="">Select gender</option>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                  <option value="X">Mixed</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Start Date</label>
                <input
                  type="date"
                  name="start_date"
                  required
                  value={formData.start_date}
                  onChange={e => setFormData(prev => ({ ...prev, start_date: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">End Date</label>
                <input
                  type="date"
                  name="end_date"
                  required
                  value={formData.end_date}
                  onChange={e => setFormData(prev => ({ ...prev, end_date: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Lift Types</label>
              <form onSubmit={handleAddLiftType} className="flex gap-2">
                <input
                  type="text"
                  name="liftType"
                  className="flex-1 px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Add lift type"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
                >
                  Add
                </button>
              </form>
              <div className="flex flex-wrap gap-2 mt-2">
                {formData.lifttypes.map(liftType => (
                  <span
                    key={liftType}
                    className="px-2 py-1 bg-secondary rounded-full text-sm flex items-center gap-1"
                  >
                    {liftType}
                    <button
                      type="button"
                      onClick={() => removeLiftType(liftType)}
                      className="hover:text-accent"
                    >
                      <X size={14} />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Weight Classes</label>
              <form onSubmit={handleAddWeightClass} className="flex gap-2">
                <input
                  type="text"
                  name="weightClass"
                  className="flex-1 px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Add weight class"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
                >
                  Add
                </button>
              </form>
              <div className="flex flex-wrap gap-2 mt-2">
                {formData.weightclasses.map(weightClass => (
                  <span
                    key={weightClass}
                    className="px-2 py-1 bg-secondary rounded-full text-sm flex items-center gap-1"
                  >
                    {weightClass}
                    <button
                      type="button"
                      onClick={() => removeWeightClass(weightClass)}
                      className="hover:text-accent"
                    >
                      <X size={14} />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-4 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-border rounded-md hover:bg-secondary transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
              >
                Create Competition
              </button>
            </div>
          </form>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CreateCompetition; 