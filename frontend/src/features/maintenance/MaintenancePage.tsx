import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { PageHeader } from '../../shared/Layout'
import { Badges, DataTable, Facts, Field, Section, Tabs, UpdateNotice, humanize, readJson, rowProps, withUnit } from '../../shared/ui'

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
type Tab = 'equipements' | 'interventions'

const API = '/api/maintenance'
const today = () => new Date().toISOString().slice(0, 10)
const emptyForm = (equipment = ''): InterventionForm => ({ kind: 'InterventionPreventive', equipment, date: today(), cost: '', description: '', provider: '' })
const STATUS_LABELS: Record<Status, string> = { 'fin-de-vie': 'Fin de vie dépassée', 'a-remplacer': 'À remplacer bientôt', 'en-service': 'En service', inconnu: 'Données manquantes' }
const CATEGORIES: Record<string, string> = { SourceEnergie: 'Source d’énergie', Stockage: 'Stockage', EquipementReseau: 'Équipement réseau' }
const KINDS: Record<string, string> = { InterventionPreventive: 'Préventive', InterventionCorrective: 'Corrective' }
const money = (value?: number | null) => withUnit(value, 'TND')
const years = (value?: number | null) => value == null ? '—' : `${value} an${Math.abs(value) > 1 ? 's' : ''}`
const formatDate = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString('fr-FR')

