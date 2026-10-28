import { FormEvent, useEffect, useState } from 'react'
import { PageHeader } from '../Layout'

type Family = { id: string; label: string; count: number }
type DefinedClass = { id: string; comment: string | null; asserted: number; members: string[] }
type Dashboard = {
  classes: number
  object_properties: number
  data_properties: number
  individuals: number
  axioms: number
  asserted_triples: number
  inferred_triples: number
  families: Family[]
  defined_classes: DefinedClass[]
}

const SCENARIO = [
  { title: 'Explorer l’ontologie', text: 'Cette page : classes, axiomes et tout ce que le raisonneur OWL déduit des données.', href: '', action: 'Voir les déductions' },
  { title: 'Parcourir territoires et acteurs', text: 'Ouvrez « Les Berges du Lac » : Maison1, déclarée simple Maison, y apparaît comme MaisonAutonome.', href: '#/territoires-acteurs', action: 'Ouvrir' },
  { title: 'Créer, modifier, supprimer', text: 'Ajoutez un acteur : la requête SPARQL Update exécutée s’affiche, puis il devient interrogeable.', href: '#/territoires-acteurs', action: 'Ouvrir' },
  { title: 'Poser une question en français', text: '« maisons sans panneau solaire » : spaCy analyse la phrase et génère la requête SPARQL.', href: `#/recherche?q=${encodeURIComponent('maisons sans panneau solaire')}`, action: 'Essayer' },
]

const fr = (value: number) => value.toLocaleString('fr-FR')
const humanize = (name: string) => name.replace(/([a-z])([A-Z0-9])/g, '$1 $2')

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState('')
  const [question, setQuestion] = useState('')

  useEffect(() => {
    fetch('/api/tableau-de-bord')
      .then((response) => {
        if (!response.ok) throw new Error(`Erreur ${response.status}.`)
        return response.json()
      })
      .then(setData)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Erreur de chargement.'))
  }, [])

  function ask(event: FormEvent) {
    event.preventDefault()
    if (question.trim()) window.location.hash = `#/recherche?q=${encodeURIComponent(question.trim())}`
  }

  return <>
    <PageHeader eyebrow="Vue d’ensemble" title="Tableau de bord">
      Une ontologie OWL du réseau énergétique intelligent, enrichie par un raisonneur et interrogeable en français.
    </PageHeader>

    <form className="card quick-search" onSubmit={ask}>
      <label htmlFor="quick-question">Posez une question</label>
      <div className="search-row">
        <input id="quick-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ex. lignes gérées par la STEG" />
        <button disabled={!question.trim()}>Rechercher</button>
      </div>
    </form>

    {error && <p className="notice error">{error} Vérifiez que le backend est démarré.</p>}
    {!data && !error && <p className="notice">Chargement de l’ontologie…</p>}
    {data && <>
      <section className="overview">
        <div className="tiles">
          <Tile label="Classes" value={data.classes} />
          <Tile label="Propriétés d’objet" value={data.object_properties} />
          <Tile label="Propriétés de données" value={data.data_properties} />
          <Tile label="Individus" value={data.individuals} />
          <Tile label="Axiomes" value={data.axioms} />
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="card">
          <h2>Individus par famille</h2>
          <p className="muted">Nombre d’individus de chaque grande classe, sous-classes et inférences comprises.</p>
          <BarChart items={data.families} />
        </div>
        <div className="card">
          <h2>Scénario de démonstration</h2>
          <ol className="scenario">
            {SCENARIO.map((step, index) => <li key={step.title}>
              <span className="step-number">{index + 1}</span>
              <div><strong>{step.title}</strong><p>{step.text}</p>{step.href
                ? <a href={step.href}>{step.action} →</a>
                : <button type="button" className="link" onClick={() => document.getElementById('deductions')?.scrollIntoView({ behavior: 'smooth' })}>{step.action} →</button>}</div>
            </li>)}
          </ol>
        </div>
      </section>

      <section className="card" id="deductions">
        <h2>Ce que le raisonneur a déduit</h2>
        <p className="muted">Classes définies par un axiome d’équivalence : aucun individu n’y est rangé à la main, le raisonneur les classe à partir de leurs propriétés.</p>
        <div className="deductions">
          {data.defined_classes.map((item) => <article key={item.id}>
            <div className="deduction-head"><strong>{humanize(item.id)}</strong><span>{item.members.length} déduit{item.members.length > 1 ? 's' : ''} · {item.asserted} déclaré{item.asserted > 1 ? 's' : ''}</span></div>
            {item.comment && <p>{item.comment}</p>}
            <div className="chips">{item.members.length === 0 ? <span className="muted">Aucun individu.</span> : item.members.map((member) => <span key={member} className="chip">{member}</span>)}</div>
          </article>)}
        </div>
      </section>
    </>}
  </>
}

function Tile({ label, value }: { label: string; value: number }) {
  return <div className="tile"><p className="card-label">{label}</p><p className="tile-value">{fr(value)}</p></div>
}

function BarChart({ items }: { items: Family[] }) {
  const max = Math.max(1, ...items.map((item) => item.count))
  return <div className="bar-chart" role="list">
    {items.map((item) => <div key={item.id} className="bar-row" role="listitem" tabIndex={0} title={`${item.label} : ${item.count} individus`} aria-label={`${item.label} : ${item.count} individus`}>
      <span className="bar-label">{item.label}</span>
      <span className="bar-track"><span className="bar" style={{ width: `calc((100% - 2.5rem) * ${item.count / max})` }} /><span className="bar-value">{item.count}</span></span>
    </div>)}
  </div>
}
