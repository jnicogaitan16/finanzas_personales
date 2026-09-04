export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-white/[0.06] rounded-xl ${className}`} />
  )
}

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`bg-white/[0.03] border border-white/5 rounded-2xl p-5 space-y-3 ${className}`}>
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-7 w-32" />
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-5 animate-in fade-in duration-300">
      {/* Balance */}
      <div className="space-y-2">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-9 w-48" />
      </div>

      {/* Month selector */}
      <Skeleton className="h-10 w-full rounded-xl" />

      {/* KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      {/* Category donut */}
      <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
        <div className="flex gap-2 mb-4">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-14 w-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-52 w-52 rounded-full mx-auto" />
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <SkeletonCard className="h-48" />
        <SkeletonCard className="h-48" />
      </div>
    </div>
  )
}
