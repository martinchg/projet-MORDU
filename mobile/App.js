import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View, ScrollView, Text, SafeAreaView } from 'react-native';
import { useState } from 'react';
import MovieCard from './components/MovieCard';
import MovieModal from './components/MovieModal';
import MoodSelector from './components/MoodSelector';

const TMDB = 'https://image.tmdb.org/t/p/w780';

const MOVIES = [
  { id: 1, title: "Fight Club", studio: "Fox 2000 Pictures", color: "#FFE600",
    mood: 'excited', image: `${TMDB}/hZkgoQYus5vegHoetLkCJzb17zJ.jpg`,
    insight: "Le film que la Chine a censuré et réécrit. La police gagne à la fin." },
  { id: 2, title: "12 Angry Men", studio: "Orion-Nova Productions", color: "#93C5FD",
    mood: 'brain', image: `${TMDB}/w4bTBXcqXc2TUyS5Fc4h67uWbPn.jpg`,
    insight: "Top 5 IMDb depuis 60 ans. Budget : une pièce et 12 chaises." },
  { id: 3, title: "Parasite", studio: "Barunson E&A", color: "#86EFAC",
    mood: 'excited', image: `${TMDB}/hiKmpZMGZsrkA3cdce8a7Dpos1j.jpg`,
    insight: "Premier film non-anglophone à gagner l'Oscar du meilleur film." },
  { id: 4, title: "Lost in Translation", studio: "Focus Features", color: "#C4B5FD",
    mood: 'sad', image: `${TMDB}/6ITVHoipvxAS8luzKtHTbPaHLtT.jpg`,
    insight: "Tourné en 27 jours à Tokyo. Le murmure final ? Personne ne sait ce qu'il dit." },
  { id: 5, title: "The Notebook", studio: "New Line Cinema", color: "#FDA4AF",
    mood: 'romantic', image: `${TMDB}/zdXnJqBaGFVtLoPNuMeKfEYUViZ.jpg`,
    insight: "Gosling et McAdams se détestaient sur le plateau. L'ironie du siècle." },
  { id: 6, title: "The Shining", studio: "Warner Bros.", color: "#FCA5A5",
    mood: 'scared', image: `${TMDB}/mmd1HnuvAzFc4iuVJcnBrhDNEKr.jpg`,
    insight: "Kubrick a fait refaire la scène de la porte 127 fois. Nicholson a failli craquer." },
  { id: 7, title: "The Big Lebowski", studio: "Gramercy Pictures", color: "#FDE68A",
    mood: 'chill', image: `${TMDB}/hXsy4XCCHrUk81XoRhcooyWejao.jpg`,
    insight: "Le Dude est basé sur un vrai mec. Il vit toujours à L.A." },
  { id: 8, title: "Eternal Sunshine", studio: "Focus Features", color: "#A5F3FC",
    mood: 'sad', image: `${TMDB}/W1ffLQGHoxfAOq0ZYdPtJlvAdb.jpg`,
    insight: "Écrit par Charlie Kaufman en une nuit d'insomnie. Ça se sent." },
];

const BG_COLORS = {
  default: '#F0F0F0',
  chill: '#FFFBEB',
  sad: '#ECFEFF',
  excited: '#FFF1F2',
  scared: '#F5F3FF',
  romantic: '#FDF2F8',
  brain: '#F0FDF4',
};

export default function App() {
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [mood, setMood] = useState(null);

  const filtered = mood ? MOVIES.filter((m) => m.mood === mood) : MOVIES;
  const bg = mood ? BG_COLORS[mood] : BG_COLORS.default;

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: bg }]}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.headerWrapper}>
          <View style={styles.headerShadow} />
          <View style={styles.header}>
            <Text style={styles.title}>MORDU</Text>
          </View>
        </View>

        <MoodSelector selected={mood} onSelect={setMood} />

        {filtered.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>Aucun film pour cette humeur... pour l'instant</Text>
          </View>
        ) : (
          <View style={styles.grid}>
            {filtered.map((movie) => (
              <MovieCard key={movie.id} movie={movie} onPress={() => setSelectedMovie(movie)} />
            ))}
          </View>
        )}
      </ScrollView>

      <MovieModal movie={selectedMovie} onClose={() => setSelectedMovie(null)} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: 24 },
  headerWrapper: { marginBottom: 24, alignSelf: 'flex-start' },
  headerShadow: {
    position: 'absolute', top: 6, left: 6,
    right: -6, bottom: -6, backgroundColor: '#000',
  },
  header: {
    backgroundColor: '#FFE600', borderWidth: 4,
    borderColor: '#000', paddingHorizontal: 16, paddingVertical: 8,
  },
  title: { fontSize: 56, fontWeight: '900', textTransform: 'uppercase', letterSpacing: -1 },
  grid: { gap: 20 },
  empty: {
    borderWidth: 3, borderColor: '#000', borderStyle: 'dashed',
    padding: 32, alignItems: 'center',
  },
  emptyText: { fontSize: 16, fontWeight: '700', textAlign: 'center' },
});
