
// Universal logger: only uses console for compatibility with Next.js app dir
export function logToFile(message: string, level: 'info' | 'warn' | 'error' = 'info') {
  const entry = `${new Date().toISOString()} [${level.toUpperCase()}] ${message}`;
  // eslint-disable-next-line no-console
  if (typeof console[level] === 'function') {
    console[level](entry);
  } else {
    console.log(entry);
  }
}
