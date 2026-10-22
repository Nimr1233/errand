// CSV with RFC 4180 quoting (spec sections 5 and 8).
const cell = (s: string): string => /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
export const toCSV = (columns: string[], rows: string[][]): string =>
  [columns, ...rows].map(r => r.map(cell).join(',')).join('\r\n')
export const toTSV = (columns: string[], rows: string[][]): string =>
  [columns, ...rows].map(r => r.join('\t')).join('\n')
