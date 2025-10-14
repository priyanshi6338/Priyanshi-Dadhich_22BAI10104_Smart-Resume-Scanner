import React, {useEffect, useState} from 'react'

export default function App(){
  const [resumes, setResumes] = useState([])
  const [selectedResume, setSelectedResume] = useState(null)
  const [jobTitle, setJobTitle] = useState('')
  const [jobDesc, setJobDesc] = useState('')
  const [matches, setMatches] = useState([])

  useEffect(()=>{ fetchResumes(); fetchMatches(); }, [])

  async function fetchResumes(){
    const r = await fetch('/api/resumes')
    const j = await r.json()
    setResumes(j)
  }
  async function fetchMatches(){
    const r = await fetch('/api/matches')
    const j = await r.json()
    setMatches(j)
  }
  async function upload(e){
    e.preventDefault()
    const file = e.target.resume.files[0]
    if(!file) return alert('choose a file')
    const fd = new FormData()
    fd.append('resume', file)
    const res = await fetch('/api/upload', {method:'POST', body:fd})
    const j = await res.json()
    alert('Uploaded: ' + j.resume_id)
    fetchResumes()
  }
  async function createJob(e){
    e.preventDefault()
    const res = await fetch('/api/jobs', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({title: jobTitle, description: jobDesc})
    })
    const j = await res.json()
    if(!selectedResume) return alert('Select a resume first')
    const mm = await fetch('/api/match', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({resume_id: selectedResume, job_id: j.job_id})
    })
    const mmj = await mm.json()
    alert('Match enqueued: ' + mmj.match_id)
    fetchMatches()
  }

  return (
    <div style={{padding:20, fontFamily:'Arial, sans-serif'}}>
      <h1>Smart Resume Scanner — Dashboard</h1>
      <section style={{marginBottom:20}}>
        <h2>Upload resume</h2>
        <form onSubmit={upload}>
          <input name="resume" type="file" accept=".pdf,.txt" />
          <button type="submit">Upload</button>
        </form>
      </section>

      <section style={{marginBottom:20}}>
        <h2>Resumes</h2>
        <ul>
          {resumes.map(r=>(
            <li key={r.id}>
              <label>
                <input type="radio" name="res" value={r.id} onChange={()=>setSelectedResume(r.id)} />
                {r.filename} — {new Date(r.created_at*1000).toLocaleString()}
              </label>
            </li>
          ))}
        </ul>
      </section>

      <section style={{marginBottom:20}}>
        <h2>Create Job + Enqueue Match</h2>
        <form onSubmit={createJob}>
          <input placeholder="Job title" value={jobTitle} onChange={e=>setJobTitle(e.target.value)} required />
          <br />
          <textarea placeholder="Job description" value={jobDesc} onChange={e=>setJobDesc(e.target.value)} rows={6} cols={60} required />
          <br />
          <button type="submit">Create job & enqueue match</button>
        </form>
      </section>

      <section>
        <h2>Matches</h2>
        <button onClick={fetchMatches}>Refresh</button>
        <ul>
          {matches.map(m=>(
            <li key={m.id}>
              <strong>{m.id}</strong> — resume: {m.resume_id} job: {m.job_id} status: {m.status}
              <div>
                TF-IDF: {m.tfidf ? m.tfidf.toFixed(3) : 'N/A'} | embedding: {m.embedding ? m.embedding.toFixed(3) : 'N/A'}
              </div>
              <details>
                <summary>LLM result</summary>
                <pre style={{whiteSpace:'pre-wrap',maxWidth:800}}>{m.llm_result}</pre>
              </details>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
