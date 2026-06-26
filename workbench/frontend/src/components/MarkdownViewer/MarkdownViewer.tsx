import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './MarkdownViewer.css'

interface Props {
  content: string
  className?: string
}

export default function MarkdownViewer({ content, className }: Props) {
  return (
    <div className={`md-viewer ${className ?? ''}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}
