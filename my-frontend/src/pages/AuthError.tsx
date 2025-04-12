import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const AuthError: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const errorMessage = searchParams.get('error') || 'Unknown authentication error';

  useEffect(() => {
    // Auto-redirect to home after 5 seconds
    const timer = setTimeout(() => {
      navigate('/');
    }, 5000);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-b from-background to-secondary/20">
      <div className="bg-background p-8 rounded-lg shadow-lg max-w-md w-full border border-border/50">
        <div className="text-center">
          <div className="flex justify-center mb-6">
            <div className="rounded-full bg-red-100 p-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">Authentication Failed</h2>
          <p className="text-muted-foreground mb-6">{errorMessage}</p>
          <div className="mb-6 h-1 w-full bg-border/30 rounded-full overflow-hidden">
            <div className="h-full bg-red-500 animate-shrink rounded-full" style={{ 
              animation: 'shrink 5s linear forwards',
            }}></div>
          </div>
          <p className="text-sm text-muted-foreground">You will be redirected to the home page in 5 seconds.</p>
          <button 
            onClick={() => navigate('/')} 
            className="mt-4 px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors w-full"
          >
            Return to Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthError;

// Add this to your global CSS or a component-specific CSS
// @keyframes shrink {
//   from { width: 100%; }
//   to { width: 0%; }
// } 