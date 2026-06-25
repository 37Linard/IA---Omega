import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Agente IA Local',
  description: 'Seu assistente de IA local com ferramentas poderosas',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="h-full">
      <body className="h-full bg-neutral-950 text-neutral-100 antialiased">{children}</body>
    </html>
  )
}
