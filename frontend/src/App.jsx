import { useEffect, useState } from 'react'
const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '')
const roleColors = { Admin: '#7c3aed', Moderator: '#2563eb', Debater: '#0f766e', Viewer: '#64748b' }
const makeProfile = () => {
  const raw = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`
  const id = `DBT-${raw.replace(/-/g, '').slice(0, 8).toUpperCase()}`
  return { id, name: `Debater-${id.slice(-4)}`, role: 'Debater', color: roleColors.Debater }
}
const readProfile = () => {
  try {
    const saved = JSON.parse(localStorage.getItem('debatence-profile') || 'null')
    return saved?.id ? saved : makeProfile()
  } catch { return makeProfile() }
}
const label = { needs_review: 'Needs review', valid: 'Valid point', invalid: 'Invalid point', unverified: 'Unverified', correct: 'Correct', incorrect: 'Incorrect' }
export default function App() {
  const [debates, setDebates] = useState([])
  const [active, setActive] = useState(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [profile, setProfile] = useState(readProfile)
  const { id: userId, name: author, role, color: profileColor } = profile
  const updateProfile = patch => setProfile(current => {
    const next = { ...current, ...patch }
    localStorage.setItem('debatence-profile', JSON.stringify(next))
    return next
  })
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [body, setBody] = useState('')
  const [stance, setStance] = useState('for')
  const [pointStatus, setPointStatus] = useState('needs_review')
  const [correctness, setCorrectness] = useState('unverified')
  const [evidence, setEvidence] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [webQuery, setWebQuery] = useState('')
  const [webResults, setWebResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [aiReview, setAiReview] = useState(null)
  const [reviewing, setReviewing] = useState(false)
  async function request(path, options={}) {
    const res = await fetch(`${API}${path}`, options)
    if (!res.ok) {
      let message = 'Request failed'
      try { message = (await res.json()).detail || message } catch {}
      throw new Error(message)
    }
    if (res.status === 204) return null
    return res.json()
  }
  async function refresh() {
    try { const rows = await request('/debates'); setDebates(rows); if (active) setActive(rows.find(d => d.id === active.id) || null) }
    catch (e) { setError(`API unavailable: ${e.message}`) }
  }
  useEffect(() => { localStorage.setItem('debatence-profile', JSON.stringify(profile)) }, [profile])\n  useEffect(() => { refresh() }, [])
  async function createDebate(e) {
    e.preventDefault(); if (!title.trim()) return
    try { const d = await request('/debates', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title, description})}); setTitle(''); setDescription(''); setActive(d); await refresh() }
    catch(e) { setError(e.message) }
  }
  async function deleteDebate() {
    if (!deleteTarget) return
    try {
      await request(`/debates/${deleteTarget.id}`, { method: 'DELETE' })
      if (active?.id === deleteTarget.id) setActive(null)
      setDeleteTarget(null)
      await refresh()
    } catch (e) { setError(e.message) }
  }
  async function searchWeb(e) {
    e.preventDefault()
    if (!webQuery.trim()) return
    setSearching(true); setError('')
    try {
      const result = await request('/research/search', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query:webQuery})})
      setWebResults(result.results || [])
    } catch(e) { setError(e.message) } finally { setSearching(false) }
  }
  async function reviewArgument() {
    if (!body.trim()) return
    setReviewing(true); setError(''); setAiReview(null)
    try {
      const evidenceText = webResults.map(r=>`${r.title}: ${r.snippet} (${r.url})`).join('\\n')
      const result = await request('/research/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({body, evidence:evidenceText})})
      setAiReview(result)
      if (result.assessment?.point_status) setPointStatus(result.assessment.point_status)
      if (result.assessment?.correctness) setCorrectness(result.assessment.correctness)
    } catch(e) { setError(e.message) } finally { setReviewing(false) }
  }
  async function postArgument(e) {
    e.preventDefault(); if (!body.trim() || !active) return
    setBusy(true); setError('')
    try {
      let attachment = {}
      if (evidence) { const fd = new FormData(); fd.append('file', evidence); attachment = await request('/evidence', {method:'POST', body:fd}) }
      await request(`/debates/${active.id}/arguments`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({author: `${author.trim() || 'Debater'} · ${role} · ${userId} · ${profileColor}`, body, stance, point_status:pointStatus, correctness, evidence_name:attachment.filename, evidence_url:attachment.url})})
      setBody(''); setEvidence(null); await refresh()
    } catch(e) { setError(e.message) } finally { setBusy(false) }
  }
  return <main className="shell">
    <header><div className="brand"><span className="mark">D</span><div><b>Debatence</b><small>Make your case. Back it up.</small></div></div><span className="online">● API connected when available</span></header>
    {error && <div className="error">{error}<button onClick={()=>setError('')}>×</button></div>}
    <div className="layout"><aside><div className="section-head"><div><small>YOUR WORKSPACE</small><h2>Debates</h2></div><span className="count">{debates.length}</span></div>
      {debates.map(d=><div className={`debate-item-wrap ${active?.id===d.id?'selected':''}`} key={d.id}><button className={`debate-item ${active?.id===d.id?'selected':''}`} onClick={()=>setActive(d)}><b>{d.title}</b><small>{d.arguments?.length || 0} arguments</small></button><button className="delete-debate" title="Delete debate" aria-label={`Delete ${d.title}`} onClick={()=>setDeleteTarget(d)}>×</button></div>)}
      {!debates.length && <p className="muted">No debates yet. Start one below.</p>}
      <form className="create" onSubmit={createDebate}><h3>Start a debate</h3><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Debate topic" required/><textarea value={description} onChange={e=>setDescription(e.target.value)} placeholder="Add context (optional)" rows="2"/><button className="primary">＋ Create debate</button></form>
    </aside>
    <section className="room">{active ? <><div className="room-title"><div><small>DEBATE ROOM</small><h1>{active.title}</h1><p>{active.description || 'Share clear arguments and support them with evidence.'}</p></div><span className="count">{active.arguments?.length || 0} posts</span></div>
      <section className="research-panel"><div className="research-heading"><b>Evidence & AI review</b><span>Web-connected research</span></div><form className="research-search" onSubmit={searchWeb}><input value={webQuery} onChange={e=>setWebQuery(e.target.value)} placeholder="Search the web for evidence related to this debate"/><button className="secondary" disabled={searching}>{searching?'Searching…':'Search web'}</button></form>{webResults.length>0&&<div className="source-results">{webResults.map((r,i)=><article className="source-result" key={r.url||i}><a href={r.url} target="_blank" rel="noreferrer">{r.title||r.source||r.url}</a><small>{r.source}</small><p>{r.snippet}</p></article>)}</div>}</section>
      <div className="thread">{(active.arguments || []).map(a=>{ const parts=(a.author||'Debater').split(' · '); const messageName=parts[0]||'Debater'; const messageRole=parts[1]||'Debater'; const messageId=parts[2]||'Guest'; const messageColor=parts[3]||roleColors[messageRole]||'#64748b'; const mine=messageId===userId; return <article className={`argument ${mine?'argument-mine':'argument-other'} role-${messageRole.toLowerCase()}`} key={a.id} style={{'--user-accent':messageColor}}><div className="avatar" style={{backgroundColor:`${messageColor}20`,color:messageColor}}>{messageName[0]?.toUpperCase()}</div><div className="argument-content"><div className="arg-head"><b>{messageName}</b><span className={`role-pin role-${messageRole.toLowerCase()}`}>{messageRole}</span><span className="user-id">{messageId}</span><span className={`stance ${a.stance}`}>{a.stance.toUpperCase()}</span>{mine&&<span className="you-pin">YOU</span>}</div><p>{a.body}</p><div className="badges"><span className={`tag ${a.point_status}`}>{label[a.point_status]}</span><span className={`tag ${a.correctness}`}>{label[a.correctness]}</span></div>{a.evidence_url && <a className="evidence" href={`${API.replace(/\/api$/, '')}${a.evidence_url}`} target="_blank" rel="noreferrer">↗ Evidence: {a.evidence_name}</a>}</div></article> })}
      {!active.arguments?.length && <div className="empty"><div>◌</div><h3>The floor is yours</h3><p>Start the discussion with your opening argument.</p></div>}</div>
      {aiReview && <section className="ai-review"><b>AI preliminary indication</b><span className={`tag ${aiReview.assessment?.correctness}`}>{label[aiReview.assessment?.correctness] || 'Unverified'}</span><span className={`tag ${aiReview.assessment?.point_status}`}>{label[aiReview.assessment?.point_status] || 'Needs review'}</span><p>{aiReview.assessment?.reason}</p>{aiReview.assessment?.evidence_needed?.length>0&&<p><b>Evidence to add:</b> {aiReview.assessment.evidence_needed.join('; ')}</p>}<small>{aiReview.disclaimer}</small></section>}
      <form className="composer" onSubmit={postArgument}><div className="composer-top"><span className="avatar small" style={{backgroundColor:profileColor+"20",color:profileColor}}>{author[0]?.toUpperCase() || 'D'}</span><input className="author" value={author} onChange={e=>updateProfile({name:e.target.value})} aria-label="Display name" placeholder="Display name"/><span className="identity-id" title="Automatically assigned user ID">{userId}</span><select value={role} onChange={e=>updateProfile({role:e.target.value,color:roleColors[e.target.value]})} aria-label="Profile role"><option>Debater</option><option>Moderator</option><option>Viewer</option></select><input className="color-picker" type="color" value={profileColor} onChange={e=>updateProfile({color:e.target.value})} title="Profile accent color" aria-label="Profile accent color"/><select value={stance} onChange={e=>setStance(e.target.value)}><option value="for">For</option><option value="against">Against</option></select></div><textarea value={body} onChange={e=>setBody(e.target.value)} placeholder="Make your argument. What is your point, and why should others agree?" rows="3" required/><div className="composer-bottom"><button type="button" className="secondary ai-button" onClick={reviewArgument} disabled={reviewing||!body.trim()}>{reviewing?'Reviewing…':'✦ AI review'}</button><label className="attach">＋ Attach evidence<input type="file" accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx" onChange={e=>setEvidence(e.target.files?.[0] || null)}/></label>{evidence && <span className="file">{evidence.name}</span>}<span className="spacer"/><select value={pointStatus} onChange={e=>setPointStatus(e.target.value)} aria-label="Point status"><option value="needs_review">Needs review</option><option value="valid">Valid point</option><option value="invalid">Invalid point</option></select><select value={correctness} onChange={e=>setCorrectness(e.target.value)} aria-label="Correctness"><option value="unverified">Unverified</option><option value="correct">Correct</option><option value="incorrect">Incorrect</option></select><button className="primary" disabled={busy || !body.trim()}>{busy?'Posting…':'Post argument →'}</button></div></form>
    </> : <div className="welcome"><div className="welcome-icon">⚖</div><h1>Make room for better arguments.</h1><p>Create a debate or select one from your workspace to join the conversation.</p></div>}</section></div>
    {deleteTarget && <div className="modal-backdrop" role="presentation"><section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="delete-title"><h2 id="delete-title">Delete debate?</h2><p>Delete “{deleteTarget.title}” and all of its arguments? This action cannot be undone.</p><div className="modal-actions"><button className="secondary" onClick={()=>setDeleteTarget(null)}>Cancel</button><button className="danger" onClick={deleteDebate}>Delete debate</button></div></section></div>}
  </main>
}
