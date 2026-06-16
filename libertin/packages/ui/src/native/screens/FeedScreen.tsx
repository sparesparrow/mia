import React from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { nativeTheme as t } from '@libertin/theme/native';

export interface FeedScreenItem {
  id: string;
  author: string;
  content: string | null;
}

export interface FeedScreenProps {
  items: FeedScreenItem[];
  loading?: boolean;
}

function initials(name: string): string {
  return name.split(/\s+/).map((p) => p.charAt(0)).slice(0, 2).join('').toUpperCase();
}

export function FeedScreen({ items, loading }: FeedScreenProps) {
  const { t: translate } = useTranslation();

  if (loading) {
    return (
      <View style={[styles.root, styles.center]}>
        <ActivityIndicator color={t.colors.primary} />
        <Text style={styles.muted}>{translate('common.loading')}</Text>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <Text style={styles.heading}>{translate('feed.title')}</Text>
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        ItemSeparatorComponent={() => <View style={styles.sep} />}
        ListEmptyComponent={<Text style={styles.muted}>{translate('feed.empty')}</Text>}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{initials(item.author)}</Text>
            </View>
            <View style={styles.rowBody}>
              <Text style={styles.author}>{item.author}</Text>
              {item.content ? <Text style={styles.content}>{item.content}</Text> : null}
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: t.colors.bg, paddingTop: t.spacing[8] },
  center: { alignItems: 'center', justifyContent: 'center', gap: t.spacing[2] },
  heading: { fontSize: t.fontSize['2xl'], fontWeight: t.fontWeight.bold, color: t.colors.text, paddingHorizontal: t.spacing[6], marginBottom: t.spacing[3] },
  list: { paddingHorizontal: t.spacing[6], paddingBottom: t.spacing[8], flexGrow: 1 },
  row: { flexDirection: 'row', gap: t.spacing[3], alignItems: 'flex-start' },
  rowBody: { flex: 1, gap: t.spacing[1] },
  avatar: { width: 48, height: 48, borderRadius: t.radius.full, backgroundColor: t.colors.primary, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: t.colors.onPrimary, fontWeight: t.fontWeight.semibold, fontSize: t.fontSize.base },
  author: { fontSize: t.fontSize.base, fontWeight: t.fontWeight.semibold, color: t.colors.text },
  content: { fontSize: t.fontSize.sm, color: t.colors.textMuted, lineHeight: 20 },
  muted: { fontSize: t.fontSize.base, color: t.colors.textMuted, textAlign: 'center' },
  sep: { height: t.spacing[4] },
});
