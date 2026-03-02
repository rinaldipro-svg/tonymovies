import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const C = {
  gold:       '#C9A84C',
  goldDim:    '#7A6330',
  teal:       '#00E5CC',
  tealDim:    '#00796B',
  white:      '#F0EEE8',
  muted:      '#6B6B7A',
  surface:    '#111118',
  pink:       '#FF69B4',
  purple:     '#9B59B6',
};

/**
 * AwardBadge Component
 * Displays award badges with emoji and label
 * 
 * Props:
 *   - type: 'tonypedia' | 'oscar' | 'palme' | 'criterion'
 *   - winner: boolean (for oscar - shows "Winner" vs "Nominated")
 */
export function AwardBadge({ type, winner = true }) {
  const badges = {
    tonypedia: {
      emoji: '🎭',
      label: 'Tonypedia',
      color: C.gold,
      bgColor: 'rgba(201, 168, 76, 0.15)',
      borderColor: C.gold,
    },
    oscar: {
      emoji: '🏆',
      label: winner ? 'Oscar Winner' : 'Oscar Nominated',
      color: winner ? C.gold : C.teal,
      bgColor: winner ? 'rgba(201, 168, 76, 0.1)' : 'rgba(0, 229, 204, 0.1)',
      borderColor: winner ? C.gold : C.teal,
    },
    palme: {
      emoji: '🌹',
      label: 'Palme d\'Or',
      color: C.pink,
      bgColor: 'rgba(255, 105, 180, 0.1)',
      borderColor: C.pink,
    },
    criterion: {
      emoji: '📚',
      label: 'Criterion',
      color: C.purple,
      bgColor: 'rgba(155, 89, 182, 0.1)',
      borderColor: C.purple,
    },
  };

  const badge = badges[type];
  if (!badge) return null;

  return (
    <View style={[
      styles.badge,
      {
        backgroundColor: badge.bgColor,
        borderColor: badge.borderColor,
      }
    ]}>
      <Text style={styles.emoji}>{badge.emoji}</Text>
      <Text style={[styles.label, { color: badge.color }]}>
        {badge.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1.5,
    marginRight: 8,
    marginBottom: 6,
  },
  emoji: {
    fontSize: 14,
    marginRight: 4,
  },
  label: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
});
