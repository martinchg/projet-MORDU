import React, { useState, useEffect } from 'react';
import axios from 'axios';
import BentoCard from './components/BentoCard';
import MovieModal from './components/MovieModal';

function App() {
  const [movies, setMovies] = useState([]); // Liste vide au départ
  const [selectedMovie, setSelectedMovie] = useState(null);

  // Le "Câblage" : On appelle l'API au chargement
  useEffect(() => {
    const fetchMovies = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:8000/api/movies');
        setMovies(response.data);
      } catch (error) {
        console.error("Erreur de connexion au cerveau Python :", error);
      }
    };
    fetchMovies();
  }, []);

  return (
    <div className="min-h-screen bg-[#F0F0F0] p-8 font-mono">
      <header className="mb-12">
        <h1 className="text-7xl font-black uppercase bg-yellow-300 border-4 border-black px-4 shadow-brutal inline-block">
          MORDU
        </h1>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {movies.map((movie) => (
          <BentoCard 
            key={movie.id}
            title={movie.title} 
            subtitle={`Studio: ${movie.studio}`}
            content={movie.insight.substring(0, 60) + "..."}
            color={movie.color}
            onClick={() => setSelectedMovie(movie)}
            className="md:col-span-2"
          />
        ))}
      </div>

      <MovieModal 
        movie={selectedMovie} 
        onClose={() => setSelectedMovie(null)} 
      />
    </div>
  );
}

export default App;