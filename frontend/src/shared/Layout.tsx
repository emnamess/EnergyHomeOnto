import { ReactNode, useEffect, useState } from 'react'

export type Route = { hash: string; label: string; icon: string; ready: boolean }

// Pour ajouter une page : passer `ready` à true et la déclarer dans App.tsx.
export const SECTIONS: Array<{ title: string; routes: Route[] }> = [
  {
    title: 'Vue d’ensemble',
    routes: [
      { hash: '#/tableau-de-bord', label: 'Tableau de bord', icon: '◧', ready: true },
      { hash: '#/recherche', label: 'Recherche intelligente', icon: '⌕', ready: true },
    ],
  },
  {
    title: 'Features',
    routes: [
      { hash: '#/batiments', label: 'Bâtiments', icon: '⌂', ready: false },
      { hash: '#/production', label: 'Production', icon: '☀', ready: false },
      { hash: '#/stockage', label: 'Stockage', icon: '▤', ready: false },
      { hash: '#/reseau', label: 'Réseau', icon: '⌁', ready: false },
      { hash: '#/territoires-acteurs', label: 'Territoires & acteurs', icon: '◎', ready: true },
    ],
  },
]

type Health = { triplets_asserts: number; triplets_inferes: number }

function ApiStatus() {
  const [health, setHealth] = useState<Health | null | undefined>(undefined)

  useEffect(() => {
    const check = () => fetch('/api/health').then((r) => (r.ok ? r.json() : null)).then(setHealth).catch(() => setHealth(null))
    check()
    const timer = setInterval(check, 15000)
    return () => clearInterval(timer)
  }, [])

  if (health === undefined) return <div className="api-status"><span className="dot" />Connexion à l’API…</div>
  if (health === null) return <div className="api-status down"><span className="dot" aria-hidden="true" />API injoignable<small>Lancez le backend (port 8000)</small></div>
  return <div className="api-status up"><span className="dot" aria-hidden="true" />API connectée<small>{health.triplets_inferes.toLocaleString('fr-FR')} triplets après raisonnement</small></div>
}

export function Layout({ current, children }: { current: string; children: ReactNode }) {
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#/tableau-de-bord"><span className="brand-mark">E</span><span>EnergyHome<small>Web sémantique</small></span></a>
      <nav aria-label="Navigation principale">
        {SECTIONS.map((section) => <div key={section.title} className="nav-section">
          <p>{section.title}</p>
          {section.routes.map((route) => route.ready
            ? <a key={route.hash} href={route.hash} className={route.hash === current ? 'nav-link active' : 'nav-link'} aria-current={route.hash === current ? 'page' : undefined}><span className="nav-icon" aria-hidden="true">{route.icon}</span>{route.label}</a>
            : <span key={route.hash} className="nav-link disabled" title="En cours de développement"><span className="nav-icon" aria-hidden="true">{route.icon}</span>{route.label}<em>à venir</em></span>)}
        </div>)}
      </nav>
      <ApiStatus />
    </aside>
    <main className="content">{children}</main>
  </div>
}

export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return <header className="page-header">
    <p className="eyebrow">{eyebrow}</p>
    <h1>{title}</h1>
    {children && <p className="lead">{children}</p>}
  </header>
}
