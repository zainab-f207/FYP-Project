/**
 * ppcUtils.js
 * Utility functions for displaying PPC (Pakistan Penal Code) crime names
 * in a concise, layman-friendly way \u2014 no hardcoded dictionaries.
 */

/**
 * Derives a short, plain-English label from a full PPC/law-section crime name.
 * Works by pattern-stripping legal boilerplate from the text itself.
 *
 * Examples:
 *   "Punishment for Murder"                            \u2192 "Murder"
 *   "Punishment for Theft"                             \u2192 "Theft"
 *   "Attempt to Commit Murder"                         \u2192 "Attempted Murder"
 *   "Causing Death by Negligence"                      \u2192 "Causing Death by Negligence"
 *   "Acts Done by Several Persons in Furtherance\u2026"   \u2192 "Acts Done by Several Persons"
 *
 * @param {string} crimeName \u2013 Full crime name from PPC/ATA section
 * @returns {string} Short label (never empty; falls back to trimmed input)
 */
export function ppcSimpleLabel(crimeName) {
  if (!crimeName || typeof crimeName !== 'string') return '';
  const name = crimeName.trim();

  // "Punishment for X" / "Penalty for X" / "Sentence for X" / "Offence of X"
  let m = name.match(/^(?:punishment|penalty|sentence|offence)\s+for\s+(.+)/i);
  if (m) {
    let label = m[1].trim();
    // Strip trailing "(Section \u2026)" or "under Section \u2026"
    label = label.replace(/\s*\(section\s+\d+[^\)]*\)/i, '').replace(/\s+under\s+section.+$/i, '').trim();
    return capitalize(label);
  }

  // "Attempt to Commit X" \u2192 "Attempted X"
  m = name.match(/^attempt\s+to\s+commit\s+(.+)/i);
  if (m) return `Attempted ${capitalize(m[1].trim())}`;

  // "Acts Done by Several Persons in Furtherance of Common Intention"
  // \u2192 trim long names at natural break
  if (name.length > 45) {
    const shortened = name.replace(/\s+in\s+furtherance.*$/i, '')
                          .replace(/\s+under.*$/i, '')
                          .replace(/\s+by\s+way.*$/i, '');
    if (shortened.length < name.length) return capitalize(shortened.trim());
    // Hard truncate at word boundary
    const words = name.split(' ');
    return words.slice(0, 6).join(' ') + (words.length > 6 ? '\u2026' : '');
  }

  return name;
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}