// initialEquipment : arrivée depuis une alerte du tableau de bord (#/maintenance?equipement=batterie7).
export default function MaintenancePage({ initialEquipment }: { initialEquipment?: string }) {
  const [tab, setTab] = useState<Tab>('equipements')
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
      setError(cause instanceof Error ? `${cause.message} Vérifiez que le backend est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [text, category, horizon, interventionKind])

  useEffect(() => {
    const timer = setTimeout(loadLists, 250)
    return () => clearTimeout(timer)
  }, [loadLists])

  // Préremplit une intervention préventive sur l'équipement signalé.
  const prefilled = useRef(false)
  useEffect(() => {
    if (prefilled.current || !allEquipment.some((item) => item.id === initialEquipment)) return
    prefilled.current = true
    setEquipment(null)
    setIntervention(null)
    setForm({ ...emptyForm(initialEquipment), description: 'Remplacement préventif de l’équipement en fin de vie' })
  }, [initialEquipment, allEquipment])

  function closeDetail() {
    setEquipment(null)
    setIntervention(null)
    setForm(null)
  }

  function changeTab(next: Tab) {
    setTab(next)
    closeDetail()
  }

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
      setTab('interventions')
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

  const panelOpen = equipment !== null || intervention !== null || form !== null
  return <>
    <PageHeader eyebrow="Feature 6" title="Maintenance">
      Âge et fin de vie prévue des sources, stockages et équipements réseau, et historique de leurs interventions. Les classes « équipement entretenu » et « déjà réparé » sont déduites par le raisonneur OWL.
    </PageHeader>

    <Tabs value={tab} onChange={changeTab} tabs={[
      { id: 'equipements', label: 'Équipements', count: equipmentList.length },
      { id: 'interventions', label: 'Interventions', count: interventions.length },
    ]} />

    <div className="filters">
      <input aria-label="Rechercher" placeholder={tab === 'equipements' ? 'Rechercher par nom…' : 'Rechercher par équipement, description, prestataire…'} value={text} onChange={(event) => setText(event.target.value)} />
      {tab === 'equipements' ? <>
        <select aria-label="Catégorie d’équipement" value={category} onChange={(event) => setCategory(event.target.value)}><option value="">Toutes les catégories</option><option value="SourceEnergie">Sources d’énergie</option><option value="Stockage">Stockages</option><option value="EquipementReseau">Équipements réseau</option></select>
        <select aria-label="Fin de vie" value={horizon} onChange={(event) => setHorizon(event.target.value)}><option value="">Toute fin de vie</option><option value="3">Fin de vie ≤ 3 ans</option><option value="10">Fin de vie ≤ 10 ans</option><option value="15">Fin de vie ≤ 15 ans</option></select>
      </> : <select aria-label="Type d’intervention" value={interventionKind} onChange={(event) => setInterventionKind(event.target.value)}><option value="">Toutes les interventions</option><option value="InterventionPreventive">Préventives</option><option value="InterventionCorrective">Correctives</option></select>}
      <button type="button" className="button primary" onClick={() => startCreate()}>+ Nouvelle intervention</button>
    </div>

    {error && <p className="notice error">{error}</p>}
    <UpdateNotice mutation={lastUpdate} />

    <div className={panelOpen ? 'workspace with-panel' : 'workspace'}>
      <div className="card table-card">
        {loading ? <p className="notice">Chargement des données sémantiques…</p> : tab === 'equipements'
          ? <DataTable empty={equipmentList.length === 0 ? 'Aucun équipement ne correspond.' : ''}>
              <thead><tr><th>Nom</th><th className="secondary">Catégorie</th><th className="num secondary">Installation</th><th className="num">Vie restante</th><th>État</th><th className="num secondary">Interventions</th></tr></thead>
              <tbody>{equipmentList.map((item) => <tr key={item.id} {...rowProps(equipment?.id === item.id, () => chooseEquipment(item.id))}>
                <td className="strong">{item.name}</td>
                <td className="secondary"><span className="badge">{CATEGORIES[item.category] ?? humanize(item.category)}</span></td>
                <td className="num secondary">{item.installation_year ?? '—'}</td>
                <td className="num nowrap">{years(item.remaining_years)}</td>
                <td><StatusLabel status={item.status} /></td>
                <td className="num secondary">{item.intervention_count}</td>
              </tr>)}</tbody>
            </DataTable>
          : <DataTable empty={interventions.length === 0 ? 'Aucune intervention ne correspond.' : ''}>
              <thead><tr><th>Date</th><th>Équipement</th><th>Type</th><th className="secondary">Description</th><th className="num">Coût</th></tr></thead>
              <tbody>{interventions.map((item) => <tr key={item.id} {...rowProps(intervention?.id === item.id, () => chooseIntervention(item.id))}>
                <td className="nowrap">{formatDate(item.date)}{item.planned && <span className="badge planned">planifiée</span>}</td>
                <td className="strong">{item.equipment_name}</td>
                <td><span className="badge">{KINDS[item.kind] ?? humanize(item.kind)}</span></td>
                <td className="secondary">{item.description}</td>
                <td className="num nowrap">{money(item.cost)}</td>
              </tr>)}</tbody>
            </DataTable>}
      </div>

      {panelOpen && <aside className="card detail-card">
        <button type="button" className="close" aria-label="Fermer le détail" onClick={closeDetail}>×</button>

        {equipment && !form && <>
          <span className="badges"><span className="badge">{humanize(equipment.kind)}</span><span className="badge">{CATEGORIES[equipment.category] ?? humanize(equipment.category)}</span></span>
          <h2>{equipment.name}</h2>
          <div className="actions"><button type="button" className="button" onClick={() => startCreate(equipment.id)}>+ Intervention</button></div>
          <StatusLabel status={equipment.status} />
          <Facts items={[
            ['Année d’installation', equipment.installation_year ?? '—'],
            ['Durée de vie prévue', years(equipment.lifetime_years)],
            ['Durée de vie restante', years(equipment.remaining_years)],
            ['Coût d’installation', money(equipment.installation_cost)],
            ['Coût de maintenance', money(equipment.maintenance_cost)],
            ['Interventions', equipment.intervention_count],
          ]} />
          <Section title="Classes déduites par le raisonneur">
            {equipment.inferred_classes.length === 0 ? <p className="muted">Aucune : l’équipement n’a encore subi aucune intervention.</p> : <Badges values={equipment.inferred_classes} />}
          </Section>
          <Section title="Historique des interventions" count={equipment.interventions.length} note="déduit de concerne via la propriété inverse aSubi">
            {equipment.interventions.length === 0 ? <p className="muted">Aucune intervention enregistrée.</p> : <DataTable compact>
              <thead><tr><th>Date</th><th>Type</th><th>Description</th><th className="num">Coût</th></tr></thead>
              <tbody>{equipment.interventions.map((item) => <tr key={item.id} {...rowProps(false, () => { setTab('interventions'); chooseIntervention(item.id) })}>
                <td className="nowrap">{formatDate(item.date)}</td><td><span className="badge">{KINDS[item.kind] ?? humanize(item.kind)}</span></td><td>{item.description}</td><td className="num nowrap">{money(item.cost)}</td>
              </tr>)}</tbody>
            </DataTable>}
          </Section>
        </>}

        {intervention && !form && <>
          <span className="badges"><span className="badge">{KINDS[intervention.kind] ?? humanize(intervention.kind)}</span>{intervention.planned && <span className="badge planned">planifiée</span>}</span>
          <h2>{intervention.description}</h2>
          <div className="actions"><button type="button" className="button" onClick={() => startEdit(intervention)}>Modifier</button><button type="button" className="button danger" onClick={() => deleteIntervention(intervention)}>Supprimer</button></div>
          <Facts items={[
            ['Date', formatDate(intervention.date)],
            ['Coût', money(intervention.cost)],
            ['Prestataire', intervention.provider ?? '—'],
            ['Équipement', <button key="equipement" type="button" className="link" onClick={() => { setTab('equipements'); chooseEquipment(intervention.equipment_id) }}>{intervention.equipment_name} →</button>],
          ]} />
        </>}

        {form && <form className="actor-form" onSubmit={saveIntervention}>
          <h2>{intervention ? 'Modifier l’intervention' : 'Nouvelle intervention'}</h2>
          <Field label="Type"><select value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}><option value="InterventionPreventive">Préventive (entretien planifié)</option><option value="InterventionCorrective">Corrective (réparation après panne)</option></select></Field>
          <Field label="Équipement"><select required value={form.equipment} onChange={(event) => setForm({ ...form, equipment: event.target.value })}>{allEquipment.map((item) => <option key={item.id} value={item.id}>{item.name} ({humanize(item.kind)})</option>)}</select></Field>
          <Field label="Date"><input type="date" required value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} /></Field>
          <Field label="Description"><input required maxLength={300} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field>
          <div className="form-row">
            <Field label="Coût (TND)"><input type="number" min="0" step="0.01" value={form.cost} onChange={(event) => setForm({ ...form, cost: event.target.value })} /></Field>
            <Field label="Prestataire"><input maxLength={120} value={form.provider} onChange={(event) => setForm({ ...form, provider: event.target.value })} /></Field>
          </div>
          <div className="actions"><button type="submit" className="button primary">Enregistrer</button><button type="button" className="button" onClick={() => intervention ? setForm(null) : closeDetail()}>Annuler</button></div>
        </form>}
      </aside>}
    </div>
  </>
}

function StatusLabel({ status }: { status: Status }) {
  return <span className={`status ${status}`}><span className="status-dot" aria-hidden="true" />{STATUS_LABELS[status]}</span>
}
