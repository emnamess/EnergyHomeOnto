import { FormEvent, useEffect, useState } from 'react'
import { PageHeader } from '../Layout'

type Token = { texte: string; lemme: string; categorie: string; dependance: string; tete: string }
type Entity = { texte: string; nature: string; iri: string; negation: boolean }
type SearchResponse = {
  interpretation: string
  sparql: string
  results: Array<Record<string, string>>
  analyse: { tokens?: Token[]; entites?: Entity[]; comptage?: boolean }
}

const EXAMPLES = [
  'Liste les maisons autonomes qui possèdent un panneau solaire',
  'maisons sans panneau solaire',
  'lignes gérées par la STEG',
  'batteries avec une capacité supérieure à 20',
  'Combien de maisons à Tunis ?',
  'quel est le panneau solaire le plus puissant',
  'Dans quel quartier se trouve la maison 1 ?',
]
const NATURES: Record<string, string> = { classe: 'Classe', objet: 'Relation', donnee: 'Donnée', individu: 'Individu' }

const display = (value: string) => value.startsWith('http') ? value.split('#').pop() ?? value : value

export default function IntelligentSearchPage({ initialQuery }: { initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery ?? EXAMPLES[0])
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function run(question: string) {
    setLoading(true)
    setError('')
    setResponse(null)
    try {
      const result = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: question }),
      })
      if (result.status === 400) throw new Error((await result.json()).detail)
      if (!result.ok) throw new Error(`Le serveur répond avec le statut ${result.status}. Vérifiez que l’API Python tourne sur le port 8000.`)
      setResponse(await result.json())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'La recherche a échoué.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (initialQuery) run(initialQuery)
  }, [])

  function submit(event: FormEvent) {
    event.preventDefault()
    run(query)
  }

  function example(question: string) {
    setQuery(question)
    run(question)
  }

  const columns = response ? [...new Set(response.results.flatMap((row) => Object.keys(row)))] : []
  return (
    <>
      <PageHeader eyebrow="Module NLP commun" title="Recherche intelligente">
        Posez votre question en français. spaCy l’analyse, l’ontologie guide sa traduction en SPARQL, puis la requête s’exécute sur le graphe enrichi par le raisonneur OWL.
      </PageHeader>
      <section>
        <form className="card search-card" onSubmit={submit}>
          <label htmlFor="query">Votre question</label>
          <div className="search-row">
            <input id="query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ex. maisons avec un panneau solaire" />
            <button disabled={loading || !query.trim()}>{loading ? 'Recherche…' : 'Rechercher'} <span aria-hidden="true">↗</span></button>
          </div>
          <div className="examples">{EXAMPLES.map((item) => <button type="button" key={item} onClick={() => example(item)}>{item}</button>)}</div>
        </form>
        {error && <p className="notice error">{error}</p>}
        {response && <section className="card results">
          <h2>{response.interpretation}</h2>
          <p className="muted">{response.results.length} résultat(s)</p>
          {response.results.length > 0 && <div className="table-wrap"><table>
            <thead><tr>{columns.map((column) => <th key={column}>{column === 'x' ? 'élément' : column}</th>)}</tr></thead>
            <tbody>{response.results.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{row[column] ? display(row[column]) : '—'}</td>)}</tr>)}</tbody>
          </table></div>}
          {response.analyse.entites && <div className="analysis">
            <h3>Analyse spaCy</h3>
            <div className="entities">{response.analyse.entites.map((entity, index) => <span key={index} className={entity.negation ? 'entity negated' : 'entity'}><small>{NATURES[entity.nature] ?? entity.nature}{entity.negation ? ' · négation' : ''}</small>{entity.texte} → :{entity.iri}</span>)}</div>
            <details><summary>Tokens, lemmes et dépendances</summary><div className="table-wrap"><table>
              <thead><tr><th>token</th><th>lemme</th><th>catégorie</th><th>dépendance</th><th>tête</th></tr></thead>
              <tbody>{response.analyse.tokens?.map((token, index) => <tr key={index}><td>{token.texte}</td><td>{token.lemme}</td><td>{token.categorie}</td><td>{token.dependance}</td><td>{token.tete}</td></tr>)}</tbody>
            </table></div></details>
          </div>}
          <details><summary>Requête SPARQL générée</summary><pre>{response.sparql}</pre></details>
        </section>}
      </section>
    </>
  )
}
