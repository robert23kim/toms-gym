import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import ChallengeForm from "./ChallengeForm";

interface CreateChallengeProps {
  onClose: () => void;
  onChallengeCreated: (newChallenge: any) => void;
}

const CreateChallenge: React.FC<CreateChallengeProps> = ({ onClose, onChallengeCreated }) => {
  const [isOpen, setIsOpen] = useState(true);

  const handleClose = () => {
    setIsOpen(false);
    setTimeout(onClose, 300);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-50"
            onClick={handleClose}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="w-full max-w-2xl bg-background rounded-lg shadow-xl overflow-hidden"
            >
              <div className="flex items-center justify-between p-6 border-b">
                <h2 className="text-2xl font-bold">Create New Challenge</h2>
                <button
                  onClick={handleClose}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X size={24} />
                </button>
              </div>
              <div className="p-6 max-h-[80vh] overflow-y-auto">
                <ChallengeForm
                  onSuccess={(newChallenge) => {
                    onChallengeCreated(newChallenge);
                    handleClose();
                  }}
                  onCancel={handleClose}
                />
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};

export default CreateChallenge; 