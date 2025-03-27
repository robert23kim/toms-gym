import React, { useState } from 'react';
import axios from 'axios';

interface CompetitionFormData {
  name: string;
  location: string;
  lifttypes: string[];
  weightclasses: string[];
  gender: string;
  start_date: string;
  end_date: string;
}

const CompetitionForm: React.FC = () => {
  const [formData, setFormData] = useState<CompetitionFormData>({
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
      // Reset form
      setFormData({
        name: '',
        location: '',
        lifttypes: ['Squat', 'Bench Press', 'Deadlift'],
        weightclasses: ['59kg', '66kg', '74kg', '83kg', '93kg', '105kg', '120kg', '120kg+'],
        gender: 'M',
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 7 days from now
      });
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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6">Create New Competition</h2>
      
      {message && <div className="bg-green-100 text-green-700 p-3 rounded mb-4">{message}</div>}
      {error && <div className="bg-red-100 text-red-700 p-3 rounded mb-4">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Name</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Location</label>
          <input
            type="text"
            name="location"
            value={formData.location}
            onChange={handleChange}
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Gender</label>
          <select
            name="gender"
            value={formData.gender}
            onChange={handleChange}
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="">Select gender</option>
            <option value="M">Male</option>
            <option value="F">Female</option>
            <option value="X">Mixed</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Start Date</label>
          <input
            type="date"
            name="start_date"
            value={formData.start_date}
            onChange={handleChange}
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">End Date</label>
          <input
            type="date"
            name="end_date"
            value={formData.end_date}
            onChange={handleChange}
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Lift Types</label>
          <input
            type="text"
            name="lifttypes"
            value={formData.lifttypes.join(', ')}
            onChange={(e) => setFormData(prev => ({
              ...prev,
              lifttypes: e.target.value.split(',').map(item => item.trim())
            }))}
            placeholder="Enter lift types separated by commas"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Weight Classes</label>
          <input
            type="text"
            name="weightclasses"
            value={formData.weightclasses.join(', ')}
            onChange={(e) => setFormData(prev => ({
              ...prev,
              weightclasses: e.target.value.split(',').map(item => item.trim())
            }))}
            placeholder="Enter weight classes separated by commas"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>

        <button
          type="submit"
          className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Create Competition
        </button>
      </form>
    </div>
  );
};

export default CompetitionForm; 