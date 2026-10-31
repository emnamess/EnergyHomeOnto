import { useEffect, useState } from 'react'
import TerritoriesActorsPage from './features/territoires-acteurs/TerritoriesActorsPage'
import BuildingsPage from './features/batiments/BuildingsPage'
import MaintenancePage from './features/maintenance/MaintenancePage'
import StockagePage from './features/stockage/StockagePage'
import IntelligentSearchPage from './shared/recherche-intelligente/IntelligentSearchPage'
import { ROUTES } from './shared/AppNav'

const currentRoute = () => ROUTES.find((route) => route.hash === window.location.hash)?.hash ?? ROUTES[0].hash

export default function App() {
  const [route, setRoute] = useState(currentRoute)

  useEffect(() => {
    const onHashChange = () => setRoute(currentRoute())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  if (route === '#/recherche') return <IntelligentSearchPage />
  if (route === '#/batiments') return <BuildingsPage />
  if (route === '#/maintenance') return <MaintenancePage />
  if (route === '#/stockage') return <StockagePage />
  return <TerritoriesActorsPage />
}
