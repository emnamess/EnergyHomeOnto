import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { PageHeader } from '../../shared/Layout'
import { DataTable, Facts, Field, Section, UpdateNotice, fr, humanize, readJson, rowProps, withUnit } from '../../shared/ui'

type NetworkKind = 'LigneElectrique' | 'LigneHauteTension' | 'LigneMoyenneTension' | 'LigneBasseTension' | 'LigneSouterraine' | 'PosteTransformation' | 'CompteurIntelligent'
type NetworkElement = {
  id: string; name: string; kind: string; length: number | null; voltage: number | null; section: number | null
  loss_rate: number | null; underground: boolean | null; transformation_power: number | null; meter_identifier: string | null
  reading_frequency: number | null; installation_year: number | null; lifetime_years: number | null
  installation_cost: number | null; related_count: number
}
type RelatedElement = { id: string; name: string; kind: string }
type NetworkDetail = NetworkElement & { inferred_classes: string[]; relationships: RelatedElement[]; managers: RelatedElement[] }
type KindIndicator = { kind: string; count: number }
type Indicators = { count: number; by_kind: KindIndicator[] }
type Option = { id: string; name: string; kind: string }
type Options = { kinds: NetworkKind[]; lines: Option[]; equipment: Option[]; managers: Option[]; buildings: Option[]; sources: Option[]; storages: Option[] }
type Mutation = { id: string; sparql: string }
type NetworkForm = {
  name: string; kind: NetworkKind; length: string; voltage: string; section: string; loss_rate: string; underground: string
  transformation_power: string; meter_identifier: string; reading_frequency: string; installation_year: string
  lifetime_years: string; installation_cost: string; related: string[]; managers: string[]
}

const API = '/api/reseau'
const KIND_LABELS: Record<string, string> = {
  LigneElectrique: 'Ligne électrique', LigneHauteTension: 'Ligne haute tension', LigneMoyenneTension: 'Ligne moyenne tension',
  LigneBasseTension: 'Ligne basse tension', LigneSouterraine: 'Ligne souterraine', PosteTransformation: 'Poste de transformation',
  CompteurIntelligent: 'Compteur intelligent',
}
const LABEL = (kind: string) => KIND_LABELS[kind] ?? humanize(kind)
const EMPTY_FORM: NetworkForm = {
  name: '', kind: 'LigneElectrique', length: '', voltage: '', section: '', loss_rate: '', underground: '',
  transformation_power: '', meter_identifier: '', reading_frequency: '', installation_year: '', lifetime_years: '',
  installation_cost: '', related: [], managers: [],
}
const numberOrNull = (value: string) => value.trim() === '' ? null : Number(value)

