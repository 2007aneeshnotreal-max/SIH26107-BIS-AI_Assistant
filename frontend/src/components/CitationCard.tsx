import {ExternalLink,FileText} from 'lucide-react'
import type {Citation} from '../lib/types'
export default function CitationCard({citation}:{citation:Citation}){return <article className="citation-card"><div className="citation-icon"><FileText/></div><div><span className="eyebrow">{citation.document_id} · {citation.source_type==='demo'?'Demo source':'Source'}</span><h4>{citation.standard_number}</h4><p>{citation.source_title}</p><small>{citation.section||'Scope'}{citation.page?` · Page ${citation.page}`:''}</small><details><summary>View source excerpt</summary><p>{citation.excerpt}</p></details>{citation.source_url&&<a href={citation.source_url} target="_blank" rel="noreferrer">Open source <ExternalLink size={14}/></a>}</div></article>}

