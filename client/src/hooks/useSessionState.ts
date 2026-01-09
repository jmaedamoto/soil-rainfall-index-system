import { useReducer, useCallback } from 'react';
import { LightweightPrefectureData, LightweightCalculationResult } from '../types/api';

// Session state interface
interface SessionState {
  // Session data
  sessionId: string | null;
  sessionInfo: LightweightCalculationResult | null;

  // Prefecture data (risk timelines)
  prefectureRiskData: Record<string, LightweightPrefectureData>;

  // Map display data (mesh risks at specific time)
  meshRisksAtTime: Record<string, number>;
  meshCoords: Record<string, { lat: number; lon: number }>;

  // UI state
  loading: boolean;
  loadingPrefecture: string | null;
  error: string | null;
  isTimeChanging: boolean;

  // Selection state
  selectedTime: number;
  selectedPrefecture: string;

  // Initial times
  swiInitialTime: string;
  guidanceInitialTime: string;

  // Flags
  isAdjustedData: boolean;
}

// Action types
type SessionAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_SESSION_INFO'; payload: { sessionId: string; sessionInfo: LightweightCalculationResult } }
  | { type: 'SET_PREFECTURE_DATA'; payload: { prefectureCode: string; data: LightweightPrefectureData } }
  | { type: 'SET_MESH_RISKS'; payload: { meshRisks: Record<string, number>; meshCoords: Record<string, { lat: number; lon: number }> } }
  | { type: 'SET_SELECTED_TIME'; payload: number }
  | { type: 'SET_SELECTED_PREFECTURE'; payload: string }
  | { type: 'SET_LOADING_PREFECTURE'; payload: string | null }
  | { type: 'SET_TIME_CHANGING'; payload: boolean }
  | { type: 'SET_INITIAL_TIMES'; payload: { swi: string; guidance: string } }
  | { type: 'SET_ADJUSTED_DATA'; payload: boolean }
  | { type: 'RESET_SESSION' };

// Initial state
const initialState: SessionState = {
  sessionId: null,
  sessionInfo: null,
  prefectureRiskData: {},
  meshRisksAtTime: {},
  meshCoords: {},
  loading: false,
  loadingPrefecture: null,
  error: null,
  isTimeChanging: false,
  selectedTime: 0,
  selectedPrefecture: '',
  swiInitialTime: '',
  guidanceInitialTime: '',
  isAdjustedData: false
};

// Reducer
function sessionReducer(state: SessionState, action: SessionAction): SessionState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };

    case 'SET_ERROR':
      return { ...state, error: action.payload };

    case 'SET_SESSION_INFO':
      return {
        ...state,
        sessionId: action.payload.sessionId,
        sessionInfo: action.payload.sessionInfo
      };

    case 'SET_PREFECTURE_DATA':
      return {
        ...state,
        prefectureRiskData: {
          ...state.prefectureRiskData,
          [action.payload.prefectureCode]: action.payload.data
        }
      };

    case 'SET_MESH_RISKS':
      return {
        ...state,
        meshRisksAtTime: action.payload.meshRisks,
        meshCoords: action.payload.meshCoords
      };

    case 'SET_SELECTED_TIME':
      return { ...state, selectedTime: action.payload };

    case 'SET_SELECTED_PREFECTURE':
      return { ...state, selectedPrefecture: action.payload };

    case 'SET_LOADING_PREFECTURE':
      return { ...state, loadingPrefecture: action.payload };

    case 'SET_TIME_CHANGING':
      return { ...state, isTimeChanging: action.payload };

    case 'SET_INITIAL_TIMES':
      return {
        ...state,
        swiInitialTime: action.payload.swi,
        guidanceInitialTime: action.payload.guidance
      };

    case 'SET_ADJUSTED_DATA':
      return { ...state, isAdjustedData: action.payload };

    case 'RESET_SESSION':
      return {
        ...initialState,
        swiInitialTime: state.swiInitialTime,
        guidanceInitialTime: state.guidanceInitialTime
      };

    default:
      return state;
  }
}

// Custom hook
export function useSessionState() {
  const [state, dispatch] = useReducer(sessionReducer, initialState);

  // Action creators
  const setLoading = useCallback((loading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: loading });
  }, []);

  const setError = useCallback((error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  }, []);

  const setSessionInfo = useCallback((sessionId: string, sessionInfo: LightweightCalculationResult) => {
    dispatch({ type: 'SET_SESSION_INFO', payload: { sessionId, sessionInfo } });
  }, []);

  const setPrefectureData = useCallback((prefectureCode: string, data: LightweightPrefectureData) => {
    dispatch({ type: 'SET_PREFECTURE_DATA', payload: { prefectureCode, data } });
  }, []);

  const setMeshRisks = useCallback((meshRisks: Record<string, number>, meshCoords: Record<string, { lat: number; lon: number }>) => {
    dispatch({ type: 'SET_MESH_RISKS', payload: { meshRisks, meshCoords } });
  }, []);

  const setSelectedTime = useCallback((time: number) => {
    dispatch({ type: 'SET_SELECTED_TIME', payload: time });
  }, []);

  const setSelectedPrefecture = useCallback((prefecture: string) => {
    dispatch({ type: 'SET_SELECTED_PREFECTURE', payload: prefecture });
  }, []);

  const setLoadingPrefecture = useCallback((prefecture: string | null) => {
    dispatch({ type: 'SET_LOADING_PREFECTURE', payload: prefecture });
  }, []);

  const setTimeChanging = useCallback((isChanging: boolean) => {
    dispatch({ type: 'SET_TIME_CHANGING', payload: isChanging });
  }, []);

  const setInitialTimes = useCallback((swi: string, guidance: string) => {
    dispatch({ type: 'SET_INITIAL_TIMES', payload: { swi, guidance } });
  }, []);

  const setAdjustedData = useCallback((isAdjusted: boolean) => {
    dispatch({ type: 'SET_ADJUSTED_DATA', payload: isAdjusted });
  }, []);

  const resetSession = useCallback(() => {
    dispatch({ type: 'RESET_SESSION' });
  }, []);

  return {
    // State
    ...state,
    // Actions
    setLoading,
    setError,
    setSessionInfo,
    setPrefectureData,
    setMeshRisks,
    setSelectedTime,
    setSelectedPrefecture,
    setLoadingPrefecture,
    setTimeChanging,
    setInitialTimes,
    setAdjustedData,
    resetSession
  };
}
