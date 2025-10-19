import React from 'react';
import { Loader2 } from 'lucide-react';

const Loading = ({ message = 'Loading...' }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <Loader2 className="w-8 h-8 animate-spin text-primary-600 mb-2" />
      <p className="text-gray-600">{message}</p>
    </div>
  );
};

export default Loading;