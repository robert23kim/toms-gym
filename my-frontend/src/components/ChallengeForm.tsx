import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { API_URL } from "../config";  // Import the API_URL from config

interface ChallengeFormProps {
  onSuccess: (challenge: any) => void;
  onCancel: () => void;
}

const ChallengeForm: React.FC<ChallengeFormProps> = ({ onSuccess, onCancel }) => {
  const navigate = useNavigate();
  // Get current date and time for default values
  const now = new Date();
  const defaultStartDate = new Date(now.getTime() + 24 * 60 * 60 * 1000); // Tomorrow
  const defaultEndDate = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000); // 7 days from now

  const [formData, setFormData] = useState({
    name: "New Powerlifting Challenge",
    location: "Powerlifting Gym",
    lifttypes: ["Squat", "Bench Press", "Deadlift"],
    weightclasses: ["83kg", "93kg", "105kg"],
    gender: "M",
    start_date: defaultStartDate.toISOString().slice(0, 16),
    end_date: defaultEndDate.toISOString().slice(0, 16),
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const liftTypeOptions = [
    "Squat",
    "Bench Press",
    "Deadlift",
    "Clean & Jerk",
    "Snatch",
    "Power Clean",
    "Push Press",
    "Overhead Press",
  ];

  const weightClassOptions = [
    "59kg",
    "66kg",
    "74kg",
    "83kg",
    "93kg",
    "105kg",
    "120kg",
    "120kg+",
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    try {
      // Transform the data to match backend expectations
      const backendData = {
        name: formData.name,
        location: formData.location,
        lifttypes: formData.lifttypes,
        weightclasses: formData.weightclasses,
        gender: formData.gender,
        start_date: formData.start_date,
        end_date: formData.end_date,
      };

      console.log('Sending data to backend:', backendData); // Debug log

      const response = await axios.post(
        `${API_URL}/create_competition`,
        backendData,
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      // Transform the response data to match our frontend Challenge type
      const transformedData = {
        id: response.data.competition_id,
        title: response.data.name,
        date: response.data.start_date,
        registrationDeadline: response.data.end_date,
        location: response.data.location,
        description: response.data.description || "",
        status: "upcoming",
        categories: response.data.lifttypes,
        participants: 0,
        prizePool: response.data.prize_pool || 0,
      };

      onSuccess(transformedData);
      // Navigate to the challenge detail page
      navigate(`/challenges/${response.data.competition_id}`);
    } catch (error: any) {
      console.error("Error creating challenge:", error);
      setErrors({
        submit: error.response?.data?.error || "Failed to create challenge. Please try again.",
      });
    }
  };

  const handleLiftTypeToggle = (type: string) => {
    setFormData((prev) => ({
      ...prev,
      lifttypes: prev.lifttypes.includes(type)
        ? prev.lifttypes.filter((t) => t !== type)
        : [...prev.lifttypes, type],
    }));
  };

  const handleWeightClassToggle = (weightClass: string) => {
    setFormData((prev) => ({
      ...prev,
      weightclasses: prev.weightclasses.includes(weightClass)
        ? prev.weightclasses.filter((w) => w !== weightClass)
        : [...prev.weightclasses, weightClass],
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium mb-2">Challenge Name</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          className="w-full px-4 py-2 rounded-lg border bg-background"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Location</label>
        <input
          type="text"
          value={formData.location}
          onChange={(e) => setFormData({ ...formData, location: e.target.value })}
          className="w-full px-4 py-2 rounded-lg border bg-background"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Lift Types</label>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {liftTypeOptions.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => handleLiftTypeToggle(type)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                formData.lifttypes.includes(type)
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary/5 hover:bg-secondary/10"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
        {formData.lifttypes.length === 0 && (
          <p className="text-sm text-red-500 mt-1">Please select at least one lift type</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Weight Classes</label>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {weightClassOptions.map((weightClass) => (
            <button
              key={weightClass}
              type="button"
              onClick={() => handleWeightClassToggle(weightClass)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                formData.weightclasses.includes(weightClass)
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary/5 hover:bg-secondary/10"
              }`}
            >
              {weightClass}
            </button>
          ))}
        </div>
        {formData.weightclasses.length === 0 && (
          <p className="text-sm text-red-500 mt-1">Please select at least one weight class</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Gender</label>
        <select
          value={formData.gender}
          onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
          className="w-full px-4 py-2 rounded-lg border bg-background"
        >
          <option value="M">Men</option>
          <option value="F">Women</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Start Date</label>
          <input
            type="datetime-local"
            value={formData.start_date}
            onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
            className="w-full px-4 py-2 rounded-lg border bg-background"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">End Date</label>
          <input
            type="datetime-local"
            value={formData.end_date}
            onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
            className="w-full px-4 py-2 rounded-lg border bg-background"
            required
          />
        </div>
      </div>

      {errors.submit && (
        <p className="text-sm text-red-500">{errors.submit}</p>
      )}

      <div className="flex justify-end gap-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-lg bg-secondary/5 hover:bg-secondary/10"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
        >
          Create Challenge
        </button>
      </div>
    </form>
  );
};

export default ChallengeForm; 