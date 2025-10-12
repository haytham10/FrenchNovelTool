/**
 * Lightweight date utilities using native Intl API
 * Replacement for date-fns to reduce bundle size
 */

/**
 * Format a date to a short format (e.g., "Jan 15")
 */
export const formatDate = (date: Date | string): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
  }).format(dateObj);
};

/**
 * Format distance from now (e.g., "2 hours ago", "3 days ago")
 */
export const formatDistanceToNow = (date: Date | string, options?: { addSuffix?: boolean }): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - dateObj.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffWeek = Math.floor(diffDay / 7);
  const diffMonth = Math.floor(diffDay / 30);
  const diffYear = Math.floor(diffDay / 365);

  const addSuffix = options?.addSuffix !== false;
  const suffix = addSuffix ? ' ago' : '';

  if (diffYear > 0) {
    return `${diffYear} year${diffYear > 1 ? 's' : ''}${suffix}`;
  }
  if (diffMonth > 0) {
    return `${diffMonth} month${diffMonth > 1 ? 's' : ''}${suffix}`;
  }
  if (diffWeek > 0) {
    return `${diffWeek} week${diffWeek > 1 ? 's' : ''}${suffix}`;
  }
  if (diffDay > 0) {
    return `${diffDay} day${diffDay > 1 ? 's' : ''}${suffix}`;
  }
  if (diffHour > 0) {
    return `${diffHour} hour${diffHour > 1 ? 's' : ''}${suffix}`;
  }
  if (diffMin > 0) {
    return `${diffMin} minute${diffMin > 1 ? 's' : ''}${suffix}`;
  }
  return `${diffSec} second${diffSec !== 1 ? 's' : ''}${suffix}`;
};

/**
 * Format a date to full format (e.g., "January 15, 2024")
 */
export const formatDateLong = (date: Date | string): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(dateObj);
};

/**
 * Format a date and time (e.g., "Jan 15, 2024 2:30 PM")
 */
export const formatDateTime = (date: Date | string): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(dateObj);
};
