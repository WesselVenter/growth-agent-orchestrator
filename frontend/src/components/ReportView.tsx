import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * The final report is markdown with headers, bold, emoji, and GFM tables
 * (the Coordinator writes full ranking tables). It must be rendered
 * through a real markdown renderer — not <pre> / raw text — or the tables
 * and formatting just show up as literal asterisks and pipes.
 */
export default function ReportView({ markdown }: { markdown: string }) {
  return (
    <div className="prose prose-sm sm:prose-base max-w-none rounded-lg border bg-white p-6 shadow-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </div>
  )
}
