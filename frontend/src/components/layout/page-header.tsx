"use client"

interface PageHeaderProps {
  title: string
  children?: React.ReactNode
}

export function PageHeader({ title, children }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-5">
      <h1 className="text-xl font-bold text-gray-100">{title}</h1>
      {children}
    </div>
  )
}
