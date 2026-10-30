export const ROUTES = [
  { hash: '#/territoires-acteurs', label: 'Territoires & acteurs' },
  { hash: '#/maintenance', label: 'Maintenance' },
  { hash: '#/recherche', label: 'Recherche' },
]

export default function AppNav({ current }: { current: string }) {
  return <nav className="app-nav">
    {ROUTES.map((route) => <a key={route.hash} href={route.hash} className={route.hash === current ? 'active' : undefined} aria-current={route.hash === current ? 'page' : undefined}>{route.label}</a>)}
  </nav>
}
