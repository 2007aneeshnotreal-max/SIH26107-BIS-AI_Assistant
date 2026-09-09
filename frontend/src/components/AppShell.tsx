import {BookOpen, Bot, CircleHelp, FileCheck2, Home, Languages, Menu, Search, ShieldCheck, X} from 'lucide-react'
import {useState,type ReactNode} from 'react'
import {NavLink} from 'react-router-dom'
import type {Language} from '../lib/types'
import {t} from '../lib/i18n'
import GoogleAuth from './GoogleAuth'

export function Brand(){return <div className="brand"><img className="bis-logo" src="/assets/bis-logo-strip.png" alt="Bureau of Indian Standards"/><div className="product-name"><strong>BIS ManakSathi <em>AI</em></strong><small>Independent standards assistant</small></div></div>}
export default function AppShell({children,language,setLanguage}:{children:ReactNode;language:Language;setLanguage:(x:Language)=>void}){
 const [open,setOpen]=useState(()=>{const saved=localStorage.getItem('manaksathi-navigation-open');return saved===null?window.innerWidth>720:saved==='true'}); const links=[['/',Home,'home'],['/assistant',Bot,'assistant'],['/standards',Search,'standards'],['/verify',ShieldCheck,'verify'],['/guide',FileCheck2,'guide'],['/consumer',CircleHelp,'consumerHelp']] as const
 const toggleNavigation=()=>setOpen(value=>{const next=!value;localStorage.setItem('manaksathi-navigation-open',String(next));return next})
 const closeMobileNavigation=()=>{if(window.innerWidth<=720){setOpen(false);localStorage.setItem('manaksathi-navigation-open','false')}}
 return <div className={`shell ${open?'nav-open':'nav-closed'}`}><header className="topbar"><button className="icon-button mobile-menu" type="button" onClick={toggleNavigation} title={open?'Hide navigation sidebar':'Show navigation sidebar'} aria-label={open?'Close navigation':'Open navigation'} aria-expanded={open} aria-controls="main-sidebar">{open?<X/>:<Menu/>}</button><Brand/><div className="top-actions"><span className="demo-pill"><span/> {t(language,'demo')}</span><label className="language"><Languages size={16}/><span className="sr-only">Language</span><select value={language} onChange={e=>setLanguage(e.target.value as Language)}><option value="en">English</option><option value="hi">हिन्दी</option></select></label><GoogleAuth/></div></header>
 {open&&<button className="nav-backdrop" aria-label="Close navigation" onClick={closeMobileNavigation}/>}<aside id="main-sidebar" className={`sidebar ${open?'open':''}`}><nav aria-label="Main navigation">{links.map(([path,Icon,key])=><NavLink key={path} to={path} end={path==='/'} onClick={closeMobileNavigation}><Icon/><span>{t(language,key)}</span></NavLink>)}</nav><div className="sidebar-foot"><BookOpen/><p><strong>Evidence first</strong><br/>Every answer shows its source.</p></div></aside><main>{children}</main></div>
}
