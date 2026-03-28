import type { Video } from '../../types'

function difficultyClass(d: string): string {
  if (d === 'beginner') return 'bg-emerald-900/70 text-emerald-200'
  if (d === 'advanced') return 'bg-red-900/70 text-red-200'
  return 'bg-amber-900/70 text-amber-200'
}

interface VideoCardProps {
  video: Video
}

export function VideoCard({ video }: VideoCardProps) {
  const wc = video.wordcloud_path?.trim()
  const imgSrc = wc ? `/${wc.replace(/^\//, '')}` : ''

  return (
    <article className="flex flex-col rounded-lg border border-zinc-700/80 bg-zinc-900/60 p-4 shadow-sm">
      <h3 className="text-base font-medium leading-snug text-zinc-100">
        {video.url ? (
          <a
            href={video.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-violet-300 hover:text-violet-200 hover:underline"
          >
            {video.title || 'Open on Locals'}
          </a>
        ) : (
          <span>{video.title || '(no title)'}</span>
        )}{' '}
        <span
          className={`ml-1 inline-block rounded px-1.5 py-0.5 align-middle text-xs ${difficultyClass(video.difficulty || 'intermediate')}`}
        >
          {video.difficulty || 'intermediate'}
        </span>
      </h3>
      <p className="mt-2 line-clamp-4 text-sm text-zinc-400">
        {video.core_lesson || video.summary_text || ''}
      </p>
      {video.topics.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1">
          {video.topics.map((t) => (
            <span
              key={t.id}
              className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300"
            >
              {t.name}
            </span>
          ))}
        </div>
      ) : null}
      {video.cluster ? (
        <p className="mt-2 text-xs text-zinc-500">
          Cluster: {video.cluster.name}
        </p>
      ) : null}
      {imgSrc ? (
        <img
          src={imgSrc}
          alt=""
          className="mt-3 h-24 w-full rounded object-cover"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.style.display = 'none'
          }}
        />
      ) : null}
    </article>
  )
}
