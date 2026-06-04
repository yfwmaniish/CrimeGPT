// Relative quality bucket for a ranked suggestion, by its position in the
// returned top-N list. Presentation-only: the backend ranking is unchanged.
//
//   top 33%    -> "high"
//   middle 33% -> "medium"
//   bottom 33% -> "lower"
//
// With only 1-2 results, everything is "high" (a tiny list has no meaningful
// spread). The first item is always "high"; for 3+ items the last is "lower".
export function qualityKey(index, total) {
  if (total <= 2) return "high";
  const r = index / total; // 0 .. <1
  if (r < 1 / 3) return "high";
  if (r < 2 / 3) return "medium";
  return "lower";
}
