export interface RainfallPreviewColorStop {
  /** Rainfall threshold in millimeters represented by this color. */
  threshold: number;
  label: string;
  color: string;
}

// Color thresholds follow the rainfall reference image (mm/3h). Zero is
// intentionally white; positive rainfall uses the reference's discrete bands.
export const RAIN_PREVIEW_LEGEND: RainfallPreviewColorStop[] = [
  { threshold: 0, label: '0', color: '#ffffff' },
  { threshold: 1, label: '1', color: '#0077c6' },
  { threshold: 2, label: '2', color: '#003c6c' },
  { threshold: 4, label: '4', color: '#0006f0' },
  { threshold: 8, label: '8', color: '#009375' },
  { threshold: 12, label: '12', color: '#00b347' },
  { threshold: 16, label: '16', color: '#00e10c' },
  { threshold: 24, label: '24', color: '#46ff09' },
  { threshold: 32, label: '32', color: '#7cce02' },
  { threshold: 40, label: '40', color: '#ffff00' },
  { threshold: 48, label: '48', color: '#ff8000' },
  { threshold: 56, label: '56', color: '#ff86ff' },
  { threshold: 64, label: '64', color: '#fe45a2' },
  { threshold: 80, label: '80+', color: '#ff0000' },
];

export function getRainPreviewColor(value: number): string {
  if (value <= 0) return RAIN_PREVIEW_LEGEND[0].color;

  let colorStop = RAIN_PREVIEW_LEGEND[1];
  for (const stop of RAIN_PREVIEW_LEGEND.slice(1)) {
    if (value < stop.threshold) break;
    colorStop = stop;
  }
  return colorStop.color;
}
