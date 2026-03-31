import { motion } from 'framer-motion'

type Props = {
  text: string
  className?: string
}

/** Renders streamed markdown-ish text with subtle fade-in. */
export function StreamText({ text, className = '' }: Props) {
  return (
    <motion.div
      className={`whitespace-pre-wrap text-sm leading-relaxed text-violet-100/90 ${className}`}
      initial={{ opacity: 0.85 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      {text}
    </motion.div>
  )
}
