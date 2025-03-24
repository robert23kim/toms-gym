import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';
import { Competition, CompetitionStatus } from '../lib/types';

interface CreateCompetitionProps {
  onClose: () => void;
  onSubmit: (competition: Omit<Competition, 'id' | 'participants'>) => void;
}

const CreateCompetition: React.FC<CreateCompetitionProps> = ({ onClose, onSubmit }) => {
  const [formData, setFormData] = useState({
    title: '',
    date: '',
    registrationDeadline: '',
    location: '',
    description: '',
    image: '',
    status: 'upcoming' as CompetitionStatus,
    categories: [] as string[],
  });

  const [category, setCategory] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleAddCategory = (e: React.FormEvent) => {
    e.preventDefault();
    if (category && !formData.categories.includes(category)) {
      setFormData(prev => ({
        ...prev,
        categories: [...prev.categories, category]
      }));
      setCategory('');
    }
  };

  const removeCategory = (categoryToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      categories: prev.categories.filter(c => c !== categoryToRemove)
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

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Title</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={e => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Competition title"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Location</label>
                <input
                  type="text"
                  required
                  value={formData.location}
                  onChange={e => setFormData(prev => ({ ...prev, location: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Competition location"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Competition Date</label>
                <input
                  type="date"
                  required
                  value={formData.date}
                  onChange={e => setFormData(prev => ({ ...prev, date: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Registration Deadline</label>
                <input
                  type="date"
                  required
                  value={formData.registrationDeadline}
                  onChange={e => setFormData(prev => ({ ...prev, registrationDeadline: e.target.value }))}
                  className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <textarea
                required
                value={formData.description}
                onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
                className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent min-h-[100px]"
                placeholder="Competition description"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Cover Image URL</label>
              <input
                type="url"
                required
                value={formData.image}
                onChange={e => setFormData(prev => ({ ...prev, image: e.target.value }))}
                className="w-full px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder="https://example.com/image.jpg"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Categories</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Add category"
                />
                <button
                  type="button"
                  onClick={handleAddCategory}
                  className="px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
                >
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {formData.categories.map(cat => (
                  <span
                    key={cat}
                    className="px-2 py-1 bg-secondary rounded-full text-sm flex items-center gap-1"
                  >
                    {cat}
                    <button
                      type="button"
                      onClick={() => removeCategory(cat)}
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