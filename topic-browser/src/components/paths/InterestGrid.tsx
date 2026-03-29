import { INTEREST_TILES, type InterestId } from '../../data/interestBuckets'

interface InterestGridProps {
  onSelectInterest: (interestId: InterestId) => void
}

export function InterestGrid({ onSelectInterest }: InterestGridProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-zinc-100">
        What do you want to get better at?
      </h2>
      <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {INTEREST_TILES.map((tile) => (
          <li key={tile.id}>
            <button
              type="button"
              onClick={() => onSelectInterest(tile.id)}
              className="flex w-full flex-col items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900/60 px-4 py-5 text-center transition-colors hover:border-violet-500/50 hover:bg-zinc-800/80"
            >
              <span className="text-2xl" aria-hidden>
                {tile.icon}
              </span>
              <span className="text-sm font-medium text-zinc-100">
                {tile.label}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
