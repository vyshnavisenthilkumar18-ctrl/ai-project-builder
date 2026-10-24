import React, {useEffect, useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Activity, ArrowDownToLine, Bot, Check, ChevronRight, CircleHelp, Code2, ExternalLink, FileCode2, FileText, Folder, Github, Layers3, LoaderCircle, LockKeyhole, Play, Plus, Rocket, ShieldCheck, Sparkles, Upload, X, Zap} from 'lucide-react';
import './style.css';

const API = '/api';
async function api(path, options={}) {
  const res = await fetch(API+path,{credentials:'include',...options});
  const data = await res.json().catch(()=>({detail:'Unexpected server response'}));
  if(!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}
function App(){
 const [topic,setTopic]=useState('Digital Twin Intelligence System for Real-Time Equipment Monitoring and Predictive Optimization');
 const [language,setLanguage]=useState('Python');
 const [framework,setFramework]=useState('React + Vite / FastAPI');
 const [file,setFile]=useState(null),[project,setProject]=useState(null),[files,setFiles]=useState([]);
 const [selected,setSelected]=useState(''),[busy,setBusy]=useState(false),[stage,setStage]=useState('');
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[github,setGithub]=useState({connected:false,configured:false});
 const [repoMode,setRepoMode]=useState('create'),[repoName,setRepoName]=useState('digital-twin-equipment-monitoring'),[description,setDescription]=useState('AI-powered equipment monitoring and predictive optimization'),[visibility,setVisibility]=useState('private'),[branch,setBranch]=useState('main'),[repos,setRepos]=useState([]),[showPublish,setShowPublish]=useState(false);
 const current=files.find(f=>f.path===selected);
 useEffect(()=>{api('/github/status').then(setGithub).catch(()=>{}); const q=new URLSearchParams(location.search);if(q.get('github')==='connected')setNotice('GitHub connected successfully.');if(q.get('github')==='denied')setError('GitHub authorization was cancelled.');if(q.has('github'))history.replaceState({},'',location.pathname);},[]);
 const formatSize=n=>n<1024?`${n} B`:`${(n/1024).toFixed(1)} KB`;
 async function generate(){
  setError('');setNotice('');setBusy(true);setStage('Reading project requirements');
  try{
   let brief=topic;
   if(file){const fd=new FormData();fd.append('topic',topic);fd.append('file',file);const a=await api('/projects/analyze',{method:'POST',body:fd});brief=a.topic;}
   if(brief.trim().length<10)throw new Error('Please enter a project topic or upload a specification.');
   setStage('Generating application source files');
   const p=await api('/projects/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic:brief,language,framework})});
   setProject(p);setFiles([]);setStage('Loading generated file tree');
   const result=await api(`/projects/${p.project_id}/files`);setFiles(result.files);setSelected(result.files[0]?.path||'');setNotice(`Generated ${result.files.length} files. Review the code before running or publishing.`);setStage('');
  }catch(e){setError(e.message);setStage('');}finally{setBusy(false);}
 }
 async function connectGithub(){setError('');try{if(!github.configured)throw new Error('GitHub OAuth is not configured on the backend. Add the GitHub OAuth credentials to backend/.env.');location.href=API+'/github/login';}catch(e){setError(e.message);}}
 async function openPublish(){setError('');try{if(!project)throw new Error('Generate a project first.');if(!github.connected)throw new Error('Connect GitHub before publishing.');const list=await api('/github/repositories');setRepos(list);setShowPublish(true);}catch(e){setError(e.message);}}
 async function publish(){setError('');setNotice('');setBusy(true);setStage('Publishing files to GitHub');try{const out=await api('/github/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:project.project_id,mode:repoMode,repo_name:repoName,description,private:visibility==='private',branch,confirm:true})});setNotice(`Published ${out.published_files} files to ${out.repository_url}`);setShowPublish(false);}catch(e){setError(e.message);}finally{setBusy(false);setStage('');}}
 const tree=useMemo(()=>files.map(f=>({...f,depth:f.path.split('/').length-1,name:f.path.split('/').pop()})),[files]);
 return <div className="app">
  <aside className="sidebar"><div className="brand"><div className="brand-icon"><Layers3 size={22}/></div><div><b>buildwise<span>.</span></b><small>AI PROJECT BUILDER</small></div></div>
   <div className="side-label">WORKSPACE</div><div className="nav active"><Layers3 size={17}/> Project builder</div><div className="nav muted"><Activity size={17}/> Recent projects <span className="soon">SOON</span></div>
   <div className="side-label tools-label">TOOLS</div><div className="nav muted"><Code2 size={17}/> Code workspace</div><div className="nav muted"><Github size={17}/> GitHub publishing</div>
   <div className="sidebar-bottom"><div className="help-icon"><CircleHelp size={17}/></div><div><b>Need a hand?</b><small>See setup instructions in README</small></div></div>
  </aside>
  <main className="main"><header className="topbar"><div className="crumb">Workspace <ChevronRight size={14}/> <b>Project builder</b></div><div className="top-right"><span className="status-dot"></span><span>Local workspace</span><div className="avatar">AI</div></div></header>
   <div className="content"><div className="welcome"><div><div className="eyebrow"><Sparkles size={14}/> FROM IDEA TO CODEBASE</div><h1>Build something <span>intelligent.</span></h1><p>Describe your idea. Let AI scaffold your project, then download it or publish it to GitHub.</p></div><div className="welcome-art"><div className="orb orb-one"></div><div className="orb orb-two"></div><div className="art-core"><Bot size={38}/></div><div className="art-tag tag-a"><Code2 size={13}/> Code</div><div className="art-tag tag-b"><Zap size={13}/> AI</div></div></div>
   {error&&<div className="alert error"><X size={17}/><span>{error}</span><button onClick={()=>setError('')}><X size={15}/></button></div>}
   {notice&&<div className="alert success"><Check size={17}/><span>{notice}</span><button onClick={()=>setNotice('')}><X size={15}/></button></div>}
   <div className="workspace-grid"><section className="panel input-panel"><div className="panel-head"><div className="step">01</div><div><h2>Project brief</h2><p>Tell us what you want to build</p></div><span className="required">REQUIRED</span></div>
    <label className="field-label" htmlFor="topic">PROJECT TOPIC & REQUIREMENTS</label><textarea id="topic" value={topic} onChange={e=>setTopic(e.target.value)} placeholder="Describe your project, key features, users, data, and expected outcomes..." rows="8"/>
    <label className="upload-zone"><input type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp" onChange={e=>setFile(e.target.files?.[0]||null)}/><div className="upload-symbol"><Upload size={19}/></div><div><b>{file?file.name:'Upload project specification'}</b><small>{file?`${formatSize(file.size)} · click to replace`:'PDF, DOCX, TXT or image · max 10 MB'}</small></div>{file?<button type="button" className="icon-button" onClick={e=>{e.preventDefault();setFile(null)}}><X size={16}/></button>:<span className="browse">Browse</span>}</label>
    <div className="field-row"><div className="field"><label className="field-label">LANGUAGE</label><select value={language} onChange={e=>setLanguage(e.target.value)}><option>Python</option><option>JavaScript</option><option>TypeScript</option><option>Java</option><option>C#</option><option>Go</option></select></div><div className="field"><label className="field-label">FRAMEWORK / STACK</label><select value={framework} onChange={e=>setFramework(e.target.value)}><option>React + Vite / FastAPI</option><option>FastAPI + HTML/CSS/JS</option><option>Flask + HTML/CSS/JS</option><option>Next.js</option><option>Django</option><option>Node.js + Express</option><option>Streamlit</option></select></div></div>
    <button className="primary generate" onClick={generate} disabled={busy}><span>{busy?<LoaderCircle className="spin" size={18}/>:<Sparkles size={18}/>}</span>{busy?'Working on your project':'Generate project'}<ChevronRight size={17}/></button><div className="secure-note"><ShieldCheck size={14}/> Your API keys stay on the backend</div>
   </section>
   <section className="panel output-panel"><div className="panel-head"><div className="step">02</div><div><h2>Generated workspace</h2><p>Explore files and preview your code</p></div><span className={`live-pill ${project?'ready':''}`}><span></span>{project?'READY':'AWAITING INPUT'}</span></div>
    {!project?<div className="empty-state"><div className="empty-illustration"><div className="empty-file"><FileCode2 size={31}/></div><div className="empty-spark"><Sparkles size={18}/></div></div><h3>Your codebase starts here</h3><p>Once generated, your project files will appear here with a code preview.</p><div className="empty-steps"><div><span>1</span> Describe</div><ChevronRight size={14}/><div><span>2</span> Generate</div><ChevronRight size={14}/><div><span>3</span> Publish</div></div></div>:<><div className="project-meta"><div className="project-icon"><Folder size={18}/></div><div><b>{project.project_name}</b><small>{files.length} files · {project.summary}</small></div></div><div className="file-layout"><div className="file-list"><div className="file-list-head"><Folder size={14}/> FILE EXPLORER <span>{files.length}</span></div>{tree.map(f=><button key={f.path} className={`file-item ${selected===f.path?'selected':''}`} style={{paddingLeft:12+f.depth*12}} onClick={()=>setSelected(f.path)} title={f.path}><FileText size={14}/><span>{f.name}</span></button>)}</div><div className="preview"><div className="preview-head"><span><Code2 size={14}/>{current?.name||'Select a file'}</span><span className="language-badge">{(current?.name||'').split('.').pop()}</span></div><pre>{current?.content||'Select a file from the explorer to preview its contents.'}</pre></div></div><div className="action-row"><a className="secondary" href={project?`${API}/projects/${project.project_id}/download`:'#'} onClick={e=>{if(!project)e.preventDefault()}}><ArrowDownToLine size={16}/> Download ZIP</a><button className="github-button" onClick={openPublish}><Github size={16}/> Publish to GitHub <ExternalLink size={13}/></button></div></>}
   </section></div>
   <div className="bottom-grid"><div className="info-card"><div className="info-icon purple"><ShieldCheck size={18}/></div><div><b>Secure by design</b><p>Secrets stay server-side. Generated archives filter environment files and common build artifacts.</p></div></div><div className="info-card"><div className="info-icon blue"><Rocket size={18}/></div><div><b>Ready for your workflow</b><p>Review your code, download the ZIP, or commit the generated files to a GitHub repository.</p></div></div></div>
   {stage&&<div className="stage-bar"><LoaderCircle size={16} className="spin"/>{stage}<div className="stage-progress"><span/></div></div>}
   <footer><span>buildwise. <span className="footer-muted">· AI Project Builder</span></span><span><LockKeyhole size={12}/> Private by default</span></footer>
   </div>
  </main>
  {showPublish&&<div className="modal-backdrop" onClick={()=>setShowPublish(false)}><div className="modal" onClick={e=>e.stopPropagation()}><div className="modal-head"><div><div className="eyebrow"><Github size={14}/> GITHUB PUBLISHING</div><h2>Publish your project</h2><p>Review the destination before creating a commit.</p></div><button className="icon-button" onClick={()=>setShowPublish(false)}><X size={18}/></button></div>
   <div className="repo-toggle"><button className={repoMode==='create'?'chosen':''} onClick={()=>setRepoMode('create')}><Plus size={15}/> New repository</button><button className={repoMode==='existing'?'chosen':''} onClick={()=>setRepoMode('existing')}><Folder size={15}/> Existing repository</button></div>
   {repoMode==='existing'&&<div className="field"><label className="field-label">YOUR REPOSITORIES</label><select value={repoName} onChange={e=>setRepoName(e.target.value)}>{repos.map(r=><option key={r.id} value={r.name}>{r.full_name}</option>)}</select></div>}
   <div className="field"><label className="field-label">REPOSITORY NAME</label><input value={repoName} onChange={e=>setRepoName(e.target.value)} /></div>
   <div className="field"><label className="field-label">DESCRIPTION</label><input value={description} onChange={e=>setDescription(e.target.value)} maxLength="350"/></div>
   <div className="field-row"><div className="field"><label className="field-label">VISIBILITY</label><select value={visibility} onChange={e=>setVisibility(e.target.value)}><option value="private">Private</option><option value="public">Public</option></select></div><div className="field"><label className="field-label">TARGET BRANCH</label><input value={branch} onChange={e=>setBranch(e.target.value)}/></div></div>
   <div className="publish-warning"><ShieldCheck size={17}/><div><b>Confirm before publishing</b><p>{files.length} files will be committed. Review the generated code and ensure it contains no private data.</p></div></div>
   <div className="modal-actions"><button className="secondary" onClick={()=>setShowPublish(false)}>Cancel</button><button className="primary" disabled={busy||!repoName.trim()} onClick={publish}><Github size={16}/>{busy?'Publishing…':'Confirm & publish'}</button></div>
  </div></div>}
 </div>
}
createRoot(document.getElementById('root')).render(<App/>);
