import { FormEvent, useState } from 'react'

type SearchResponse = {
  interpretation: string
  sparql: string
  results: Array<Record<string, string>>
}

export default function App() {
  const [query, setQuery] = useState('Liste les maisons autonomes qui possèdent un panneau solaire')
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function search(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResponse(null)
    try {
      const result = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      if (!result.ok) throw new Error(`Le serveur répond avec le statut ${result.status}.`)
      setResponse(await result.json())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'La recherche a échoué.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page">
      <header className="topbar"><span className="brand-mark">E</span><span>EnergyHome</span><span className="tag">WEB SÉMANTIQUE</span></header>
      <section className="hero">
        <p className="eyebrow">L’ÉNERGIE, EN CLAIR</p>
        <h1>Interrogez votre<br /><em>habitat énergétique.</em></h1>
        <p className="intro">Posez votre question simplement. Le moteur local la transforme en recherche sémantique.</p>
        <form className="search-card" onSubmit={search}>
          <label htmlFor="query">VOTRE QUESTION</label>
          <div className="search-row">
            <input id="query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ex. maisons avec un panneau solaire" />
            <button disabled={loading || !query.trim()}>{loading ? 'Recherche…' : 'Rechercher'} <span aria-hidden="true">↗</span></button>
          </div>
          <p className="hint">Essayez : « maisons autonomes avec un panneau solaire »</p>
        </form>
        {error && <p className="notice error">{error} Vérifiez que l’API tourne sur le port 8080.</p>}
        {response && <section className="results"><h2>{response.interpretation}</h2><pre>{response.sparql}</pre><p>{response.results.length} résultat(s)</p></section>}
      </section>
      <footer><span>Une ontologie pour mieux comprendre les ressources énergétiques.</span><span>OWL · SPARQL · Apache Jena</span></footer>
    </main>
  )
}
