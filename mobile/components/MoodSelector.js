import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

const MOODS = [
  { id: 'chill', label: 'Chill' },
  { id: 'sad', label: 'Triste' },
  { id: 'excited', label: 'Survolté' },
  { id: 'scared', label: 'Frissons' },
  { id: 'romantic', label: 'Love' },
  { id: 'brain', label: 'Réfléchir' },
];

const MOOD_COLORS = {
  chill: '#FDE68A',
  sad: '#A5F3FC',
  excited: '#FCA5A5',
  scared: '#DDD6FE',
  romantic: '#FBCFE8',
  brain: '#BBF7D0',
};

export default function MoodSelector({ selected, onSelect }) {
  return (
    <View style={styles.container}>
      <Text style={styles.question}>Tu veux quoi ce soir ?</Text>
      <View style={styles.grid}>
        {MOODS.map((mood) => (
          <TouchableOpacity
            key={mood.id}
            style={[
              styles.moodBtn,
              selected === mood.id && { backgroundColor: MOOD_COLORS[mood.id] },
            ]}
            onPress={() => onSelect(mood.id === selected ? null : mood.id)}
            activeOpacity={0.8}
          >
            <Text style={[
              styles.label,
              selected === mood.id && styles.labelSelected,
            ]}>{mood.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

export { MOOD_COLORS };

const styles = StyleSheet.create({
  container: { marginBottom: 24 },
  question: {
    fontSize: 20, fontWeight: '900', textTransform: 'uppercase',
    marginBottom: 12, letterSpacing: -0.5,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  moodBtn: {
    borderWidth: 3, borderColor: '#000', backgroundColor: '#fff',
    paddingVertical: 12, paddingHorizontal: 18,
    alignItems: 'center', minWidth: 80,
  },
  label: { fontSize: 13, fontWeight: '900', textTransform: 'uppercase' },
  labelSelected: { color: '#000' },
});
