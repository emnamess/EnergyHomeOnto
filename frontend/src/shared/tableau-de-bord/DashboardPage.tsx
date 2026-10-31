import { FormEvent, useEffect, useState } from 'react'
import { PageHeader } from '../Layout'
import { readJson } from '../ui'

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
type AlertItem = { id: string; name: string; detail: string; action: string | null }
type Alert = { id: string; title: string; rule: string; severity: 'critique' | 'attention' | 'info'; items: AlertItem[] }

const SEVERITY: Record<Alert['severity'], string> = { critique: 'Critique', attention: 'Attention', info: 'Information' }
const EMPTY: Record<string, string> = {
  'batiments-non-secourus': 'Tous les bâtiments publics sont secourus par un stockage.',
  'fin-de-vie': 'Tous les équipements en fin de vie ont un entretien préventif.',
  'maisons-energivores': 'Aucune maison énergivore non autonome.',
}

const fr = (value: number) => value.toLocaleString('fr-FR')
const humanize = (name: string) => name.replace(/([a-z])([A-Z0-9])/g, '$1 $2')
const search = (question: string) => `#/recherche?q=${encodeURIComponent(question)}`

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [alerts, setAlerts] = useState<Alert[] | null>(null)
  const [error, setError] = useState('')
  const [question, setQuestion] = useState('')

  useEffect(() => {
    Promise.all([fetch('/api/tableau-de-bord').then(readJson<Dashboard>), fetch('/api/tableau-de-bord/alertes').then(readJson<Alert[]>)])
      .then(([dashboard, alertList]) => {
        setData(dashboard)
        setAlerts(alertList)
      })
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Erreur de chargement.'))
  }, [])

  function ask(event: FormEvent) {
    event.preventDefault()
    if (question.trim()) window.location.hash = search(question.trim())
  }

  const toFix = alerts?.filter((alert) => alert.severity !== 'info').reduce((total, alert) => total + alert.items.length, 0) ?? 0
  const firstAction = (id: string, fallback: string) => alerts?.find((alert) => alert.id === id)?.items[0]?.action ?? fallback
  const firstName = (id: string) => alerts?.find((alert) => alert.id === id)?.items[0]?.name
  const scenario = [
    { title: 'Diagnostiquer', text: 'Lisez les alertes : chacune est une requête SPARQL sur le graphe déduit par le raisonneur OWL, définie par une règle de l’ontologie.', href: '', action: 'Voir les alertes' },
    { title: 'Analyser en français', text: 'Posez la question « bâtiments publics sans stockage » : spaCy la traduit en SPARQL et retrouve les mêmes bâtiments.', href: search('bâtiments publics sans stockage'), action: 'Poser la question' },
    { title: 'Agir sur le stockage', text: `Créez une batterie de secours${firstName('batiments-non-secourus') ? ` pour « ${firstName('batiments-non-secourus')} »` : ''} : le raisonneur classe le bâtiment « avec stockage » et l’alerte disparaît.`, href: firstAction('batiments-non-secourus', '#/stockage'), action: 'Créer la batterie' },
    { title: 'Planifier la maintenance', text: `Planifiez une intervention préventive${firstName('fin-de-vie') ? ` sur « ${firstName('fin-de-vie')} »` : ''} : l’équipement devient « entretenu » par déduction.`, href: firstAction('fin-de-vie', '#/maintenance'), action: 'Planifier' },
    { title: 'Faire le bilan', text: 'Revenez ici : les alertes traitées ont disparu. Les maisons énergivores restent pour la future feature Production.', href: '', action: 'Revoir les alertes' },
  ]
  const scrollToAlerts = () => document.getElementById('alertes')?.scrollIntoView({ behavior: 'smooth' })

  return <>
    <PageHeader eyebrow="Vue d’ensemble" title="Tableau de bord">
      Une ontologie OWL du réseau énergétique intelligent, enrichie par un raisonneur et interrogeable en français.
    </PageHeader>

    <section className="card mission">
      <div>
        <p className="eyebrow">Votre mission</p>
        <h2>Responsable énergie de la ville</h2>
        <p className="lead">Sécuriser l’alimentation des bâtiments publics et anticiper l’usure des équipements du réseau, à partir de ce que l’ontologie déduit des données.</p>
      </div>
      {alerts && <div className={toFix === 0 ? 'mission-count done' : 'mission-count'}>
        <strong>{toFix}</strong><span>{toFix === 0 ? 'alerte à traiter : mission accomplie' : `alerte${toFix > 1 ? 's' : ''} à traiter`}</span>
      </div>}
    </section>

    {error && <p className="notice error">{error} Vérifiez que le backend est démarré.</p>}
    {!data && !error && <p className="notice">Chargement de l’ontologie…</p>}

    {alerts && <section id="alertes" className="alerts">
      {alerts.map((alert) => <article key={alert.id} className={`card alert ${alert.severity}`}>
        <div className="alert-head">
          <span className={`severity ${alert.severity}`}><span className="status-dot" aria-hidden="true" />{SEVERITY[alert.severity]}</span>
          <span className="count">{alert.items.length}</span>
        </div>
        <h2>{alert.title}</h2>
        <p className="rule">{alert.rule}</p>
        {alert.items.length === 0
          ? <p className="alert-empty">✓ {EMPTY[alert.id]}</p>
          : <ul className="alert-items">{alert.items.map((item) => <li key={item.id}>
              <div><strong>{item.name}</strong><span>{item.detail}</span></div>
              {item.action ? <a className="button" href={item.action}>Traiter →</a> : <span className="badge">feature à venir</span>}
            </li>)}</ul>}
      </article>)}
    </section>}

    <section className="card">
      <h2>Scénario de démonstration</h2>
      <ol className="scenario steps">
        {scenario.map((step, index) => <li key={step.title}>
          <span className="step-number">{index + 1}</span>
          <div><strong>{step.title}</strong><p>{step.text}</p>{step.href
            ? <a href={step.href}>{step.action} →</a>
            : <button type="button" className="link" onClick={scrollToAlerts}>{step.action} →</button>}</div>
        </li>)}
      </ol>
    </section>

    <form className="card quick-search" onSubmit={ask}>
      <label htmlFor="quick-question">Posez une question en français</label>
      <div className="search-row">
        <input id="quick-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ex. maisons non autonomes avec une consommation supérieure à 20" />
        <button disabled={!question.trim()}>Rechercher</button>
      </div>
    </form>

    {data && <>
      <h2 className="section-title">L’ontologie en chiffres</h2>
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
          <h2>Graphe RDF</h2>
          <p className="muted">Triplets déclarés dans Protégé puis complétés par le raisonneur OWL RL.</p>
          <BarChart items={[
            { id: 'asserted', label: 'Déclarés', count: data.asserted_triples },
            { id: 'inferred', label: 'Après raisonnement', count: data.inferred_triples },
          ]} />
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
    {items.map((item) => <div key={item.id} className="bar-row" role="listitem" tabIndex={0} title={`${item.label} : ${fr(item.count)}`} aria-label={`${item.label} : ${fr(item.count)}`}>
      <span className="bar-label">{item.label}</span>
      <span className="bar-track"><span className="bar" style={{ width: `calc((100% - 3.5rem) * ${item.count / max})` }} /><span className="bar-value">{fr(item.count)}</span></span>
    </div>)}
  </div>
}
