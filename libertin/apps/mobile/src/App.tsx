import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View } from 'react-native';

export default function App() {
  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Libertin</Text>
      <Text style={styles.sub}>Phase 1 — skeleton OK</Text>
      <StatusBar style="light" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAF9', alignItems: 'center', justifyContent: 'center' },
  heading: { fontSize: 32, fontWeight: '700', color: '#F20B49' },
  sub: { fontSize: 16, color: '#1E1B1B', marginTop: 8 },
});
