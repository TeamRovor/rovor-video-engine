'use strict';

const cache = new Map();

function wrapCaption(text, maxChars = 34, maxLines = 3) {
  const limit = Math.max(1, Math.floor(maxChars));
  const lineLimit = Math.max(1, Math.floor(maxLines));
  const source = String(text || '').trim();
  const key = `${limit}:${lineLimit}:${source}`;
  if (cache.has(key)) return [...cache.get(key)];
  const words = source.split(/\s+/).filter(Boolean);
  if (!words.length) return [];

  const chunks = words.flatMap(word => {
    if (word.length <= limit) return [word];
    return word.match(new RegExp(`.{1,${limit}}`, 'g')) || [word];
  });
  const lines = [];
  let truncated = false;

  for (const chunk of chunks) {
    if (!lines.length) {
      lines.push(chunk);
    } else {
      const last = lines.length - 1;
      if (lines[last].length + 1 + chunk.length <= limit) {
        lines[last] += ' ' + chunk;
      } else if (lines.length < lineLimit) {
        lines.push(chunk);
      } else {
        truncated = true;
        break;
      }
    }
  }

  if (truncated) {
    const last = lines.length - 1;
    lines[last] = lines[last].slice(0, Math.max(0, limit - 1)).trimEnd() + '…';
  }
  cache.set(key, lines);
  return [...lines];
}

module.exports = {wrapCaption};

