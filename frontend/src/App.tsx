import { useEffect, useState } from 'react'
import TerritoriesActorsPage from './features/territoires-acteurs/TerritoriesActorsPage'
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

  return route === '#/recherche' ? <IntelligentSearchPage /> : <TerritoriesActorsPage />
}
