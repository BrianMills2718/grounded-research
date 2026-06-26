/**
 * JSONTreeViewer — collapsible JSON tree using @uiw/react-json-view.
 *
 * Styled to integrate with the dark CSS variable theme.
 * Copy-paste into any project that has @uiw/react-json-view installed.
 */
import JsonView from '@uiw/react-json-view'
import { darkTheme } from '@uiw/react-json-view/dark'

interface Props {
  data: unknown
  /** Depth to collapse by default (default: 2) */
  collapsed?: number
}

export default function JSONTreeViewer({ data, collapsed = 2 }: Props) {
  return (
    <JsonView
      value={data as object}
      style={{
        ...darkTheme,
        background: 'var(--bg)',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        lineHeight: 1.6,
      }}
      collapsed={collapsed}
      displayDataTypes={false}
      displayObjectSize
      enableClipboard
    />
  )
}
