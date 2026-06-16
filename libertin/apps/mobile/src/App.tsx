import { useEffect, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView, StyleSheet } from 'react-native';
import { initI18n } from '@libertin/i18n';
import { AuthFlow } from './AuthFlow';
import { server } from './mocks/native';

export default function App() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Boot offline against MSW mocks in development.
    if (__DEV__) {
      server.listen({ onUnhandledRequest: 'bypass' });
    }
    let active = true;
    void initI18n('cs').then(() => {
      if (active) setReady(true);
    });
    return () => {
      active = false;
      if (__DEV__) server.close();
    };
  }, []);

  if (!ready) return null;

  return (
    <SafeAreaView style={styles.root}>
      <AuthFlow />
      <StatusBar style="dark" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#FAFAF9' },
});
