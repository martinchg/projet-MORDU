import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { useState } from 'react';

export default function MovieCard({ movie, onPress }) {
  const [pressed, setPressed] = useState(false);

  return (
    <View style={styles.wrapper}>
      {!pressed && <View style={styles.shadow} />}
      <TouchableOpacity
        style={[styles.card, { backgroundColor: movie.color }, pressed && styles.cardPressed]}
        onPressIn={() => setPressed(true)}
        onPressOut={() => setPressed(false)}
        onPress={onPress}
        activeOpacity={1}
      >
        <View style={styles.row}>
          <View style={styles.imageContainer}>
            <Image source={{ uri: movie.image }} style={styles.image} resizeMode="cover" />
          </View>
          <View style={styles.content}>
            <View>
              <Text style={styles.title}>{movie.title}</Text>
              <Text style={styles.studio}>Studio : {movie.studio}</Text>
            </View>
            <View style={styles.divider} />
            <Text style={styles.hook}>{movie.insight}</Text>
            <View style={styles.footer}>
              <Text style={styles.footerLabel}>Détails studio</Text>
              <View style={styles.arrow}>
                <Text style={styles.arrowText}>→</Text>
              </View>
            </View>
          </View>
        </View>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { marginBottom: 4 },
  shadow: {
    position: 'absolute', top: 6, left: 6,
    right: -6, bottom: -6, backgroundColor: '#000',
  },
  card: { borderWidth: 4, borderColor: '#000', padding: 12 },
  cardPressed: { transform: [{ translateX: 6 }, { translateY: 6 }] },
  row: { flexDirection: 'row', gap: 12 },
  imageContainer: {
    width: 120, borderRadius: 4, borderWidth: 2, borderColor: '#000',
    overflow: 'hidden',
  },
  image: {
    width: '100%', aspectRatio: 16 / 9,
    backgroundColor: '#000',
  },
  content: {
    flex: 1, justifyContent: 'space-between',
  },
  title: { fontSize: 20, fontWeight: '900', textTransform: 'uppercase', letterSpacing: -0.5 },
  studio: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase', opacity: 0.6, marginTop: 4 },
  divider: { height: 2, backgroundColor: '#000', opacity: 0.15, marginVertical: 10 },
  hook: { fontSize: 13, fontWeight: '600', lineHeight: 19 },
  footer: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', borderTopWidth: 2, borderTopColor: '#000',
    marginTop: 12, paddingTop: 10,
  },
  footerLabel: { fontSize: 11, fontWeight: '900', textTransform: 'uppercase', fontStyle: 'italic' },
  arrow: { width: 28, height: 28, backgroundColor: '#000', alignItems: 'center', justifyContent: 'center' },
  arrowText: { color: '#fff', fontSize: 16, fontWeight: '900' },
});
