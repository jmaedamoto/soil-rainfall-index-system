export type RegionCode = 'kinki' | 'chugoku' | 'shikoku';

export interface RegionConfig {
  code: RegionCode;
  name: string;
  prefectureCodes: string[];
  prefectureNames: string[];
  path: string;
}

export const REGION_CONFIGS: Record<RegionCode, RegionConfig> = {
  kinki: {
    code: 'kinki',
    name: '近畿地方',
    path: '/kinki',
    prefectureCodes: ['shiga', 'kyoto', 'hyogo', 'osaka', 'nara', 'wakayama'],
    prefectureNames: ['滋賀県', '京都府', '兵庫県', '大阪府', '奈良県', '和歌山県'],
  },
  chugoku: {
    code: 'chugoku',
    name: '中国地方',
    path: '/chugoku',
    prefectureCodes: ['tottori', 'okayama', 'hiroshima', 'shimane'],
    prefectureNames: ['鳥取県', '岡山県', '広島県', '島根県'],
  },
  shikoku: {
    code: 'shikoku',
    name: '四国地方',
    path: '/shikoku',
    prefectureCodes: ['ehime', 'tokushima', 'kagawa', 'kochi'],
    prefectureNames: ['愛媛県', '徳島県', '香川県', '高知県'],
  },
};
