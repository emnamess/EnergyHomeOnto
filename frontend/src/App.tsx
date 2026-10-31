import { useEffect, useState } from 'react'
import TerritoriesActorsPage from './features/territoires-acteurs/TerritoriesActorsPage'
import MaintenancePage from './features/maintenance/MaintenancePage'
import StockagePage from './features/stockage/StockagePage'
import IntelligentSearchPage from './shared/recherche-intelligente/IntelligentSearchPage'
import DashboardPage from './shared/tableau-de-bord/DashboardPage'
import { Layout } from './shared/Layout'

// « #/recherche?q=maisons » -> route « #/recherche » et paramètre q.
function readLocation() {
  const [route, search = ''] = window.location.hash.split('?')
  return { route, params: new URLSearchParams(search) }
}

export default function App() {
  const [location, setLocation] = useState(readLocation)

  useEffect(() => {
    const onHashChange = () => {
      setLocation(readLocation())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const { route, params } = location
  const query = params.get('q') ?? undefined
  if (route === '#/recherche') return <Layout current={route}><IntelligentSearchPage key={query} initialQuery={query} /></Layout>
  if (route === '#/territoires-acteurs') return <Layout current={route}><TerritoriesActorsPage /></Layout>
  if (route === '#/stockage') return <Layout current={route}><StockagePage /></Layout>
  if (route === '#/maintenance') return <Layout current={route}><MaintenancePage /></Layout>
  return <Layout current="#/tableau-de-bord"><DashboardPage /></Layout>
}
