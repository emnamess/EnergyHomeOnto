import { FormEvent, useCallback, useEffect, useState } from 'react'
import AppNav from '../../shared/AppNav'

type Status = 'fin-de-vie' | 'a-remplacer' | 'en-service' | 'inconnu'
type Equipment = {
  id: string; name: string; category: string; kind: string; inferred_classes: string[]
  installation_year: number | null; lifetime_years: number | null; age_years: number | null; remaining_years: number | null
  status: Status; intervention_count: number
}
type Intervention = {
  id: string; kind: string; date: string; planned: boolean; cost: number | null; description: string
  provider: string | null; equipment_id: string; equipment_name: string
}
type EquipmentDetail = Equipment & { installation_cost: number | null; maintenance_cost: number; interventions: Intervention[] }
type InterventionForm = { kind: string; equipment: string; date: string; cost: string; description: string; provider: string }
type Mutation = { id: string; sparql: string }

const API = '/api/maintenance'
const today = () => new Date().toISOString().slice(0, 10)
const emptyForm = (equipment = ''): InterventionForm => ({ kind: 'InterventionPreventive', equipment, date: today(), cost: '', description: '', provider: '' })
const shortKind = (kind: string) => kind.replace(/([a-z])([A-Z])/g, '$1 $2')
const STATUS_LABELS: Record<Status, string> = { 'fin-de-vie': 'Fin de vie dépassée', 'a-remplacer': 'À remplacer bientôt', 'en-service': 'En service', inconnu: 'Données manquantes' }
const money = (value?: number | null) => value == null ? '—' : `${value.toLocaleString('fr-FR')} TND`
const years = (value?: number | null) => value == null ? '—' : `${value} an${Math.abs(value) > 1 ? 's' : ''}`
const formatDate = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString('fr-FR')

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Erreur ${response.status}.`)
  }
  return response.json()
}

export default function MaintenancePage() {
  const [equipmentList, setEquipmentList] = useState<Equipment[]>([])
  const [allEquipment, setAllEquipment] = useState<Equipment[]>([])
  const [interventions, setInterventions] = useState<Intervention[]>([])
  const [equipment, setEquipment] = useState<EquipmentDetail | null>(null)
  const [intervention, setIntervention] = useState<Intervention | null>(null)
  const [text, setText] = useState('')
  const [category, setCategory] = useState('')
  const [horizon, setHorizon] = useState('')
  const [interventionKind, setInterventionKind] = useState('')
  const [form, setForm] = useState<InterventionForm | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Mutation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadLists = useCallback(async () => {
    const query = text.trim() && { q: text.trim() }
    const equipmentParams = new URLSearchParams({ ...(category && { category }), ...(horizon && { horizon }), ...query })
    const interventionParams = new URLSearchParams({ ...(interventionKind && { kind: interventionKind }), ...query })
    try {
      const [equipmentItems, interventionItems, everyEquipment] = await Promise.all([
        fetch(`${API}/equipements?${equipmentParams}`).then(readJson<Equipment[]>),
        fetch(`${API}/interventions?${interventionParams}`).then(readJson<Intervention[]>),
        fetch(`${API}/equipements`).then(readJson<Equipment[]>),
      ])
      setEquipmentList(equipmentItems)
      setInterventions(interventionItems)
      setAllEquipment(everyEquipment)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? `${cause.message} Vérifiez que FastAPI est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, category, horizon, interventionKind])

  useEffect(() => {
    const timer = setTimeout(loadLists, 250)
    return () => clearTimeout(timer)
  }, [loadLists])

  async function chooseEquipment(id: string) {
    setIntervention(null)
    setForm(null)
    try {
      setEquipment(await fetch(`${API}/equipements/${id}`).then(readJson<EquipmentDetail>))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger cet équipement.')
    }
  }

  async function chooseIntervention(id: string) {
    setEquipment(null)
    setForm(null)
    try {
      setIntervention(await fetch(`${API}/interventions/${id}`).then(readJson<Intervention>))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger cette intervention.')
    }
  }

  function startCreate(equipmentId = '') {
    setEquipment(null)
    setIntervention(null)
    setForm(emptyForm(equipmentId || allEquipment[0]?.id || ''))
  }

  function startEdit(current: Intervention) {
    setForm({
      kind: current.kind, equipment: current.equipment_id, date: current.date, cost: current.cost?.toString() ?? '',
      description: current.description, provider: current.provider ?? '',
    })
  }

  async function saveIntervention(event: FormEvent) {
    event.preventDefault()
    if (!form) return
    const editing = intervention !== null
    const body = { ...form, cost: form.cost === '' ? null : Number(form.cost), provider: form.provider || null }
    try {
      const mutation = await fetch(editing ? `${API}/interventions/${intervention.id}` : `${API}/interventions`, {
        method: editing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).then(readJson<Mutation>)
      setLastUpdate(mutation)
      await loadLists()
      await chooseIntervention(mutation.id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Enregistrement impossible.')
    }
  }

  async function deleteIntervention(current: Intervention) {
    if (!window.confirm(`Supprimer l’intervention « ${current.description} » du graphe RDF ?`)) return
    try {
      setLastUpdate(await fetch(`${API}/interventions/${current.id}`, { method: 'DELETE' }).then(readJson<Mutation>))
      setIntervention(null)
      await loadLists()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Suppression impossible.')
    }
  }

  const selected = equipment ?? intervention ?? form
  return <main className="maintenance-page">
    <header className="topbar"><span className="brand-mark">E</span><span>EnergyHome</span><span className="tag">MAINTENANCE</span><AppNav current="#/maintenance" /></header>
    <section className="maintenance-hero"><p className="eyebrow">FEATURE 6</p><h1>Anticiper l’usure<br />des <em>équipements énergétiques.</em></h1><p className="intro">Suivez l’âge et la fin de vie prévue des sources, stockages et équipements réseau, et l’historique de leurs interventions. Les classes « entretenu » et « déjà réparé » sont déduites par le raisonneur OWL.</p></section>
    <section className="filters">
      <input aria-label="Filtrer par nom" placeholder="Filtrer par nom, description, prestataire…" value={text} onChange={(event) => setText(event.target.value)} />
      <select aria-label="Catégorie d’équipement" value={category} onChange={(event) => setCategory(event.target.value)}><option value="">Tous les équipements</option><option value="SourceEnergie">Sources d’énergie</option><option value="Stockage">Stockages</option><option value="EquipementReseau">Équipements réseau</option></select>
      <select aria-label="Fin de vie" value={horizon} onChange={(event) => setHorizon(event.target.value)}><option value="">Toute fin de vie</option><option value="3">Fin de vie ≤ 3 ans</option><option value="10">Fin de vie ≤ 10 ans</option><option value="15">Fin de vie ≤ 15 ans</option></select>
      <select aria-label="Type d’intervention" value={interventionKind} onChange={(event) => setInterventionKind(event.target.value)}><option value="">Toutes les interventions</option><option value="InterventionPreventive">Préventives</option><option value="InterventionCorrective">Correctives</option></select>
      <button type="button" className="primary" onClick={() => startCreate()}>+ Nouvelle intervention</button>
    </section>
    {loading && <p className="notice">Chargement des données sémantiques…</p>}
    {error && <p className="notice error">{error}</p>}
    {lastUpdate && <details className="notice update-notice"><summary>Requête SPARQL Update exécutée (:{lastUpdate.id})</summary><pre>{lastUpdate.sparql}</pre></details>}
    {!loading && <section className="explorer">
      <aside className="explorer-list">
        <p className="list-title">ÉQUIPEMENTS</p>
        {equipmentList.length === 0 && <p className="muted list-empty">Aucun résultat.</p>}
        {equipmentList.map((item) => <button key={item.id} className={equipment?.id === item.id ? 'list-item active' : 'list-item'} onClick={() => chooseEquipment(item.id)}><span>{item.name}</span><small><i className={`status-dot ${item.status}`} />{item.remaining_years == null ? STATUS_LABELS[item.status] : `${years(item.remaining_years)} restant${Math.abs(item.remaining_years) > 1 ? 's' : ''}`}</small></button>)}
        <p className="list-title interventions-title">INTERVENTIONS</p>
        {interventions.length === 0 && <p className="muted list-empty">Aucun résultat.</p>}
        {interventions.map((item) => <button key={item.id} className={intervention?.id === item.id ? 'list-item active' : 'list-item'} onClick={() => chooseIntervention(item.id)}><span>{item.equipment_name} · {formatDate(item.date)}</span><small>{shortKind(item.kind)}{item.planned ? ' · planifiée' : ''}</small></button>)}
      </aside>
      <section className="detail-panel">
        {!selected && <div className="empty-state"><span>⌁</span><h2>Sélectionnez un équipement ou une intervention</h2><p>Les données viennent de l’ontologie OWL via des requêtes SPARQL.</p></div>}
        {equipment && <>
          <div className="detail-head"><p className="eyebrow">{shortKind(equipment.kind)} · {shortKind(equipment.category)}</p><div className="actions"><button type="button" onClick={() => startCreate(equipment.id)}>+ Intervention</button></div></div>
          <h2>{equipment.name}</h2>
          <p className={`status-badge ${equipment.status}`}>{STATUS_LABELS[equipment.status]}</p>
          <div className="metrics"><Metric label="Installation" value={equipment.installation_year?.toString() ?? '—'} /><Metric label="Durée de vie prévue" value={years(equipment.lifetime_years)} /><Metric label="Durée de vie restante" value={years(equipment.remaining_years)} /></div>
          <div className="metrics"><Metric label="Coût d’installation" value={money(equipment.installation_cost)} /><Metric label="Coût de maintenance" value={money(equipment.maintenance_cost)} /><Metric label="Interventions" value={String(equipment.intervention_count)} /></div>
          <section className="related"><h3>Classes déduites par le raisonneur</h3>{equipment.inferred_classes.length === 0 ? <p className="muted">Aucune : l’équipement n’a encore subi aucune intervention.</p> : <div className="related-grid">{equipment.inferred_classes.map((kind) => <article key={kind}><span>Classe définie</span><strong>{shortKind(kind)}</strong></article>)}</div>}</section>
          <section className="related"><h3>Historique des interventions (déduit de concerne via aSubi)</h3>{equipment.interventions.length === 0 ? <p className="muted">Aucune intervention enregistrée.</p> : <div className="related-grid">{equipment.interventions.map((item) => <article key={item.id} className="clickable" onClick={() => chooseIntervention(item.id)}><span>{shortKind(item.kind)} · {formatDate(item.date)}</span><strong>{item.description}</strong><small className="muted">{money(item.cost)}</small></article>)}</div>}</section>
        </>}
        {intervention && !form && <>
          <div className="detail-head"><p className="eyebrow">{shortKind(intervention.kind)}{intervention.planned ? ' · PLANIFIÉE' : ''}</p><div className="actions"><button type="button" onClick={() => startEdit(intervention)}>Modifier</button><button type="button" className="danger" onClick={() => deleteIntervention(intervention)}>Supprimer</button></div></div>
          <h2>{intervention.description}</h2>
          <div className="metrics"><Metric label="Date" value={formatDate(intervention.date)} /><Metric label="Coût" value={money(intervention.cost)} /><Metric label="Prestataire" value={intervention.provider ?? '—'} /></div>
          <section className="related"><h3>Équipement concerné</h3><div className="related-grid"><article className="clickable" onClick={() => chooseEquipment(intervention.equipment_id)}><span>Voir la fiche</span><strong>{intervention.equipment_name}</strong></article></div></section>
        </>}
        {form && <form className="intervention-form" onSubmit={saveIntervention}>
          <p className="eyebrow">{intervention ? 'MODIFIER L’INTERVENTION' : 'NOUVELLE INTERVENTION'}</p>
          <label>Type<select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}><option value="InterventionPreventive">Préventive (entretien planifié)</option><option value="InterventionCorrective">Corrective (réparation après panne)</option></select></label>
          <label>Équipement<select required value={form.equipment} onChange={(event) => setForm({ ...form, equipment: event.target.value })}>{allEquipment.map((item) => <option key={item.id} value={item.id}>{item.name} ({shortKind(item.kind)})</option>)}</select></label>
          <label>Date<input type="date" required value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} /></label>
          <label>Description<input required maxLength={300} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          <label>Coût (TND)<input type="number" min="0" step="0.01" value={form.cost} onChange={(event) => setForm({ ...form, cost: event.target.value })} /></label>
          <label>Prestataire<input maxLength={120} value={form.provider} onChange={(event) => setForm({ ...form, provider: event.target.value })} /></label>
          <div className="actions"><button type="submit" className="primary">Enregistrer</button><button type="button" onClick={() => setForm(null)}>Annuler</button></div>
        </form>}
      </section>
    </section>}
  </main>
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="metric"><small>{label}</small><strong>{value}</strong></div> }
