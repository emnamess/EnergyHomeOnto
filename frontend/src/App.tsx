import { useEffect, useState } from 'react'
import TerritoriesActorsPage from './features/territoires-acteurs/TerritoriesActorsPage'
import MaintenancePage from './features/maintenance/MaintenancePage'
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
  if (route === '#/maintenance') return <MaintenancePage />
  return <TerritoriesActorsPage />
}
