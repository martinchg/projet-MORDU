import { View, Text, StyleSheet, Modal, TouchableOpacity, ScrollView } from 'react-native';

export default function MovieModal({ movie, onClose }) {
  if (!movie) return null;

  return (
    <Modal transparent animationType="fade" visible={!!movie}>
      <View style={styles.overlay}>
        <View style={styles.wrapper}>
          <View style={styles.shadow} />
          <View style={styles.modal}>
            <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
              <Text style={styles.closeTxt}>✕</Text>
            </TouchableOpacity>

            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{movie.title}</Text>
              <Text style={styles.modalStudio}>Studio : {movie.studio}</Text>
            </View>

            <ScrollView style={styles.body}>
              <View style={styles.insightBox}>
                <Text style={styles.insightLabel}>Le mot du Mordu :</Text>
                <Text style={styles.insightText}>{movie.insight}</Text>
              </View>

              <View style={styles.stats}>
                <View style={styles.stat}>
                  <Text style={styles.statText}>⭐ Score Mood : 9.2</Text>
                </View>
                <View style={styles.stat}>
                  <Text style={styles.statText}>📈 Hype Studio : Max</Text>
                </View>
              </View>

              <TouchableOpacity style={styles.cta}>
                <Text style={styles.ctaText}>Miser sur ce film</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'center', padding: 20 },
  wrapper: {},
  shadow: { position: 'absolute', top: 10, left: 10, right: -10, bottom: -10, backgroundColor: '#000' },
  modal: { backgroundColor: '#fff', borderWidth: 4, borderColor: '#000', maxHeight: '90%' },
  closeBtn: {
    position: 'absolute', top: 12, right: 12, zIndex: 10,
    backgroundColor: '#EF4444', borderWidth: 2, borderColor: '#000', padding: 4,
  },
  closeTxt: { fontSize: 18, fontWeight: '900', color: '#fff' },
  modalHeader: { backgroundColor: '#FFE600', borderBottomWidth: 4, borderBottomColor: '#000', padding: 24 },
  modalTitle: { fontSize: 36, fontWeight: '900', textTransform: 'uppercase', letterSpacing: -1 },
  modalStudio: { fontSize: 16, fontWeight: '700', fontStyle: 'italic', marginTop: 4 },
  body: { padding: 24 },
  insightBox: { backgroundColor: '#DBEAFE', borderWidth: 3, borderColor: '#000', padding: 16, marginBottom: 20 },
  insightLabel: { fontSize: 12, fontWeight: '900', textTransform: 'uppercase', fontStyle: 'italic', marginBottom: 8 },
  insightText: { fontSize: 15, fontWeight: '600', lineHeight: 22 },
  stats: { flexDirection: 'row', gap: 12, marginBottom: 24 },
  stat: { flex: 1, borderWidth: 2, borderColor: '#000', padding: 12 },
  statText: { fontWeight: '900', fontStyle: 'italic' },
  cta: {
    backgroundColor: '#000', padding: 20, marginBottom: 8,
    shadowColor: '#EF4444', shadowOffset: { width: 4, height: 4 }, shadowOpacity: 1, shadowRadius: 0,
  },
  ctaText: { color: '#fff', fontSize: 20, fontWeight: '900', textTransform: 'uppercase', textAlign: 'center' },
});
