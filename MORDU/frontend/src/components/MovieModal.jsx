import React from 'react';
import { X, Star, Info, TrendingUp } from 'lucide-react';

const MovieModal = ({ movie, onClose }) => {
  if (!movie) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4">
      {/* Fenêtre principale au style Néo-Brutaliste */}
      <div className="bg-white border-4 border-black shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] max-w-2xl w-full max-h-[90vh] overflow-y-auto relative">
        
        {/* Bouton Fermer */}
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 bg-red-500 border-2 border-black p-1 hover:bg-black hover:text-white transition-colors"
        >
          <X size={24} strokeWidth={3} />
        </button>

        {/* Header de la Modal */}
        <div className="p-8 border-b-4 border-black bg-yellow-300">
          <h2 className="text-5xl font-black uppercase tracking-tighter">{movie.title}</h2>
          <p className="text-xl font-bold italic mt-2">Studio: {movie.studio}</p>
        </div>

        <div className="p-8">
          <div className="bg-blue-100 border-3 border-black p-4 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Info size={20} strokeWidth={3} />
              <span className="font-black uppercase text-sm italic">Le mot du Mordu :</span>
            </div>
            <p className="font-bold leading-tight">
              {movie.insight}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-8">
            <div className="border-2 border-black p-3 flex items-center gap-3">
              <Star className="text-yellow-500" fill="currentColor" />
              <span className="font-black italic">Score Mood: 9.2</span>
            </div>
            <div className="border-2 border-black p-3 flex items-center gap-3">
              <TrendingUp className="text-green-600" />
              <span className="font-black italic">Hype Studio: Max</span>
            </div>
          </div>

          <button className="w-full bg-black text-white py-4 text-2xl font-black uppercase hover:bg-red-500 transition-colors shadow-[4px_4px_0px_0px_rgba(239,68,68,1)]">
            Miser sur ce film
          </button>
        </div>
      </div>
    </div>
  );
};

export default MovieModal;