export const CHAPTER_SELECTORS = [
  '#top',
  '#problem',
  '#laws',
  '#protocol',
  '#proof',
  '#self-telemetry',
  '#final-cta',
] as const;

export type SceneQuality = 'high' | 'low';

interface ChapterFrame {
  progress: number;
  weight: number;
}

interface NarrativeState {
  activeChapter: number;
  chapters: ChapterFrame[];
  pointerX: number;
  pointerY: number;
  scrollVelocity: number;
  theme: number;
}

const narrativeState: NarrativeState = {
  activeChapter: 0,
  chapters: CHAPTER_SELECTORS.map((_, index) => ({
    progress: 0,
    weight: index === 0 ? 1 : 0,
  })),
  pointerX: 0,
  pointerY: 0,
  scrollVelocity: 0,
  theme: 0,
};

const smoothstep = (start: number, end: number, value: number): number => {
  const x = Math.min(1, Math.max(0, (value - start) / (end - start)));
  return x * x * (3 - 2 * x);
};

function chapterWeight(index: number, progress: number): number {
  if (index === 0) return 1 - smoothstep(0.58, 1, progress);
  if (index === CHAPTER_SELECTORS.length - 1) return smoothstep(0, 0.38, progress);
  return smoothstep(0, 0.24, progress) * (1 - smoothstep(0.76, 1, progress));
}

export function setChapterFrame(index: number, progress: number): void {
  const chapter = narrativeState.chapters[index];
  if (!chapter) return;
  chapter.progress = progress;
  chapter.weight = chapterWeight(index, progress);

  let strongestIndex = narrativeState.activeChapter;
  let strongestWeight = -1;
  narrativeState.chapters.forEach((frame, frameIndex) => {
    if (frame.weight > strongestWeight) {
      strongestIndex = frameIndex;
      strongestWeight = frame.weight;
    }
  });
  narrativeState.activeChapter = strongestIndex;
}

export function setNarrativeInput(
  input: Partial<Pick<NarrativeState, 'pointerX' | 'pointerY' | 'scrollVelocity' | 'theme'>>,
): void {
  Object.assign(narrativeState, input);
}

export function readNarrative(): Readonly<NarrativeState> {
  return narrativeState;
}