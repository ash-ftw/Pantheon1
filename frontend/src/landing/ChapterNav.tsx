import { CHAPTERS, type ChapterDef } from './types';

interface ChapterNavProps {
  activeChapterId: string;
  onSelectChapter: (id: string) => void;
}

export function ChapterNav({ activeChapterId, onSelectChapter }: ChapterNavProps) {
  return (
    <nav className="chapter-side-nav" aria-label="Narrative Chapters Navigation">
      <div className="chapter-side-nav-inner">
        <div className="chapter-nav-guideline" />

        {CHAPTERS.map((chapter: ChapterDef) => {
          const isActive = chapter.id === activeChapterId;
          return (
            <button
              key={chapter.id}
              type="button"
              className={`chapter-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectChapter(chapter.id)}
              title={chapter.title}
              data-testid={`chapter-nav-${chapter.id}`}
            >
              <div className="chapter-nav-indicator" />
              <div className="chapter-nav-label-box">
                <span className="chapter-nav-num">{chapter.numeral}</span>
                <span className="chapter-nav-text">{chapter.label}</span>
              </div>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