export default function ReseauPage() {
  const [elements, setElements] = useState<NetworkElement[]>([])
  const [indicators, setIndicators] = useState<Indicators | null>(null)
  const [options, setOptions] = useState<Options>({ kinds: [], lines: [], equipment: [], managers: [], buildings: [], sources: [], storages: [] })
  const [element, setElement] = useState<NetworkDetail | null>(null)
  const [text, setText] = useState('')
  const [kind, setKind] = useState('')
  const [minVoltage, setMinVoltage] = useState('')
  const [maxVoltage, setMaxVoltage] = useState('')
  const [underground, setUnderground] = useState('')
  const [form, setForm] = useState<NetworkForm | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Mutation | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadLists = useCallback(async () => {
    const params = new URLSearchParams({
      ...(kind && { kind }), ...(text.trim() && { q: text.trim() }), ...(minVoltage && { min_voltage: minVoltage }),
      ...(maxVoltage && { max_voltage: maxVoltage }), ...(underground && { underground }),
    })
    setLoading(true)
    try {
      const [list, totals, choices] = await Promise.all([
        fetch(`${API}?${params}`).then(readJson<NetworkElement[]>),
        fetch(`${API}/indicateurs`).then(readJson<Indicators>),
        fetch(`${API}/options`).then(readJson<Options>),
      ])
      setElements(list)
      setIndicators(totals)
      setOptions(choices)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? `${cause.message} Vérifiez que le backend est démarré.` : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [kind, maxVoltage, minVoltage, text, underground])

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadLists() }, 250)
    return () => window.clearTimeout(timer)
  }, [loadLists])

  async function chooseElement(id: string, preserveSuccess = false) {
    setForm(null)
    if (!preserveSuccess) setSuccess('')
    try {
      setElement(await fetch(`${API}/${encodeURIComponent(id)}`).then(readJson<NetworkDetail>))
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Impossible de charger cet élément réseau.')
    }
  }

  function closePanel() {
    setElement(null)
    setForm(null)
  }

  function startCreate() {
    setElement(null)
    setForm({ ...EMPTY_FORM })
    setError('')
    setSuccess('')
  }

  function startEdit(current: NetworkDetail) {
    setForm({
      name: current.name, kind: current.kind.split(', ')[0] as NetworkKind,
      length: current.length?.toString() ?? '', voltage: current.voltage?.toString() ?? '',
      section: current.section?.toString() ?? '', loss_rate: current.loss_rate?.toString() ?? '',
      underground: current.underground == null ? '' : String(current.underground),
      transformation_power: current.transformation_power?.toString() ?? '', meter_identifier: current.meter_identifier ?? '',
      reading_frequency: current.reading_frequency?.toString() ?? '', installation_year: current.installation_year?.toString() ?? '',
      lifetime_years: current.lifetime_years?.toString() ?? '', installation_cost: current.installation_cost?.toString() ?? '',
      related: [...new Set(current.relationships.map((item) => item.id))],
      managers: [...new Set(current.managers.map((item) => item.id))],
    })
    setError('')
    setSuccess('')
  }

  function toggle(field: 'related' | 'managers', id: string) {
    if (!form) return
    const values = form[field].includes(id) ? form[field].filter((value) => value !== id) : [...form[field], id]
    setForm({ ...form, [field]: values })
  }

  async function saveElement(event: FormEvent) {
    event.preventDefault()
    if (!form) return
    const editing = element !== null
    const isLine = form.kind.startsWith('Ligne')
    const isTransformer = form.kind === 'PosteTransformation'
    const isMeter = form.kind === 'CompteurIntelligent'
    const isNetworkEquipment = isTransformer || isMeter
    const body = {
      name: form.name.trim(), kind: form.kind, length: isLine ? numberOrNull(form.length) : null,
      voltage: isLine || isTransformer ? numberOrNull(form.voltage) : null,
      section: isLine ? numberOrNull(form.section) : null, loss_rate: isLine ? numberOrNull(form.loss_rate) : null,
      underground: isLine && form.underground !== '' ? form.underground === 'true' : null,
      transformation_power: isTransformer ? numberOrNull(form.transformation_power) : null,
      meter_identifier: isMeter ? form.meter_identifier || null : null,
      reading_frequency: isMeter ? numberOrNull(form.reading_frequency) : null,
      installation_year: numberOrNull(form.installation_year),
      lifetime_years: isNetworkEquipment ? numberOrNull(form.lifetime_years) : null,
      installation_cost: isNetworkEquipment ? numberOrNull(form.installation_cost) : null,
      related: isLine ? form.related : [], managers: form.managers,
    }
    setSaving(true)
    try {
      const mutation = await fetch(editing ? `${API}/${encodeURIComponent(element.id)}` : API, {
        method: editing ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      }).then(readJson<Mutation>)
      setLastUpdate(mutation)
      setSuccess(editing ? 'Élément réseau modifié.' : 'Élément réseau créé.')
      setError('')
      setForm(null)
      await loadLists()
      await chooseElement(mutation.id, true)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Enregistrement impossible.')
    } finally {
      setSaving(false)
    }
  }

  async function deleteElement(current: NetworkDetail) {
    if (!window.confirm(`Supprimer « ${current.name} » du graphe RDF ?`)) return
    try {
      const mutation = await fetch(`${API}/${encodeURIComponent(current.id)}`, { method: 'DELETE' }).then(readJson<Mutation>)
      setLastUpdate(mutation)
      setSuccess('Élément réseau supprimé.')
      setError('')
      closePanel()
      await loadLists()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Suppression impossible.')
    }
  }

  const panelOpen = element !== null || form !== null
  const byKind = useMemo(() => [...(indicators?.by_kind ?? [])].sort((a, b) => b.count - a.count), [indicators])
  const maxCount = Math.max(1, ...byKind.map((item) => item.count))
  const relatedOptions = useMemo(() => [...options.buildings, ...options.sources, ...options.storages, ...options.lines, ...options.equipment]
    .filter((item, index, list) => list.findIndex((other) => other.id === item.id) === index), [options])

  return <>
    <PageHeader eyebrow="Feature 4" title="Réseau énergétique">
      Lignes électriques, postes de transformation et compteurs intelligents. Consultez les propriétés et les relations connues dans l’ontologie.
    </PageHeader>

    <section className="overview" aria-label="Vue d’ensemble du réseau">
      <div className="tiles">
        <Tile label="Éléments réseau" value={indicators ? fr(indicators.count) : '…'} />
        <Tile label="Lignes électriques" value={indicators ? fr(options.lines.length) : '…'} />
        <Tile label="Postes" value={indicators ? fr(byKind.find((item) => item.kind === 'PosteTransformation')?.count ?? 0) : '…'} />
        <Tile label="Compteurs" value={indicators ? fr(byKind.find((item) => item.kind === 'CompteurIntelligent')?.count ?? 0) : '…'} />
      </div>
      {indicators && <div className="card capacity-card">
        <h2>Éléments par type</h2>
        {byKind.length === 0 ? <p className="muted">Aucune statistique disponible.</p> : <div className="bar-chart">
          {byKind.map((item) => <div className="bar-row" key={item.kind}>
            <span className="bar-label">{LABEL(item.kind)} <span className="muted">· {item.count}</span></span>
            <span className="bar-track"><span className="bar" style={{ width: `calc((100% - 4rem) * ${item.count / maxCount})` }} /><span className="bar-value">{fr(item.count)}</span></span>
          </div>)}
        </div>}
      </div>}
    </section>

    <div className="filters">
      <input aria-label="Rechercher un élément réseau" placeholder="Rechercher par nom…" value={text} onChange={(event) => setText(event.target.value)} />
      <select aria-label="Type d’élément réseau" value={kind} onChange={(event) => setKind(event.target.value)}>
        <option value="">Tous les types</option>{options.kinds.map((item) => <option key={item} value={item}>{LABEL(item)}</option>)}
      </select>
      <input className="small-input" type="number" min="0" aria-label="Tension minimale" placeholder="Tension min" value={minVoltage} onChange={(event) => setMinVoltage(event.target.value)} />
      <input className="small-input" type="number" min="0" aria-label="Tension maximale" placeholder="Tension max" value={maxVoltage} onChange={(event) => setMaxVoltage(event.target.value)} />
      <select aria-label="Installation souterraine" value={underground} onChange={(event) => setUnderground(event.target.value)}>
        <option value="">Aérien et souterrain</option><option value="true">Souterrain</option><option value="false">Aérien</option>
      </select>
      <button type="button" className="button primary" onClick={startCreate}>+ Nouvel élément</button>
    </div>

    {error && <p className="notice error" role="alert">{error}</p>}
    {success && <p className="notice update-notice" role="status">{success}</p>}
    <UpdateNotice mutation={lastUpdate} />

    <div className={panelOpen ? 'workspace with-panel' : 'workspace'}>
      <div className="card table-card">
        {loading ? <p className="notice" role="status">Chargement des données du réseau…</p> : <DataTable empty={elements.length === 0 ? 'Aucun élément réseau ne correspond aux filtres.' : ''}>
          <thead><tr><th>Nom</th><th>Type</th><th className="num">Tension</th><th className="num secondary">Longueur</th><th className="secondary">Particularité</th><th className="num">Relations</th></tr></thead>
          <tbody>{elements.map((item) => <tr key={item.id} {...rowProps(element?.id === item.id, () => { void chooseElement(item.id) })}>
            <td className="strong">{item.name}</td><td><span className="badge">{LABEL(item.kind.split(', ')[0])}</span></td>
            <td className="num nowrap">{withUnit(item.voltage, 'kV')}</td><td className="num secondary nowrap">{withUnit(item.length, 'm')}</td>
            <td className="secondary">{item.underground == null ? '—' : item.underground ? 'Souterrain' : 'Aérien'}</td><td className="num">{item.related_count}</td>
          </tr>)}</tbody>
        </DataTable>}
      </div>

      {panelOpen && <aside className="card detail-card">
        <button type="button" className="close" aria-label="Fermer le panneau" onClick={closePanel}>×</button>

        {element && !form && <>
          <span className="badge">{LABEL(element.kind.split(', ')[0])}</span>
          <h2>{element.name}</h2>
          <div className="actions">
            <button type="button" className="button" onClick={() => startEdit(element)}>Modifier</button>
            <button type="button" className="button danger" onClick={() => { void deleteElement(element) }}>Supprimer</button>
          </div>
          <Facts items={[
            ['Longueur', withUnit(element.length, 'm')], ['Tension', withUnit(element.voltage, 'kV')],
            ['Section', withUnit(element.section, 'mm²')], ['Taux de pertes', withUnit(element.loss_rate, '%')],
            ['Installation', element.underground == null ? '—' : element.underground ? 'Souterraine' : 'Aérienne'],
            ['Puissance de transformation', withUnit(element.transformation_power, 'MVA')],
            ['Identifiant compteur', element.meter_identifier ?? '—'], ['Fréquence de relevé', withUnit(element.reading_frequency, 'jours')],
            ['Année d’installation', element.installation_year ?? '—'], ['Durée de vie', withUnit(element.lifetime_years, 'ans')],
            ['Coût d’installation', withUnit(element.installation_cost, 'TND')],
          ]} />
          <Related title="Entités liées" items={element.relationships} />
          <Related title="Gestionnaires" items={element.managers} />
          <Section title="Classes inférées">
            {element.inferred_classes.length === 0 ? <p className="muted">Aucune classe supplémentaire inférée.</p> : <div className="badges">{element.inferred_classes.map((value) => <span className="badge inferred" key={value}>{humanize(value)}</span>)}</div>}
          </Section>
        </>}

        {form && <form className="actor-form" onSubmit={(event) => { void saveElement(event) }}>
          <h2>{element ? `Modifier ${element.name}` : 'Nouvel élément réseau'}</h2>
          <Field label="Nom"><input required maxLength={120} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Field>
          <Field label="Type"><select value={form.kind} onChange={(event) => { const nextKind = event.target.value as NetworkKind; setForm({ ...form, kind: nextKind, underground: nextKind === 'LigneSouterraine' ? 'true' : form.underground }) }}>{options.kinds.map((item) => <option key={item} value={item}>{LABEL(item)}</option>)}</select></Field>
          {form.kind.startsWith('Ligne') && <>
            <div className="form-row"><Field label="Longueur (m)"><input type="number" min="0.01" step="any" value={form.length} onChange={(event) => setForm({ ...form, length: event.target.value })} /></Field><Field label="Section"><input type="number" min="0.01" step="any" value={form.section} onChange={(event) => setForm({ ...form, section: event.target.value })} /></Field></div>
            <div className="form-row"><Field label="Tension (kV)"><input type="number" min="0.01" step="any" value={form.voltage} onChange={(event) => setForm({ ...form, voltage: event.target.value })} /></Field><Field label="Taux de pertes (%)"><input type="number" min="0" max="100" step="any" value={form.loss_rate} onChange={(event) => setForm({ ...form, loss_rate: event.target.value })} /></Field></div>
            <Field label="Installation"><select value={form.underground} onChange={(event) => setForm({ ...form, underground: event.target.value })}><option value="">Non renseignée</option><option value="true">Souterraine</option><option value="false" disabled={form.kind === 'LigneSouterraine'}>Aérienne</option></select></Field>
          </>}
          {form.kind === 'PosteTransformation' && <><Field label="Tension (kV)"><input type="number" min="0.01" step="any" value={form.voltage} onChange={(event) => setForm({ ...form, voltage: event.target.value })} /></Field><Field label="Puissance de transformation"><input type="number" min="0.01" step="any" value={form.transformation_power} onChange={(event) => setForm({ ...form, transformation_power: event.target.value })} /></Field></>}
          {form.kind === 'CompteurIntelligent' && <><Field label="Identifiant compteur"><input maxLength={100} value={form.meter_identifier} onChange={(event) => setForm({ ...form, meter_identifier: event.target.value })} /></Field><Field label="Fréquence de relevé (jours)"><input type="number" min="1" max="3650" value={form.reading_frequency} onChange={(event) => setForm({ ...form, reading_frequency: event.target.value })} /></Field></>}
          <div className="form-row"><Field label="Année d’installation"><input type="number" min="1900" max="2100" value={form.installation_year} onChange={(event) => setForm({ ...form, installation_year: event.target.value })} /></Field>{['PosteTransformation', 'CompteurIntelligent'].includes(form.kind) && <Field label="Durée de vie (ans)"><input type="number" min="1" max="200" value={form.lifetime_years} onChange={(event) => setForm({ ...form, lifetime_years: event.target.value })} /></Field>}</div>
          {['PosteTransformation', 'CompteurIntelligent'].includes(form.kind) && <Field label="Coût d’installation (TND)"><input type="number" min="0" step="any" value={form.installation_cost} onChange={(event) => setForm({ ...form, installation_cost: event.target.value })} /></Field>}
          {form.kind.startsWith('Ligne') && <fieldset><legend>Entités reliées</legend><div className="checks">{relatedOptions.map((item) => <label className="check" key={item.id}><input type="checkbox" checked={form.related.includes(item.id)} onChange={() => toggle('related', item.id)} />{item.name} <span className="muted">({LABEL(item.kind.split(', ')[0])})</span></label>)}</div></fieldset>}
          <fieldset><legend>Gestionnaires</legend><div className="checks">{options.managers.map((item) => <label className="check" key={item.id}><input type="checkbox" checked={form.managers.includes(item.id)} onChange={() => toggle('managers', item.id)} />{item.name}</label>)}</div></fieldset>
          <div className="actions"><button type="submit" className="button primary" disabled={saving}>{saving ? 'Enregistrement…' : 'Enregistrer'}</button><button type="button" className="button" onClick={() => element ? setForm(null) : closePanel()}>Annuler</button></div>
        </form>}
      </aside>}
    </div>
  </>
}

function Tile({ label, value }: { label: string; value: string }) {
  return <div className="tile"><span className="card-label">{label}</span><strong className="tile-value">{value}</strong></div>
}

function Related({ title, items }: { title: string; items: RelatedElement[] }) {
  const uniqueItems = items.filter((item, index, list) => list.findIndex((other) => other.id === item.id) === index)
  return <Section title={title} count={uniqueItems.length}>
    {uniqueItems.length === 0 ? <p className="muted">Aucune relation déclarée.</p> : <div className="related-scroll"><DataTable compact>
      <thead><tr><th>Nom</th><th>Type</th></tr></thead>
      <tbody>{uniqueItems.map((item) => <tr key={item.id}><td className="strong">{item.name}</td><td><span className="badge">{LABEL(item.kind.split(', ')[0])}</span></td></tr>)}</tbody>
    </DataTable></div>}
  </Section>
}
