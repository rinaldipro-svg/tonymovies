import { API_URL, API_TIMEOUT } from '../config';
import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, Image, ScrollView,
  ActivityIndicator, StyleSheet, SafeAreaView, Dimensions,
  StatusBar, FlatList
} from 'react-native';
import axios from 'axios';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

// ─── DESIGN TOKENS ────────────────────────────────────────────────────────────
const C = {
  bg:          '#0A0A0F',
  surface:     '#111118',
  surfaceHigh: '#18181F',
  border:      '#222230',
  gold:        '#C9A84C',
  goldDim:     '#7A6330',
  teal:        '#00E5CC',
  tealDim:     '#00796B',
  white:       '#F0EEE8',
  muted:       '#6B6B7A',
  mutedLight:  '#9A9AAA',
  danger:      '#FF6B6B',
};

// ─── 12 CORE MOODS ────────────────────────────────────────────────────────────
const MOODS = [
  { id: 'Thrilling', label: 'Thrilling', emoji: '💥' },
  { id: 'Heartwarming', label: 'Heartwarming', emoji: '❤️' },
  { id: 'Melancholic', label: 'Melancholic', emoji: '🌧️' },
  { id: 'Mind-bending', label: 'Mind-bending', emoji: '🤯' },
  { id: 'Darkly comic', label: 'Darkly comic', emoji: '😈' },
  { id: 'Romantic', label: 'Romantic', emoji: '💕' },
  { id: 'Haunting', label: 'Haunting', emoji: '👻' },
  { id: 'Euphoric', label: 'Euphoric', emoji: '🎉' },
  { id: 'Tense', label: 'Tense', emoji: '⚡' },
  { id: 'Contemplative', label: 'Contemplative', emoji: '🤔' },
  { id: 'Triumphant', label: 'Triumphant', emoji: '👑' },
  { id: 'Visceral', label: 'Visceral', emoji: '🔥' },
];

const TOPICS = [
  'Identity & self-discovery',
  'Family & relationships',
  'Power & corruption',
  'Survival & resilience',
  'Love & heartbreak',
  'Justice & morality',
  'War & conflict',
  'Art & creativity',
  'Isolation & loneliness',
  'Freedom & rebellion',
  'Coming of age',
  'Obsession & ambition',
  'The heist & the con',
  'History & civilization',
  'Science & the unknown'
];

const VIBES = [
  'Cinematic & epic',
  'Raw & gritty',
  'Dreamlike & surreal',
  'Intimate & quiet',
  'Stylish & cool',
  'Nostalgic & warm',
  'Bleak & unflinching',
  'Whimsical & playful'
];

const GENRES = [
  'Drama', 'Comedy', 'Thriller', 'Horror', 'Sci-Fi',
  'Romance', 'Action', 'Documentary', 'Animation', 'Crime',
  'War', 'Fantasy', 'Musical', 'Western'
];
const ERAS = [
  'Pre-1960 (Golden Age)',
  '1960-1979 (New Wave)',
  '1980-1999 (Modern Classics)',
  '2000-2014 (Digital Age)',
  '2015-Present (Contemporary)'
];

// ─── SCORE BADGE ──────────────────────────────────────────────────────────────
function ScoreBadge({ label, value, accent, size = 'md' }) {
  const isLarge = size === 'lg';
  const display = value != null ? parseFloat(value).toFixed(1) : '—';
  return (
    <View style={[badgeStyles.wrap, isLarge && badgeStyles.wrapLg, { borderColor: accent }]}>
      <Text style={[badgeStyles.value, isLarge && badgeStyles.valueLg, { color: accent }]}>
        {display}
      </Text>
      <Text style={[badgeStyles.label, isLarge && badgeStyles.labelLg]}>{label}</Text>
    </View>
  );
}

