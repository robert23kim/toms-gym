import React, { useState } from 'react';
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { getGhibliAvatar } from '../lib/api';

interface GhibliAvatarProps {
  id?: string | number;
  name?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const GhibliAvatar: React.FC<GhibliAvatarProps> = ({ 
  id = 'default', 
  name = '', 
  size = 'md',
  className = ''
}) => {
  const [imageError, setImageError] = useState(false);
  
  // Get initials from name
  const initials = name
    ? name
        .split(' ')
        .map(part => part[0])
        .join('')
        .toUpperCase()
        .substring(0, 2)
    : '?';

  // Determine avatar size
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24'
  };

  const sizeClass = sizeClasses[size] || sizeClasses.md;

  // Get avatar URL
  const avatarUrl = getGhibliAvatar(id);

  return (
    <Avatar className={`${sizeClass} ${className}`}>
      {!imageError && (
        <AvatarImage 
          src={avatarUrl} 
          alt={name || 'Avatar'} 
          onError={() => setImageError(true)}
        />
      )}
      <AvatarFallback
        className="bg-accent/10 text-accent font-medium"
      >
        {initials}
      </AvatarFallback>
    </Avatar>
  );
};

export default GhibliAvatar; 