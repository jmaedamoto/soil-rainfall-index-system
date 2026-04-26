export const MSM_HOUR_OPTIONS = [0, 3, 6, 9, 12, 15, 18, 21];
export const GSM_HOUR_OPTIONS = [0, 6, 12, 18];

export interface DefaultDateTimeSelection {
  date: string;
  hour: number;
}

export const getGuidanceHourOptions = (guidanceType: 'msm' | 'gsm'): number[] => {
  return guidanceType === 'gsm' ? GSM_HOUR_OPTIONS : MSM_HOUR_OPTIONS;
};

export const buildIsoStringFromJst = (date: string, hour: number): string => {
  if (!date) return '';
  const jstDate = new Date(`${date}T${hour.toString().padStart(2, '0')}:00:00+09:00`);
  return jstDate.toISOString();
};

export const getDefaultJstSelection = (
  guidanceType: 'msm' | 'gsm' = 'msm'
): DefaultDateTimeSelection => {
  const now = new Date();
  const jstNow = new Date(now.getTime() + 9 * 60 * 60 * 1000 - 3 * 60 * 60 * 1000);
  const year = jstNow.getUTCFullYear();
  const month = (jstNow.getUTCMonth() + 1).toString().padStart(2, '0');
  const day = jstNow.getUTCDate().toString().padStart(2, '0');
  const hourStep = guidanceType === 'gsm' ? 6 : 3;
  const hour = Math.floor(jstNow.getUTCHours() / hourStep) * hourStep;

  return {
    date: `${year}-${month}-${day}`,
    hour,
  };
};

export const formatIsoDateTimeToJst = (isoString: string): string => {
  const date = new Date(isoString);
  const jstDate = new Date(date.getTime() + 9 * 60 * 60 * 1000);
  return `${jstDate.getUTCFullYear()}年${jstDate.getUTCMonth() + 1}月${jstDate.getUTCDate()}日 ${jstDate.getUTCHours()}時 (JST)`;
};