const badgeStyles = StyleSheet.create({
  wrap: {
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1.5, borderRadius: 10,
    paddingHorizontal: 12, paddingVertical: 8, marginHorizontal: 4,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  wrapLg: { paddingHorizontal: 18, paddingVertical: 12, borderRadius: 14, borderWidth: 2 },
  value: { fontSize: 18, fontWeight: '800', letterSpacing: 0.5 },
  valueLg: { fontSize: 26 },
  label: { fontSize: 9, color: C.muted, fontWeight: '600', letterSpacing: 1, marginTop: 2, textTransform: 'uppercase' },
  labelLg: { fontSize: 11, marginTop: 4 },
});

// ─── AWARD BADGE ──────────────────────────────────────────────────────────────
/**
 * AwardBadge Component - Displays award badges with emoji and label
 * Types: 'tonypedia' | 'oscar' | 'palme' | 'criterion'
 */
function AwardBadge({ type, winner = true }) {
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
      color: '#FF69B4',
      bgColor: 'rgba(255, 105, 180, 0.1)',
      borderColor: '#FF69B4',
    },
    criterion: {
      emoji: '📚',
      label: 'Criterion',
      color: '#9B59B6',
      bgColor: 'rgba(155, 89, 182, 0.1)',
      borderColor: '#9B59B6',
    },
  };

  const badge = badges[type];
  if (!badge) return null;

  return (
    <View style={[
      awardBadgeStyles.badge,
      {
        backgroundColor: badge.bgColor,
        borderColor: badge.borderColor,
      }
    ]}>
      <Text style={awardBadgeStyles.emoji}>{badge.emoji}</Text>
      <Text style={[awardBadgeStyles.label, { color: badge.color }]}>
        {badge.label}
      </Text>
    </View>
  );
}

const awardBadgeStyles = StyleSheet.create({
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

// ─── SCORE BREAKDOWN ──────────────────────────────────────────────────────────
function ScoreRow({ label, value }) {
  if (value == null) return null;
  const pct = Math.min((value / 10) * 100, 100);
  return (
    <View style={breakdownStyles.row}>
      <Text style={breakdownStyles.label}>{label}</Text>
      <View style={breakdownStyles.barBg}>
        <View style={[breakdownStyles.barFill, { width: `${pct}%` }]} />
      </View>
      <Text style={breakdownStyles.value}>{parseFloat(value).toFixed(1)}</Text>
    </View>
  );
}

const breakdownStyles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  label: { width: 80, color: C.mutedLight, fontSize: 11, fontWeight: '600', letterSpacing: 0.5, textTransform: 'uppercase' },
  barBg: { flex: 1, height: 4, backgroundColor: C.border, borderRadius: 2, marginHorizontal: 10 },
  barFill: { height: 4, backgroundColor: C.gold, borderRadius: 2 },
  value: { width: 28, color: C.white, fontSize: 12, fontWeight: '700', textAlign: 'right' },
});

