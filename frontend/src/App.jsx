import { useEffect, useState } from 'react'
const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '')
const roleColors = { Initiator: '#7c3aed', Admin: '#2563eb', Debater: '#0f766e', Viewer: '#64748b' }
const makeProfile = () => {
  const raw = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`
  const id = `DBT-${raw.replace(/-/g, '').slice(0, 8).toUpperCase()}`
  return { id, name: `Debater-${id.slice(-4)}`, role: 'Viewer', color: roleColors.Viewer }
}
const readProfile = () => {
  try {
    const saved = JSON.parse(localStorage.getItem('debatence-profile') || 'null')
    return saved?.id ? saved : makeProfile()
  } catch { return makeProfile() }
}
const label = { needs_review: 'Needs evidence', valid: 'Supported', invalid: 'Contradicted', unverified: 'Unclear', correct: 'Supported', incorrect: 'Contradicted' }
export default function App() {
  const [debates, setDebates] = useState([])
  const [active, setActive] = useState(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [search, setSearch] = useState('')
  const [debateStats, setDebateStats] = useState(null)
  const [comments, setComments] = useState([])
  const [commentText, setCommentText] = useState('')
  const [commentSort, setCommentSort] = useState('newest')
  const [commentsOpen, setCommentsOpen] = useState(false)
  const [profile, setProfile] = useState(readProfile)
  const [ownedDebates, setOwnedDebates] = useState(() => JSON.parse(localStorage.getItem('debatence-owned-debates') || '[]'))
  const [debateRole, setDebateRole] = useState('Viewer')
  const [serverRoleRequests, setServerRoleRequests] = useState([])
  const [requestPending, setRequestPending] = useState(false)
  const { id: userId, name: author, role: profileRole, color: profileColor } = profile
  const isActiveCreator = !!active && ownedDebates.includes(active.id)
  const role = isActiveCreator ? 'Initiator' : debateRole
  const updateProfile = patch => setProfile(current => {
    const next = { ...current, ...patch }
    localStorage.setItem('debatence-profile', JSON.stringify(next))
    return next
  })
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [body, setBody] = useState('')
  const [stance, setStance] = useState('for')
  const [pointStatus, setPointStatus] = useState('')
  const [correctness, setCorrectness] = useState('')
  const [evidence, setEvidence] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [roleRequests, setRoleRequests] = useState(() => JSON.parse(localStorage.getItem('debatence-role-requests') || '[]'))
  const [debateCreators, setDebateCreators] = useState(() => JSON.parse(localStorage.getItem('debatence-debate-creators') || '{}'))
  const [notice, setNotice] = useState('')
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
  useEffect(() => { localStorage.setItem('debatence-profile', JSON.stringify(profile)) }, [profile])
  useEffect(() => { refresh() }, [])
  useEffect(() => {
    if (!active?.id) { setDebateStats(null); setComments([]); return }
    let cancelled = false
    Promise.all([
      request(`/debates/${active.id}/stats?user_id=${encodeURIComponent(userId)}`),
      request(`/debates/${active.id}/comments`)
    ]).then(([stats, rows]) => { if (!cancelled) { setDebateStats(stats); setComments(rows) } }).catch(()=>{})
    return () => { cancelled = true }
  }, [active?.id, userId])
  useEffect(() => {
    if (!active?.id) { setDebateRole('Viewer'); setServerRoleRequests([]); return }
    let cancelled = false
    request(`/debates/${active.id}/role?user_id=${encodeURIComponent(userId)}`)
      .then(data => { if (!cancelled) setDebateRole(data.role || 'Viewer') })
      .catch(() => { if (!cancelled) setDebateRole(ownedDebates.includes(active.id) ? 'Initiator' : 'Viewer') })
    if (active.creator_id === userId || ownedDebates.includes(active.id)) {
      request(`/debates/${active.id}/role-requests?initiator_id=${encodeURIComponent(userId)}`)
        .then(rows => { if (!cancelled) setServerRoleRequests(rows) })
        .catch(() => { if (!cancelled) setServerRoleRequests([]) })
    } else setServerRoleRequests([])
    return () => { cancelled = true }
  }, [active?.id, active?.creator_id, userId, ownedDebates])
  async function createDebate(e) {
    e.preventDefault(); if (!title.trim()) return
    try { const d = await request('/debates', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title, description, creator_id:userId, creator_name:author})}); setTitle(''); setDescription(''); setActive(d); const creators={...debateCreators,[d.id]:{id:userId,name:author}}; setDebateCreators(creators); localStorage.setItem('debatence-debate-creators',JSON.stringify(creators)); const own=[...ownedDebates,d.id]; setOwnedDebates(own); localStorage.setItem('debatence-owned-debates',JSON.stringify(own)); updateProfile({role:'Viewer',color:roleColors.Viewer}); await refresh() }
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
  async function postArgument(e) {
    e.preventDefault(); if (!body.trim() || !active || !['Initiator','Admin','Debater'].includes(role)) return
    setBusy(true); setError('')
    try {
      let attachment = {}
      if (evidence) { const fd = new FormData(); fd.append('file', evidence); attachment = await request('/evidence', {method:'POST', body:fd}) }
      await request(`/debates/${active.id}/arguments`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({author: `${author.trim() || 'Debater'} · ${role} · ${userId} · ${profileColor}`, body, stance, point_status:pointStatus || 'needs_review', correctness:correctness || 'unverified', evidence_name:attachment.filename, evidence_url:attachment.url})})
      setBody(''); setEvidence(null); await refresh()
    } catch(e) { setError(e.message) } finally { setBusy(false) }
  }
  return <main className="shell">
    <header><div className="brand"><span className="mark">D</span><div><b>Debatence</b><small>Make your case. Back it up.</small></div></div><div className="header-right"><span className="online">● API connected when available</span><div className="profile-chip"><span className="profile-avatar" style={{backgroundColor:profileColor}}>{author[0]?.toUpperCase() || "U"}</span><div className="profile-fields"><input aria-label="Your profile name" value={author} onChange={e=>updateProfile({name:e.target.value})}/><small>{role} · {userId}</small></div></div></div></header>
    {error && <div className="error">{error}<button onClick={()=>setError('')}>×</button></div>}
    <div className="layout"><aside><div className="section-head"><div><small>YOUR WORKSPACE</small><h2>Debates</h2></div><span className="count">{debates.length}</span></div>
      <input className="discovery-search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search debates…" aria-label="Search debates"/>
      {debates.filter(d=>`${d.title} ${d.description||''} ${d.category||''}`.toLowerCase().includes(search.toLowerCase())).map(d=><div className={`debate-item-wrap ${active?.id===d.id?'selected':''}`} key={d.id}><button className={`debate-item ${active?.id===d.id?'selected':''}`} onClick={()=>setActive(d)}><b>{d.title}</b><small>{d.arguments?.length || 0} arguments</small></button><button className="delete-debate" title="Delete debate" aria-label={`Delete ${d.title}`} onClick={()=>setDeleteTarget(d)}>×</button></div>)}
      {!debates.length && <p className="muted">No debates yet. Start one below.</p>}
      <form className="create" onSubmit={createDebate}><h3>Start a debate</h3><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Debate topic" required/><textarea value={description} onChange={e=>setDescription(e.target.value)} placeholder="Add context (optional)" rows="2"/>
        <button className="primary">＋ Create debate</button></form>
    </aside>
    <section className="room">{active ? <><div className="room-title"><div><small>DEBATE ROOM</small><h1>{active.title}</h1><div className="creator-line">Created by <b>{active.creator_name || debateCreators[active.id]?.name || (ownedDebates.includes(active.id) ? author : 'Debate initiator')}</b><span className="role-pin role-admin">{active.creator_id===userId || ownedDebates.includes(active.id) ? 'INITIATOR' : 'CREATOR'}</span></div><p>{active.description || 'Share clear arguments and support them with evidence.'}</p></div><span className="count">{active.arguments?.length || 0} posts</span></div>
      <div className="debate-meta"><span className={`status-pill status-${active.status||'open'}`}>{(active.status||'open').toUpperCase()}</span>
      {active.creator_id===userId && <div className="lifecycle-actions">{['open','paused','completed'].map(st=><button key={st} className="secondary" onClick={async()=>{try{const d=await request(`/debates/${active.id}?initiator_id=${encodeURIComponent(userId)}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:st})});setActive(d);await refresh()}catch(e){setError(e.message)}}}>{st}</button>)}</div>}</div>
      <div className="engagement"><button onClick={async()=>{try{await request(`/debates/${active.id}/vote`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,vote:'up'})});setDebateStats(await request(`/debates/${active.id}/stats?user_id=${encodeURIComponent(userId)}`))}catch(e){setError(e.message)}}}>▲ {debateStats?.upvotes||0}</button><button onClick={async()=>{try{await request(`/debates/${active.id}/vote`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,vote:'down'})});setDebateStats(await request(`/debates/${active.id}/stats?user_id=${encodeURIComponent(userId)}`))}catch(e){setError(e.message)}}}>▼ {debateStats?.downvotes||0}</button><button onClick={async()=>{try{await request(`/debates/${active.id}/bookmark?user_id=${encodeURIComponent(userId)}`,{method:'POST'});setDebateStats(await request(`/debates/${active.id}/stats?user_id=${encodeURIComponent(userId)}`))}catch(e){setError(e.message)}}>{debateStats?.bookmarked ? '★ Saved' : '☆ Save debate'}</button></div>
      <button className="comments-toggle" type="button" onClick={() => setCommentsOpen(open => !open)} aria-expanded={commentsOpen}>
        {commentsOpen ? 'Hide comments' : `Comments (${comments.length})`}
      </button>
      {commentsOpen && (
        <section className="comments-panel youtube-comments">
          <div className="comments-heading">
            <div><h3>Comments <span>{comments.length}</span></h3><p>Join the conversation around this debate.</p></div>
            <label className="comment-sort">Sort by <select value={commentSort} onChange={e => setCommentSort(e.target.value)}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
          </div>
          <form className="youtube-comment-form" onSubmit={async e => { e.preventDefault(); if (!commentText.trim()) return; try { await request(`/debates/${active.id}/comments`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: userId, user_name: author, body: commentText }) }); setCommentText(''); setComments(await request(`/debates/${active.id}/comments`)); setDebateStats(await request(`/debates/${active.id}/stats?user_id=${encodeURIComponent(userId)}`)); } catch (e) { setError(e.message); } }}>
            <span className="comment-avatar">{author[0]?.toUpperCase() || 'U'}</span>
            <div className="comment-compose">
              <input value={commentText} onChange={e => setCommentText(e.target.value)} placeholder="Add a comment…" maxLength="3000" aria-label="Add a comment" />
              <div className="comment-compose-actions"><span>{commentText.length}/3000</span><button type="button" className="secondary" onClick={() => setCommentText('')}>Cancel</button><button className="primary" disabled={!commentText.trim() || active.status !== 'open'}>Comment</button></div>
            </div>
          </form>
          <div className="comment-list">
            {[...comments].sort((a, b) => commentSort === 'newest' ? new Date(b.created_at || 0) - new Date(a.created_at || 0) : new Date(a.created_at || 0) - new Date(b.created_at || 0)).map(c => <article className="comment youtube-comment" key={c.id}><span className="comment-avatar muted-avatar">{(c.user_name || 'U')[0]?.toUpperCase()}</span><div className="comment-main"><div className="comment-user-line"><b>{c.user_name}</b><span>{c.created_at ? new Date(c.created_at).toLocaleString() : ''}</span></div><p>{c.body}</p><div className="comment-actions"><span title="Comments are shown chronologically">Discussion</span></div></div></article>)}
            {!comments.length && <div className="comments-empty">No comments yet. Be the first to share a thought.</div>}
          </div>
        </section>
      )}
      <div className="thread">{(active.arguments || []).map(a=>{ const parts=(a.author||'Debater').split(' · '); const messageName=parts[0]||'Debater'; const messageRole=parts[1]||'Debater'; const messageId=parts[2]||'Guest'; const messageColor=parts[3]||roleColors[messageRole]||'#64748b'; const mine=messageId===userId; const isCreator=debateCreators[active.id]?.id===messageId || (ownedDebates.includes(active.id)&&mine); return <article className={`argument ${mine?'argument-mine':'argument-other'} ${isCreator?'argument-creator':''} role-${messageRole.toLowerCase()}`} key={a.id} style={{'--user-accent':messageColor}}><div className="avatar" style={{backgroundColor:`${messageColor}20`,color:messageColor}}>{messageName[0]?.toUpperCase()}</div><div className="argument-content"><div className="arg-head"><b>{messageName}</b><span className={`role-pin role-${messageRole.toLowerCase()}`}>{messageRole}</span><span className="user-id">{messageId}</span><span className={`stance ${a.stance}`}>{a.stance.toUpperCase()}</span>{mine&&<span className="you-pin">YOU</span>}</div><p>{a.body}</p><div className="badges ai-badges"><span className={`tag ai-${a.ai_status||'pending'}`}>AI {a.ai_status==='complete'?'stance':a.ai_status==='unavailable'?'not configured':a.ai_status==='failed'?'analysis failed':'analyzing'}</span>{a.ai_stance && <span className={`tag ai-stance-${a.ai_stance}`}>AI indicates: {({supports:'For',opposes:'Against',unrelated:'Unrelated',unclear:'Unclear',unable_to_assess:'Unable to assess'})[a.ai_stance]||a.ai_stance}</span>}{a.stance_match==='differs' && <span className="tag ai-mismatch">Stance differs from selection</span>}{a.ai_confidence && <span className="tag ai-confidence">Confidence: {a.ai_confidence}</span>}{a.ai_analysis && <span className="ai-explanation">{a.ai_analysis}</span>}</div>{(a.body||'').trim().split(/\s+/).length >= 8 && (a.point_status !== 'needs_review' || a.correctness !== 'unverified') && <div className="badges"><span className={`tag ${a.point_status}`}>{label[a.point_status]}</span><span className={`tag ${a.correctness}`}>{label[a.correctness]}</span></div>}{a.evidence_url && <a className="evidence" href={`${API.replace(/\/api$/, '')}${a.evidence_url}`} target="_blank" rel="noreferrer">↗ Evidence: {a.evidence_name}</a>}<button className="report-argument" onClick={async()=>{const reason=window.prompt('Report reason: spam, harassment, misinformation, abuse, or other','other');if(!reason)return;try{await request(`/debates/${active.id}/report`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reporter_id:userId,reason,argument_id:a.id})});setNotice('Report submitted for review.')}catch(e){setError(e.message)}}}>Report</button></div></article> })}
      {!active.arguments?.length && <div className="empty"><div>◌</div><h3>The floor is yours</h3><p>Start the discussion with your opening argument.</p></div>}</div>
      {role === 'Viewer' && !ownedDebates.includes(active.id) && <div className="role-request"><p>You’re viewing this debate. Request the Debater role to contribute arguments.</p><button type="button" className="secondary" onClick={async()=>{try{setRequestPending(true);await request(`/debates/${active.id}/role-requests`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({requester_id:userId,requester_name:author})});setNotice('Role request submitted to debate leadership.')}catch(e){setError(e.message)}finally{setRequestPending(false)}}} disabled={requestPending}>{requestPending ? 'Sending...' : 'Request Debater role'}</button></div>}
      {notice && <div className="notice">{notice}<button onClick={()=>setNotice('')}>×</button></div>}
      {(['Initiator','Admin','Debater'].includes(role) || ownedDebates.includes(active.id)) ? <form className="composer" onSubmit={postArgument}><div className="composer-top"><span className="avatar small" style={{backgroundColor:profileColor+"20",color:profileColor}}>{author[0]?.toUpperCase() || 'D'}</span><input className="author" value={author} onChange={e=>updateProfile({name:e.target.value})} aria-label="Display name" placeholder="Display name"/><span className="identity-id" title="Automatically assigned user ID">{userId}</span>{ownedDebates.includes(active?.id) ? <span className="role-pin role-admin">INITIATOR</span> : <span className={`role-pin role-${role.toLowerCase()}`}>{role}</span>}<select value={stance} onChange={e=>setStance(e.target.value)}><option value="for">For</option><option value="against">Against</option></select></div><textarea value={body} onChange={e=>setBody(e.target.value)} placeholder="Make your argument. What is your point, and why should others agree?" rows="3" required/><div className="composer-bottom"><label className="attach">＋ Attach evidence<input type="file" accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx" onChange={e=>setEvidence(e.target.files?.[0] || null)}/></label>{evidence && <span className="file">{evidence.name}</span>}<span className="spacer"/><button className="primary" disabled={busy || !body.trim()}>{busy?'Posting…':'Post argument →'}</button></div></form> : null}
      {(active.creator_id===userId || ownedDebates.includes(active.id)) && <section className="role-requests"><b>Role requests</b>{serverRoleRequests.length===0 ? <p>No pending requests.</p> : serverRoleRequests.map(r=><div key={r.id}><span>{r.requester_name} requests Debater</span><span className="request-actions"><button onClick={async()=>{try{await request(`/debates/${active.id}/role-requests/${r.id}/decision`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({initiator_id:userId,decision:'approve'})});setServerRoleRequests(rows=>rows.filter(x=>x.id!==r.id));setNotice(`${r.requester_name} approved as Debater.`)}catch(e){setError(e.message)}}}>Approve</button><button onClick={async()=>{try{await request(`/debates/${active.id}/role-requests/${r.id}/decision`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({initiator_id:userId,decision:'reject'})});setServerRoleRequests(rows=>rows.filter(x=>x.id!==r.id))}catch(e){setError(e.message)}}}>Reject</button></span></div>)}</section>}
    </> : <div className="welcome"><div className="welcome-icon">⚖</div><h1>Make room for better arguments.</h1><p>Create a debate or select one from your workspace to join the conversation.</p></div>}</section></div>
    {deleteTarget && <div className="modal-backdrop" role="presentation"><section className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="delete-title"><h2 id="delete-title">Delete debate?</h2><p>Delete “{deleteTarget.title}” and all of its arguments? This action cannot be undone.</p><div className="modal-actions"><button className="secondary" onClick={()=>setDeleteTarget(null)}>Cancel</button><button className="danger" onClick={deleteDebate}>Delete debate</button></div></section></div>}
  </main>
}
