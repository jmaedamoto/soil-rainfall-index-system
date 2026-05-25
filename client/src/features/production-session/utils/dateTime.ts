export const MSM_HOUR_OPTIONS = [0, 3, 6, 9, 12, 15, 18, 21];
export const GSM_HOUR_OPTIONS = [3, 9, 15, 21];

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
  const allowedHours = getGuidanceHourOptions(guidanceType);
  let selectionDate = new Date(jstNow);
  let hour = [...allowedHours].reverse().find((candidate) => candidate <= jstNow.getUTCHours());

  if (hour === undefined) {
    selectionDate = new Date(selectionDate.getTime() - 24 * 60 * 60 * 1000);
    hour = allowedHours[allowedHours.length - 1];
  }

  const year = selectionDate.getUTCFullYear();
  const month = (selectionDate.getUTCMonth() + 1).toString().padStart(2, '0');
  const day = selectionDate.getUTCDate().toString().padStart(2, '0');

  return {
    date: `${year}-${month}-${day}`,
    hour: hour ?? allowedHours[0],
  };
};

export const formatIsoDateTimeToJst = (isoString: string): string => {
  const date = new Date(isoString);
  const jstDate = new Date(date.getTime() + 9 * 60 * 60 * 1000);
  return `${jstDate.getUTCFullYear()}年${jstDate.getUTCMonth() + 1}月${jstDate.getUTCDate()}日 ${jstDate.getUTCHours()}時 (JST)`;
};