// ─── FILM CARD ────────────────────────────────────────────────────────────────
function FilmCard({ item, onPress, selected }) {
  return (
    <TouchableOpacity
      style={[cardStyles.wrap, selected && cardStyles.wrapSelected]}
      onPress={() => onPress(item)}
      activeOpacity={0.85}
    >
      <View style={cardStyles.rankBadge}>
        <Text style={cardStyles.rankText}>#{item.rank}</Text>
      </View>

      <Image
        source={{ uri: item.poster || 'https://via.placeholder.com/120x180/111118/C9A84C?text=?' }}
        style={cardStyles.poster}
      />

      <View style={cardStyles.info}>
        <Text style={cardStyles.title} numberOfLines={2}>{item.title}</Text>
        <Text style={cardStyles.year}>{item.year}</Text>

        <View style={cardStyles.scores}>
          {item.is_tonypedia && <ScoreBadge label="Tonypedia" value={item.tonypedia_score} accent={C.gold} />}
          <ScoreBadge label="Global" value={item.global_average} accent={C.teal} />
        </View>

        {/* NEW: Award Badges */}
        <View style={cardStyles.awardBadges}>
          {item.is_oscar_winner && <AwardBadge type="oscar" winner={true} />}
          {item.is_oscar_nominated && !item.is_oscar_winner && <AwardBadge type="oscar" winner={false} />}
          {item.is_palme_dor_winner && <AwardBadge type="palme" />}
          {item.is_criterion && <AwardBadge type="criterion" />}
        </View>

        <Text style={cardStyles.explanation} numberOfLines={2}>
          {item.explanation}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const cardStyles = StyleSheet.create({
  wrap: {
    flexDirection: 'row', backgroundColor: C.surface,
    borderRadius: 16, marginBottom: 12, overflow: 'hidden',
    borderWidth: 1, borderColor: C.border,
  },
  wrapSelected: { borderColor: C.gold },
  rankBadge: {
    position: 'absolute', top: 10, left: 10, zIndex: 2,
    backgroundColor: 'rgba(0,0,0,0.75)', borderRadius: 6,
    paddingHorizontal: 7, paddingVertical: 3,
  },
  rankText: { color: C.gold, fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  poster: { width: 100, height: 150, resizeMode: 'cover' },
  info: { flex: 1, padding: 14, justifyContent: 'space-between' },
  title: { color: C.white, fontSize: 15, fontWeight: '700', lineHeight: 20 },
  year: { color: C.muted, fontSize: 12, marginTop: 3 },
  scores: { flexDirection: 'row', marginTop: 10 },
  awardBadges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
    marginBottom: 4,
  },
  explanation: { color: C.mutedLight, fontSize: 12, lineHeight: 16, marginTop: 8, fontStyle: 'italic' },
});

// ─── FILM DETAIL MODAL ────────────────────────────────────────────────────────
function FilmDetail({ film, onClose }) {
  if (!film) return null;
  return (
    <View style={detailStyles.overlay}>
      <ScrollView contentContainerStyle={detailStyles.scroll} showsVerticalScrollIndicator={false}>

        <TouchableOpacity style={detailStyles.closeBtn} onPress={onClose}>
          <Text style={detailStyles.closeText}>✕ Close</Text>
        </TouchableOpacity>

        <Image
          source={{ uri: film.poster || 'https://via.placeholder.com/400x600/111118/C9A84C?text=?' }}
          style={detailStyles.poster}
        />

        <View style={detailStyles.titleBlock}>
          <View style={detailStyles.rankPill}>
            <Text style={detailStyles.rankText}>#{film.rank} Match</Text>
          </View>
          <Text style={detailStyles.title}>{film.title}</Text>
          <Text style={detailStyles.year}>{film.year}</Text>
        </View>

        <View style={detailStyles.dualScore}>
          <ScoreBadge label="Global Average" value={film.global_average} accent={C.teal} size="lg" />
          <View style={detailStyles.scoreDivider} />
          <ScoreBadge label="Tonypedia" value={film.tonypedia_score} accent={C.gold} size="lg" />
        </View>

        <View style={detailStyles.explanationBox}>
          <Text style={detailStyles.explanationLabel}>WHY THIS FILM</Text>
          <Text style={detailStyles.explanationText}>{film.explanation}</Text>
        </View>

        <View style={detailStyles.section}>
          <Text style={detailStyles.sectionLabel}>SYNOPSIS</Text>
          <Text style={detailStyles.plot}>{film.plot}</Text>
        </View>

        {film.scores && (
          <View style={detailStyles.section}>
            <Text style={detailStyles.sectionLabel}>SCORE BREAKDOWN</Text>
            <ScoreRow label="IMDb" value={film.scores.imdb} />
            <ScoreRow label="Rotten T." value={film.scores.rt} />
            <ScoreRow label="Metacritic" value={film.scores.metacritic} />
            <ScoreRow label="TMDB" value={film.scores.tmdb} />
            <View style={detailStyles.dividerLine} />
            <ScoreRow label="Tonypedia" value={film.tonypedia_score} />
          </View>
        )}

        {/* NEW: AWARDS & RECOGNITION SECTION */}
        {(film.is_oscar_winner || film.is_oscar_nominated || film.is_palme_dor_winner || film.is_criterion) && (
          <View style={detailStyles.awardSection}>
            <Text style={detailStyles.sectionLabel}>🏆 AWARDS & RECOGNITION</Text>
            
            {film.is_oscar_winner && (
              <View style={detailStyles.awardItem}>
                <Text style={detailStyles.awardEmoji}>🏆</Text>
                <Text style={detailStyles.awardText}>Academy Award Winner</Text>
              </View>
            )}
            
            {film.is_oscar_nominated && !film.is_oscar_winner && (
              <View style={detailStyles.awardItem}>
                <Text style={detailStyles.awardEmoji}>🏆</Text>
                <Text style={detailStyles.awardText}>Oscar Nominated</Text>
              </View>
            )}
            
            {film.is_palme_dor_winner && (
              <View style={detailStyles.awardItem}>
                <Text style={detailStyles.awardEmoji}>🌹</Text>
                <Text style={detailStyles.awardText}>Palme d'Or Winner (Cannes)</Text>
              </View>
            )}
            
            {film.is_criterion && (
              <View style={detailStyles.awardItem}>
                <Text style={detailStyles.awardEmoji}>📚</Text>
                <Text style={detailStyles.awardText}>Criterion Collection</Text>
              </View>
            )}
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}

const detailStyles = StyleSheet.create({
  overlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: C.bg, zIndex: 100,
  },
  scroll: { paddingBottom: 60 },
  closeBtn: {
    position: 'absolute', top: 50, right: 20, zIndex: 10,
    backgroundColor: 'rgba(0,0,0,0.6)', paddingHorizontal: 14,
    paddingVertical: 8, borderRadius: 20, borderWidth: 1, borderColor: C.border,
  },
  closeText: { color: C.mutedLight, fontSize: 13, fontWeight: '600' },
  poster: { width: SCREEN_W, height: SCREEN_H * 0.55, resizeMode: 'cover' },
  titleBlock: { padding: 20, paddingBottom: 0 },
  rankPill: {
    alignSelf: 'flex-start', backgroundColor: C.gold,
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, marginBottom: 12,
  },
  rankText: { color: '#0A0A0F', fontWeight: '800', fontSize: 11, letterSpacing: 0.5 },
  title: { fontSize: 24, fontWeight: '900', color: C.white, marginBottom: 6 },
  year: { color: C.muted, fontSize: 13, marginBottom: 20 },
  dualScore: { flexDirection: 'row', paddingHorizontal: 20, marginBottom: 20 },
  scoreDivider: { width: 1, backgroundColor: C.border, marginHorizontal: 12 },
  explanationBox: { paddingHorizontal: 20, paddingVertical: 16, backgroundColor: C.surface, borderRadius: 12, marginHorizontal: 20, marginBottom: 20 },
  explanationLabel: { color: C.gold, fontSize: 10, fontWeight: '800', letterSpacing: 1.5, marginBottom: 6 },
  explanationText: { color: C.white, fontSize: 15, lineHeight: 22, fontStyle: 'italic' },
  section: { paddingHorizontal: 20, paddingVertical: 12, marginBottom: 20 },
  sectionLabel: { color: C.gold, fontSize: 10, fontWeight: '800', letterSpacing: 1.5, marginBottom: 12 },
  plot: { color: C.mutedLight, fontSize: 14, lineHeight: 20 },
  dividerLine: { height: 1, backgroundColor: C.border, marginVertical: 12 },
  awardSection: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    marginHorizontal: 20,
    marginBottom: 20,
    backgroundColor: C.surface,
    borderRadius: 12,
    borderLeftWidth: 3,
    borderLeftColor: C.gold,
  },
  awardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  awardEmoji: {
    fontSize: 18,
    marginRight: 10,
  },
  awardText: {
    color: C.white,
    fontSize: 14,
    fontWeight: '600',
  },
});

// ─── PRESET SELECTOR (Topic/Vibe) ─────────────────────────────────────────
function PresetSelector({ presets, selected, onChange, label }) {
  return (
    <View style={presetStyles.wrap}>
      <Text style={presetStyles.label}>{label}</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={presetStyles.scrollWrap}
      >
        {presets.map((preset, idx) => (
          <TouchableOpacity
            key={idx}
            style={[presetStyles.btn, selected === preset && presetStyles.btnSelected]}
            onPress={() => onChange(preset)}
          >
            <Text style={[presetStyles.btnText, selected === preset && presetStyles.btnTextSelected]}>
              {preset}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const presetStyles = StyleSheet.create({
  wrap: { marginBottom: 16 },
  label: { color: C.gold, fontSize: 11, fontWeight: '800', letterSpacing: 1, marginBottom: 8, textTransform: 'uppercase' },
  scrollWrap: { flexDirection: 'row', gap: 8 },
  btn: {
    paddingVertical: 10, paddingHorizontal: 14,
    backgroundColor: C.surfaceHigh, borderRadius: 10,
    borderWidth: 1, borderColor: C.border,
  },
  btnSelected: { borderColor: C.gold, backgroundColor: 'rgba(201, 168, 76, 0.15)' },
  btnText: { color: C.mutedLight, fontSize: 13, fontWeight: '600', whiteSpace: 'nowrap' },
  btnTextSelected: { color: C.gold },
});
function MoodSelector({ selected, onChange }) {
  return (
    <View style={moodStyles.grid}>
      {MOODS.map((mood) => (
        <TouchableOpacity
          key={mood.id}
          style={[moodStyles.btn, selected === mood.id && moodStyles.btnSelected]}
          onPress={() => onChange(mood.id)}
        >
          <Text style={moodStyles.emoji}>{mood.emoji}</Text>
          <Text style={[moodStyles.label, selected === mood.id && moodStyles.labelSelected]}>
            {mood.label}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const moodStyles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 24 },
  btn: {
    width: '23%', aspectRatio: 0.9,
    backgroundColor: C.surfaceHigh, borderRadius: 14,
    borderWidth: 2, borderColor: C.border,
    alignItems: 'center', justifyContent: 'center', gap: 6,
    paddingVertical: 12,
  },
  btnSelected: { borderColor: C.gold, backgroundColor: 'rgba(201, 168, 76, 0.15)' },
  emoji: { fontSize: 28 },
  label: { color: C.mutedLight, fontSize: 11, fontWeight: '600', textAlign: 'center' },
  labelSelected: { color: C.gold },
});

// ─── GENRE DROPDOWN ────────────────────────────────────────────────────────────
function GenreDropdown({ selected, onChange }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={{ marginBottom: 16 }}>
      <TouchableOpacity
        style={[genreStyles.btn, open && genreStyles.btnOpen]}
        onPress={() => setOpen(!open)}
      >
        <Text style={genreStyles.btnText}>
          {selected || 'Genre (Optional)'}
        </Text>
        <Text style={genreStyles.arrow}>{open ? '▲' : '▼'}</Text>
      </TouchableOpacity>
      {open && (
        <FlatList
          data={[{ id: 'none', label: 'None' }, ...GENRES.map((g, i) => ({ id: i.toString(), label: g }))]}
          keyExtractor={(item) => item.id}
          scrollEnabled
          style={genreStyles.dropdown}
          nestedScrollEnabled
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[genreStyles.option, selected === item.label && genreStyles.optionSelected]}
              onPress={() => {
                onChange(item.label === 'None' ? null : item.label);
                setOpen(false);
              }}
            >
              <Text style={[genreStyles.optionText, selected === item.label && genreStyles.optionTextSelected]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const genreStyles = StyleSheet.create({
  btn: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    backgroundColor: C.surfaceHigh, padding: 16, borderRadius: 12,
    borderWidth: 1, borderColor: C.border,
  },
  btnOpen: { borderColor: C.gold },
  btnText: { color: C.white, fontSize: 15, fontWeight: '600' },
  arrow: { color: C.muted, fontSize: 12 },
  dropdown: {
    backgroundColor: C.surface, borderRadius: 12, borderWidth: 1,
    borderColor: C.border, overflow: 'hidden', marginTop: 8, maxHeight: 250,
  },
  option: { paddingVertical: 14, paddingHorizontal: 16, borderBottomWidth: 1, borderColor: C.border },
  optionSelected: { backgroundColor: C.surfaceHigh },
  optionText: { color: C.mutedLight, fontSize: 14 },
  optionTextSelected: { color: C.gold, fontWeight: '700' },
});

// ─── ERA CHECKBOXES ────────────────────────────────────────────────────────────
function EraSelector({ selected, onChange }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={{ marginBottom: 16 }}>
      <TouchableOpacity
        style={[genreStyles.btn, open && genreStyles.btnOpen]}
        onPress={() => setOpen(!open)}
      >
        <Text style={genreStyles.btnText}>
          {selected || 'Era (Optional)'}
        </Text>
        <Text style={genreStyles.arrow}>{open ? '▲' : '▼'}</Text>
      </TouchableOpacity>
      {open && (
        <FlatList
          data={[{ id: 'none', label: 'None' }, ...ERAS.map((e, i) => ({ id: i.toString(), label: e }))]}
          keyExtractor={(item) => item.id}
          scrollEnabled
          style={genreStyles.dropdown}
          nestedScrollEnabled
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[genreStyles.option, selected === item.label && genreStyles.optionSelected]}
              onPress={() => {
                onChange(item.label === 'None' ? null : item.label);
                setOpen(false);
              }}
            >
              <Text style={[genreStyles.optionText, selected === item.label && genreStyles.optionTextSelected]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
    </View>
  );
}

const eraStyles = StyleSheet.create({
  wrap: { gap: 10, marginBottom: 16 },
  btn: {
    flexDirection: 'row', alignItems: 'center',
    paddingVertical: 12, paddingHorizontal: 14,
    backgroundColor: C.surfaceHigh, borderRadius: 10,
    borderWidth: 1, borderColor: C.border,
  },
  btnSelected: { borderColor: C.gold, backgroundColor: 'rgba(201, 168, 76, 0.1)' },
  checkbox: {
    width: 20, height: 20, borderRadius: 4,
    borderWidth: 2, borderColor: C.border,
    alignItems: 'center', justifyContent: 'center',
    marginRight: 10,
  },
  checkboxSelected: { backgroundColor: C.gold, borderColor: C.gold },
  check: { color: '#0A0A0F', fontSize: 12, fontWeight: '800' },
  label: { color: C.mutedLight, fontSize: 14, fontWeight: '600' },
  labelSelected: { color: C.white },
});

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
export default function App() {
  const [step, setStep]       = useState(1);
  const [loading, setLoading] = useState(false);
  const [form, setForm]       = useState({
    mood: null, topic: '', vibe: '', genre: null, era: null
  });
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [browseTonypediaList, setBrowseTonypediaList] = useState([]);
  const [showBrowseModal, setShowBrowseModal] = useState(false);

  const getRecommendations = async (moodValue = form.mood, topicValue = form.topic, vibeValue = form.vibe) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/recommend`, {
        params: {
          mood: moodValue,
          topic: topicValue,
          vibe: vibeValue,
          genre: form.genre || undefined,
          era: form.era || undefined,
        },
        timeout: API_TIMEOUT,
      });

      if (response.data?.results?.length > 0) {
        setResults(response.data.results);
        setStep(3);
      } else {
        alert('No results found. Try different options.');
      }
    } catch (error) {
      console.error(error);
      alert('Connection error. Make sure the Railway backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const randomize = async () => {
    // Generate random topic and vibe for variety
    const topics = ['love', 'adventure', 'survival', 'redemption', 'revenge', 'discovery', 'mystery', 'sacrifice'];
    const vibes = ['dark', 'epic', 'intimate', 'chaotic', 'contemplative', 'surreal', 'minimal', 'explosive'];
    
    const randomTopic = topics[Math.floor(Math.random() * topics.length)];
    const randomVibe = vibes[Math.floor(Math.random() * vibes.length)];
    
    await getRecommendations(form.mood, randomTopic, randomVibe);
  };

  const browseTonypedia = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/tonypedia/browse`, {
        timeout: API_TIMEOUT,
      });

      if (response.data?.results?.length > 0) {
        setBrowseTonypediaList(response.data.results);
        setShowBrowseModal(true);
      } else {
        alert('No Tonypedia-rated movies yet.');
      }
    } catch (error) {
      console.error(error);
      alert('Error loading Tonypedia collection.');
    } finally {
      setLoading(false);
    }
  };

  const resetSearch = () => {
    setForm({ mood: null, topic: '', vibe: '', genre: null, era: null });
    setResults([]);
    setSelected(null);
    setStep(1);
  };

  const canProceedStep2 = form.mood && form.topic && form.vibe;
  const canProceedStep3 = form.eras.length > 0;

  return (
    <SafeAreaView style={appStyles.safe}>
      <StatusBar barStyle="light-content" backgroundColor={C.bg} />

      {selected && <FilmDetail film={selected} onClose={() => setSelected(null)} />}

      {showBrowseModal && (
        <View style={appStyles.modalOverlay}>
          <ScrollView contentContainerStyle={appStyles.modalScroll} showsVerticalScrollIndicator={false}>
            <TouchableOpacity 
              style={appStyles.modalCloseBtn} 
              onPress={() => setShowBrowseModal(false)}
            >
              <Text style={appStyles.modalCloseText}>✕ Close</Text>
            </TouchableOpacity>

            <View style={appStyles.modalHeader}>
              <Text style={appStyles.modalTitle}>My Tonypedia Collection</Text>
              <Text style={appStyles.modalSubtitle}>{browseTonypediaList.length} films, ranked best to worst</Text>
            </View>

            {browseTonypediaList.map((film, i) => (
              <TouchableOpacity
                key={film.rank}
                onPress={() => setSelected(film)}
                activeOpacity={0.85}
              >
                <FilmCard
                  item={film}
                  selected={selected?.rank === film.rank}
                  onPress={f => setSelected(f)}
                />
              </TouchableOpacity>
            ))}

            <View style={{ height: 40 }} />
          </ScrollView>
        </View>
      )}

      <ScrollView
        contentContainerStyle={appStyles.scroll}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {/* Logo */}
        <View style={appStyles.logoWrap}>
          <Text style={appStyles.logoMain}>TONYPEDIA</Text>
          <View style={appStyles.logoPill}>
            <Text style={appStyles.logoSub}>MOVIES</Text>
          </View>
        </View>

        {/* Loading */}
        {loading && (
          <View style={appStyles.loadingWrap}>
            <ActivityIndicator size="large" color={C.gold} />
            <Text style={appStyles.loadingTitle}>Finding your films</Text>
            <Text style={appStyles.loadingSubtitle}>Claude is analyzing your mood...</Text>
          </View>
        )}

        {/* Step 1 — Mood Selection */}
        {!loading && step === 1 && (
          <View style={qStyles.wrap}>
            <Text style={qStyles.stepNum}>Step 1 of 3</Text>
            <Text style={qStyles.question}>How are you feeling?</Text>
            <Text style={qStyles.subtitle}>Pick a mood that resonates with you right now.</Text>
            
            <MoodSelector
              selected={form.mood}
              onChange={(mood) => setForm({ ...form, mood })}
            />

            <TouchableOpacity
              style={[qStyles.btn, !form.mood && qStyles.btnDisabled]}
              onPress={() => setStep(2)}
              disabled={!form.mood}
              activeOpacity={0.8}
            >
              <Text style={qStyles.btnText}>Next →</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Step 2 — Topic & Vibe */}
        {!loading && step === 2 && (
          <View style={qStyles.wrap}>
            <Text style={qStyles.stepNum}>Step 2 of 3</Text>
            <Text style={qStyles.question}>What should it be about?</Text>
            <Text style={qStyles.subtitle}>Pick a theme or add your own.</Text>
            
            <PresetSelector
              presets={TOPICS}
              selected={form.topic}
              onChange={(topic) => setForm({ ...form, topic })}
              label="Topic"
            />

            {form.topic && (
              <TextInput
                style={[qStyles.input, { marginBottom: 0 }]}
                placeholder="Or type your own topic..."
                placeholderTextColor={C.muted}
                value={form.topic}
                onChangeText={txt => setForm({ ...form, topic: txt })}
              />
            )}

            <View style={{ height: 16 }} />

            <Text style={qStyles.question2}>What's the aesthetic?</Text>
            <Text style={qStyles.subtitle2}>Pick a vibe or add your own.</Text>

            <PresetSelector
              presets={VIBES}
              selected={form.vibe}
              onChange={(vibe) => setForm({ ...form, vibe })}
              label="Vibe"
            />

            {form.vibe && (
              <TextInput
                style={[qStyles.input, { marginBottom: 20 }]}
                placeholder="Or type your own vibe..."
                placeholderTextColor={C.muted}
                value={form.vibe}
                onChangeText={txt => setForm({ ...form, vibe: txt })}
              />
            )}

            <TouchableOpacity
              style={[qStyles.btn, !canProceedStep2 && qStyles.btnDisabled]}
              onPress={() => setStep(3)}
              disabled={!canProceedStep2}
              activeOpacity={0.8}
            >
              <Text style={qStyles.btnText}>Next →</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Step 3 — Filters & Results */}
        {!loading && step === 3 && results.length === 0 && (
          <View style={qStyles.wrap}>
            <Text style={qStyles.stepNum}>Step 3 of 3</Text>
            <Text style={qStyles.question}>Optional filters</Text>
            <Text style={qStyles.subtitle}>Narrow down or explore broadly.</Text>
            
            <Text style={qStyles.filterLabel}>Genre</Text>
            <GenreDropdown
              selected={form.genre}
              onChange={(genre) => setForm({ ...form, genre })}
            />

            <Text style={qStyles.filterLabel}>Era</Text>
            <EraSelector
              selected={form.era}
              onChange={(era) => setForm({ ...form, era })}
            />

            <TouchableOpacity
              style={[qStyles.btn, !canProceedStep3 && qStyles.btnDisabled]}
              onPress={() => getRecommendations()}
              disabled={!canProceedStep3}
              activeOpacity={0.8}
            >
              <Text style={qStyles.btnText}>Find My Films</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Results */}
        {!loading && step === 3 && results.length > 0 && (
          <View style={appStyles.resultsWrap}>

            <View style={appStyles.resultsHeader}>
              <Text style={appStyles.resultsTitle}>Your Top 10</Text>
              <Text style={appStyles.resultsMeta}>
                {MOODS.find(m => m.id === form.mood)?.label} · {form.topic} · {form.vibe}
              </Text>
            </View>

            <View style={appStyles.legend}>
              <View style={appStyles.legendItem}>
                <View style={[appStyles.legendDot, { backgroundColor: C.teal }]} />
                <Text style={appStyles.legendText}>Global Average</Text>
              </View>
              <View style={appStyles.legendItem}>
                <View style={[appStyles.legendDot, { backgroundColor: C.gold }]} />
                <Text style={appStyles.legendText}>Tonypedia</Text>
              </View>
            </View>

            {results.map((film, i) => (
              <FilmCard
                key={film.imdb_id || i}
                item={film}
                selected={selected?.rank === film.rank}
                onPress={f => setSelected(f)}
              />
            ))}

            <View style={appStyles.actionRow}>
              <TouchableOpacity style={appStyles.randomBtn} onPress={randomize}>
                <Text style={appStyles.randomText}>🔀 Randomize</Text>
              </TouchableOpacity>

              <TouchableOpacity style={appStyles.browseBtn} onPress={() => browseTonypedia()}>
                <Text style={appStyles.browseText}>📚 Browse Tonypedia</Text>
              </TouchableOpacity>

              <TouchableOpacity style={appStyles.resetBtn} onPress={resetSearch}>
                <Text style={appStyles.resetText}>New Search</Text>
              </TouchableOpacity>
            </View>

          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const qStyles = StyleSheet.create({
  wrap: { width: '100%' },
  stepNum: { color: C.gold, fontSize: 11, fontWeight: '800', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 12 },
  question: { fontSize: 26, fontWeight: '900', color: C.white, marginBottom: 8, lineHeight: 32 },
  question2: { fontSize: 20, fontWeight: '800', color: C.white, marginBottom: 6, marginTop: 8 },
  subtitle: { fontSize: 14, color: C.muted, marginBottom: 16, lineHeight: 20 },
  subtitle2: { fontSize: 13, color: C.muted, marginBottom: 12, lineHeight: 18 },
  filterLabel: { color: C.gold, fontSize: 11, fontWeight: '800', letterSpacing: 1, marginBottom: 12, textTransform: 'uppercase' },
  input: {
    backgroundColor: C.surfaceHigh, color: C.white,
    padding: 16, borderRadius: 12, fontSize: 15,
    marginBottom: 12, borderWidth: 1, borderColor: C.border,
    letterSpacing: 0.3,
  },
  btn: {
    backgroundColor: C.gold, padding: 16,
    borderRadius: 12, alignItems: 'center',
  },
  btnDisabled: { backgroundColor: C.goldDim, opacity: 0.5 },
  btnText: { color: '#0A0A0F', fontWeight: '800', fontSize: 16, letterSpacing: 0.5 },
});

const appStyles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  scroll: { padding: 24, paddingTop: 60, paddingBottom: 80 },

  logoWrap: { flexDirection: 'row', alignItems: 'center', marginBottom: 48, gap: 10 },
  logoMain: { fontSize: 24, fontWeight: '900', color: C.white, letterSpacing: 3 },
  logoPill: { backgroundColor: C.gold, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  logoSub: { fontSize: 11, fontWeight: '800', color: '#0A0A0F', letterSpacing: 2 },

  loadingWrap: { alignItems: 'center', marginTop: 80, gap: 16 },
  loadingTitle: { color: C.white, fontSize: 20, fontWeight: '700' },
  loadingSubtitle: { color: C.muted, fontSize: 14 },

  resultsWrap: { width: '100%' },
  resultsHeader: { marginBottom: 20 },
  resultsTitle: { fontSize: 28, fontWeight: '900', color: C.white, letterSpacing: 1 },
  resultsMeta: { color: C.muted, fontSize: 12, marginTop: 6, fontStyle: 'italic' },

  legend: { flexDirection: 'row', gap: 20, marginBottom: 20 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { color: C.mutedLight, fontSize: 11, fontWeight: '600', letterSpacing: 0.5 },

  actionRow: { flexDirection: 'row', gap: 10, marginTop: 24 },
  randomBtn: {
    flex: 1, padding: 14, borderRadius: 12,
    backgroundColor: C.surfaceHigh, borderWidth: 1.5, borderColor: C.teal,
    alignItems: 'center',
  },
  randomText: { color: C.teal, fontWeight: '700', fontSize: 12, letterSpacing: 0.5 },
  browseBtn: {
    flex: 1, padding: 14, borderRadius: 12,
    backgroundColor: C.surfaceHigh, borderWidth: 1.5, borderColor: C.gold,
    alignItems: 'center',
  },
  browseText: { color: C.gold, fontWeight: '700', fontSize: 12, letterSpacing: 0.5 },
  resetBtn: {
    flex: 1, padding: 14, borderRadius: 12,
    borderWidth: 1.5, borderColor: C.gold, alignItems: 'center',
  },
  resetText: { color: C.gold, fontWeight: '700', fontSize: 12, letterSpacing: 0.5 },
  
  // Browse Modal
  modalOverlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: C.bg, zIndex: 100,
  },
  modalScroll: { paddingBottom: 60 },
  modalCloseBtn: {
    position: 'absolute', top: 50, right: 20, zIndex: 10,
    backgroundColor: 'rgba(0,0,0,0.6)', paddingHorizontal: 14,
    paddingVertical: 8, borderRadius: 20, borderWidth: 1, borderColor: C.border,
  },
  modalCloseText: { color: C.mutedLight, fontSize: 13, fontWeight: '600' },
  modalHeader: { padding: 24, paddingTop: 60, paddingBottom: 20 },
  modalTitle: { fontSize: 28, fontWeight: '900', color: C.white, letterSpacing: 1 },
  modalSubtitle: { color: C.muted, fontSize: 12, marginTop: 6, fontStyle: 'italic' },
});
