import {
  ArrowUp,
  BookOpen,
  Camera,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  GripVertical,
  FileText,
  Image as ImageIcon,
  LoaderCircle,
  LogIn,
  Mic,
  MicOff,
  MapPin,
  Plus,
  MessageSquarePlus,
  Pin,
  ShieldAlert,
  Sparkles,
  Square,
  Trash2,
  Volume2,
} from "lucide-react";
import { motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import CitationCard from "../components/CitationCard";
import { api } from "../lib/api";
import { t } from "../lib/i18n";
import type { Language, Message, Session } from "../lib/types";
const openLogin = () =>
  window.dispatchEvent(new CustomEvent("manaksetu-open-auth"));
interface SpeechResultLike {isFinal:boolean;0:{transcript:string}}
interface SpeechRecognitionLike {lang:string;interimResults:boolean;continuous:boolean;start:()=>void;stop:()=>void;onresult:((event:{results:ArrayLike<SpeechResultLike>})=>void)|null;onend:(()=>void)|null;onerror:(()=>void)|null}
type SpeechRecognitionConstructor=new()=>SpeechRecognitionLike;
export default function Assistant({
  language,
  audience,
}: {
  language: Language;
  audience: string;
}) {
  const [session, setSession] = useState<Session | null>(null),
    [history, setHistory] = useState<Session[]>([]),
    [messages, setMessages] = useState<Message[]>([]),
    [value, setValue] = useState(""),
    [loading, setLoading] = useState(false),
    [sources, setSources] = useState<Message | null>(null),
    [historyMenu, setHistoryMenu] = useState<{id:string;x:number;y:number} | null>(null),
    [historyOpen, setHistoryOpen] = useState(()=>localStorage.getItem("manaksetu-history-open")!=="false"),
    [historyWidth, setHistoryWidth] = useState(()=>Math.min(420,Math.max(180,Number(localStorage.getItem("manaksetu-history-width"))||220))),
    [historyNotice, setHistoryNotice] = useState(""),
    [listening,setListening]=useState(false),
    [speakingId,setSpeakingId]=useState<number|null>(null),
    [voiceNotice,setVoiceNotice]=useState(""),
    [attachOpen,setAttachOpen]=useState(false),
    [dropActive,setDropActive]=useState(false),
    [locating,setLocating]=useState(false),
    [authenticated, setAuthenticated] = useState(
      Boolean(localStorage.getItem("manaksetu-token")),
    ),
    [guestUsed, setGuestUsed] = useState(() =>
      Number(localStorage.getItem("manaksetu-guest-prompts") || 0),
    );
  const end = useRef<HTMLDivElement>(null);
  const recognitionRef=useRef<SpeechRecognitionLike|null>(null);
  const requestControllerRef=useRef<AbortController|null>(null);
  const imageInputRef=useRef<HTMLInputElement>(null),cameraInputRef=useRef<HTMLInputElement>(null),fileInputRef=useRef<HTMLInputElement>(null);
  const workspaceRef=useRef<HTMLDivElement>(null),resizeStart=useRef({x:0,width:220,last:220,moved:false});
  const loadHistory = useCallback(async () => {
      if (!localStorage.getItem("manaksetu-token")) {
        setHistory([]);
        return;
      }
      try {
        setHistory(await api.sessions());
      } catch {
        setHistory([]);
      }
    }, []),
    newChat = useCallback(async () => {
      const created = await api.createSession(audience, language);
      setSession(created);
      setMessages([]);
    }, [audience, language]);
  useEffect(() => {
    void newChat().catch(() => {});
    void loadHistory();
  }, [newChat, loadHistory]);
  useEffect(() => {
    const changed = () => {
      setAuthenticated(Boolean(localStorage.getItem("manaksetu-token")));
      void loadHistory();
    };
    window.addEventListener("manaksetu-auth-changed", changed);
    return () => {
      window.removeEventListener("manaksetu-auth-changed", changed);
    };
  }, [loadHistory]);
  useEffect(() => {
    if (end.current) {
      end.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);
  useEffect(()=>{
    if(!historyMenu)return;
    const dismiss=(event:PointerEvent)=>{
      const target=event.target;
      if(!(target instanceof Element)){setHistoryMenu(null);return;}
      if(target.closest(".history-delete"))return;
      const row=target.closest<HTMLElement>(".history-entry");
      if(row?.dataset.sessionId===historyMenu.id)return;
      setHistoryMenu(null);
    };
    document.addEventListener("pointermove",dismiss);
    return ()=>document.removeEventListener("pointermove",dismiss);
  },[historyMenu]);
  useEffect(()=>{
    if(!historyNotice)return;
    const timer=window.setTimeout(()=>setHistoryNotice(""),2200);
    return ()=>window.clearTimeout(timer);
  },[historyNotice]);
  const prompts =
      language === "hi"
        ? [
            "इलेक्ट्रिक केतली के लिए कौन सा मानक है?",
            "ISI प्रमाणन के लिए कौन से दस्तावेज़ चाहिए?",
            "टूथपेस्ट का भारतीय मानक बताएं",
          ]
        : [
            "Which standard applies to an electric kettle?",
            "What documents are needed for ISI certification?",
            "Which Indian Standard covers toothpaste?",
          ],
    guestLocked = !authenticated && guestUsed >= 6;
  async function openSession(item: Session) {
    const full = await api.session(item.public_id);
    setSession(full);
    setMessages(full.messages);
  }
  async function removeSession(event: React.MouseEvent, id: string) {
    event.stopPropagation();
    await api.deleteSession(id);
    setHistoryMenu(null);
    setHistory((items) => items.filter((x) => x.public_id !== id));
    if (session?.public_id === id) newChat();
  }
  async function togglePin(event: React.MouseEvent, item: Session) {
    event.stopPropagation();
    const next=!item.is_pinned;
    setHistory(items=>items.map(entry=>entry.public_id===item.public_id?{...entry,is_pinned:next}:entry));
    setHistoryNotice(next?"Conversation pinned":"Conversation unpinned");
    try {
      const updated=await api.pinSession(item.public_id,next);
      if(session?.public_id===updated.public_id)setSession(current=>current?{...current,is_pinned:updated.is_pinned}:current);
    } catch {
      setHistory(items=>items.map(entry=>entry.public_id===item.public_id?{...entry,is_pinned:item.is_pinned}:entry));
      setHistoryNotice("Could not update pin. Please sign in again.");
    }
  }
  async function send(text = value, showUser = true) {
    if (!text.trim() || loading) return;
    if (guestLocked) {
      openLogin();
      return;
    }
    setValue("");
    if(showUser)setMessages((items) => [
      ...items,
      {
        id: Date.now(),
        role: "user",
        content: text,
        intent: "",
        confidence: null,
        abstained: false,
        citations: [],
        next_steps: [],
        created_at: new Date().toISOString(),
      },
    ]);
    setLoading(true);
    const controller=new AbortController();
    requestControllerRef.current=controller;
    try {
      const active = session || (await api.createSession(audience, language));
      if (!session) setSession(active);
      const answer = await api.sendMessage(active.public_id, text, language, !showUser, controller.signal);
      setMessages((items) => [...items, answer]);
      if (authenticated) {
        void loadHistory();
      } else {
        const next = guestUsed + 1;
        setGuestUsed(next);
        localStorage.setItem("manaksetu-guest-prompts", String(next));
      }
    } catch (error) {
      if(error instanceof DOMException&&error.name==="AbortError")return;
      const message =
        error instanceof Error
          ? error.message
          : "Unable to reach the assistant.";
      if (message.toLowerCase().includes("sign in")) openLogin();
      setMessages((items) => [
        ...items,
        {
          id: Date.now(),
          role: "assistant",
          content: message,
          intent: "error",
          confidence: 0,
          abstained: true,
          citations: [],
          next_steps: [],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      requestControllerRef.current=null;
      setLoading(false);
    }
  }
  function askAboutRoadmapStage(step:string,index:number,total:number){
    const productContext=[...messages].reverse().find(item=>item.role==="user"&&!item.content.includes("ROADMAP_STAGE"))?.content;
    const marker=`ROADMAP_STAGE ${String(index+1).padStart(2,"0")} OF ${String(total).padStart(2,"0")}\nSTAGE_TITLE: ${step}`;
    const prompt=productContext ? `${marker}\nPRODUCT_CONTEXT: ${productContext}\nExplain only this selected stage with clear actions, documents, checks and expected outcome using available evidence.` : `${marker}\nExplain only this selected stage with clear actions, documents, checks and expected outcome.`;
    void send(prompt);
  }
  function askRecommendedStep(step:string){
    const context=[...messages].reverse().find(item=>item.role==="user"&&!item.content.includes("ROADMAP_STAGE"))?.content;
    void send(context?`Regarding my earlier question: "${context}", continue with this next action: ${step}`:step);
  }
  function toggleVoiceInput(){
    if(listening){recognitionRef.current?.stop();return;}
    const speechWindow=window as unknown as {SpeechRecognition?:SpeechRecognitionConstructor;webkitSpeechRecognition?:SpeechRecognitionConstructor};
    const Recognition=speechWindow.SpeechRecognition||speechWindow.webkitSpeechRecognition;
    if(!Recognition){setVoiceNotice("Voice input is not supported in this browser. Try Chrome or Edge.");return;}
    const recognition=new Recognition();
    recognition.lang=language==="hi"?"hi-IN":"en-IN";
    recognition.interimResults=true;recognition.continuous=false;
    recognition.onresult=(event)=>{let transcript="",final=false;for(let index=0;index<event.results.length;index++){transcript+=event.results[index][0].transcript;final=final||event.results[index].isFinal}setValue(transcript);if(final&&transcript.trim())void send(transcript.trim())};
    recognition.onend=()=>setListening(false);
    recognition.onerror=()=>{setListening(false);setVoiceNotice("Could not hear clearly. Please try the mic again.")};
    recognitionRef.current=recognition;setVoiceNotice("");setListening(true);recognition.start();
  }
  function speakAnswer(message:Message){
    if(!("speechSynthesis" in window)){setVoiceNotice("Text-to-speech is not supported in this browser.");return;}
    window.speechSynthesis.cancel();
    if(speakingId===message.id){setSpeakingId(null);return;}
    const utterance=new SpeechSynthesisUtterance(message.content.replace(/[*#•]/g," "));
    utterance.lang=language==="hi"?"hi-IN":"en-IN";utterance.rate=.95;
    utterance.onend=()=>setSpeakingId(null);utterance.onerror=()=>setSpeakingId(null);
    setSpeakingId(message.id);window.speechSynthesis.speak(utterance);
  }
  async function handleFile(file:File){
    setAttachOpen(false);setDropActive(false);
    if(file.type.startsWith("image/")){
      if(file.size>5*1024*1024){setVoiceNotice("Image must be 5 MB or smaller.");return;}
      setLoading(true);
      setMessages(items=>[...items,{id:Date.now(),role:"user",content:`📷 Product photo: ${file.name}`,intent:"",confidence:null,abstained:false,citations:[],next_steps:[],created_at:new Date().toISOString()}]);
      try{const active=session||(await api.createSession(audience,language));if(!session)setSession(active);const answer=await api.analyzeImage(active.public_id,file,language);setMessages(items=>[...items,answer]);if(authenticated)void loadHistory();}
      catch(error){setMessages(items=>[...items,{id:Date.now(),role:"assistant",content:error instanceof Error?error.message:"Image analysis failed.",intent:"error",confidence:0,abstained:true,citations:[],next_steps:[],created_at:new Date().toISOString()}]);}
      finally{setLoading(false)}return;
    }
    const allowed=["text/plain","text/markdown","text/csv","application/json"];
    if(!allowed.includes(file.type)&&!(/\.(txt|md|csv|json)$/i.test(file.name))){setVoiceNotice("Drop a JPEG, PNG, WebP, TXT, Markdown, CSV, or JSON file.");return;}
    if(file.size>1024*1024){setVoiceNotice("Text file must be 1 MB or smaller.");return;}
    const content=(await file.text()).slice(0,4000);if(content.trim())void send(`Analyze this uploaded text (${file.name}):\n${content}`);
  }
  function recommendFromCurrentLocation(){
    if(!navigator.geolocation){setVoiceNotice("Current location is not supported. Please type your city or PIN code.");return;}
    setLocating(true);setVoiceNotice("");
    navigator.geolocation.getCurrentPosition(async position=>{
      let place=`coordinates ${position.coords.latitude.toFixed(5)}, ${position.coords.longitude.toFixed(5)}`;
      try{const response=await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${position.coords.latitude}&lon=${position.coords.longitude}`);if(response.ok){const data=await response.json() as {address?:{city?:string;town?:string;village?:string;state?:string;postcode?:string}};const address=data.address;place=[address?.city||address?.town||address?.village,address?.state,address?.postcode].filter(Boolean).join(", ")||place;}}
      catch{ /* coordinates remain available */ }
      const roadmapMessage=[...messages].reverse().find(item=>item.intent==="manufacturing_roadmap");
      const originalQuestion=[...messages].reverse().find(item=>item.role==="user"&&!item.content.includes("ROADMAP_STAGE")&&!item.content.toLowerCase().includes("nearby lab"));
      const standard=roadmapMessage?.citations[0]?.standard_number;
      const productContext=originalQuestion?.content;
      const context=[productContext&&`Product context: ${productContext}`,standard&&`Standard: ${standard}`].filter(Boolean).join("\n");
      setLocating(false);void send(`Recommend a nearby BIS-recognized testing laboratory near ${place}.${context?`\n${context}`:""}\nReturn laboratory locations, and require verification that each laboratory's current recognized scope covers the exact standard.`,false);
    },()=>{setLocating(false);setVoiceNotice("Location permission was denied. Type your city or 6-digit PIN to find a lab.")},{enableHighAccuracy:false,timeout:10000,maximumAge:300000});
  }
  const historyItem=(item:Session)=><div className="history-entry" data-session-id={item.public_id} key={item.public_id} onContextMenu={(event)=>{event.preventDefault();event.stopPropagation();setHistoryMenu({id:item.public_id,x:Math.min(event.clientX,window.innerWidth-190),y:Math.min(event.clientY,window.innerHeight-55)})}}>
    <button className={session?.public_id === item.public_id ? "active" : ""} onClick={() => openSession(item)}><span>{item.title}</span></button>
    <button className={`history-pin ${item.is_pinned?'is-pinned':''}`} aria-label={item.is_pinned?'Unpin conversation':'Pin conversation'} onClick={(event)=>void togglePin(event,item)}><Pin/></button>
  </div>;
  function resizeHistory(event:React.PointerEvent<HTMLElement>){
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeStart.current={x:event.clientX,width:historyWidth,last:historyWidth,moved:false};
  }
  function moveHistoryResize(event:React.PointerEvent<HTMLElement>){
    if(!event.currentTarget.hasPointerCapture(event.pointerId))return;
    const delta=event.clientX-resizeStart.current.x;
    if(Math.abs(delta)>3)resizeStart.current.moved=true;
    const next=Math.min(420,Math.max(180,resizeStart.current.width+delta));
    resizeStart.current.last=next;
    setHistoryWidth(next);
  }
  function finishHistoryResize(event:React.PointerEvent<HTMLElement>){
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId);
    localStorage.setItem("manaksetu-history-width",String(Math.round(resizeStart.current.last)));
  }
  return (
    <div ref={workspaceRef} style={{"--history-width":`${historyWidth}px`} as CSSProperties} className={`workspace ${historyOpen?'history-open':'history-closed'}`}>
      <aside className="conversation-list" onClick={() => setHistoryMenu(null)}>
        <button className="new-chat" onClick={() => newChat()}>
          <MessageSquarePlus /> New conversation
        </button>
        <div className="history-heading"><span className="eyebrow">{authenticated ? "Your history" : "Guest session"}</span>{authenticated&&history.length>0&&<small>{history.length} saved</small>}</div>
        <div className="history-list">
          {history.some(item=>item.is_pinned)&&<div className="history-group-label"><Pin/> Pinned</div>}
          {history.filter(item=>item.is_pinned).map(historyItem)}
          {history.some(item=>item.is_pinned)&&history.some(item=>!item.is_pinned)&&<div className="history-group-label">Recent</div>}
          {history.filter(item=>!item.is_pinned).map(historyItem)}
          {authenticated && !history.length && (
            <p>No saved conversations yet.</p>
          )}
          {historyNotice&&<p className="history-notice" role="status">{historyNotice}</p>}
        </div>
        {!authenticated && (
          <div className="guest-meter">
            <div>
              <span style={{ width: `${(guestUsed / 6) * 100}%` }} />
            </div>
            <strong>{Math.max(0, 6 - guestUsed)} free questions left</strong>
            <button onClick={openLogin}>Sign in for unlimited chat</button>
          </div>
        )}
        <div className="privacy-note">
          <ShieldAlert />
          <p>Independent demo. Avoid entering personal information.</p>
        </div>
      </aside>
      {historyMenu&&<button className="history-delete" style={{left:historyMenu.x,top:historyMenu.y}} role="menuitem" onClick={(event)=>removeSession(event,historyMenu.id)} onMouseDown={(event)=>event.stopPropagation()}><Trash2/> Delete conversation</button>}
      {historyOpen&&<div className="history-resize-rail" role="separator" aria-label="Resize chat history" aria-orientation="vertical" onPointerDown={resizeHistory} onPointerMove={moveHistoryResize} onPointerUp={finishHistoryResize}/>}
      <button className="history-toggle" type="button" aria-label={historyOpen?"Hide chat history":"Show chat history"} title={historyOpen?"Hide history":"Show history"} onClick={()=>setHistoryOpen(current=>{const next=!current;localStorage.setItem("manaksetu-history-open",String(next));return next})}>{historyOpen?<><GripVertical/><ChevronLeft/></>:<ChevronRight/>}</button>
      <section className={`chat-panel ${dropActive?"drop-active":""}`} onDragEnter={(event)=>{event.preventDefault();setDropActive(true)}} onDragOver={(event)=>event.preventDefault()} onDragLeave={(event)=>{if(!event.currentTarget.contains(event.relatedTarget as Node))setDropActive(false)}} onDrop={(event)=>{event.preventDefault();const file=event.dataTransfer.files[0];if(file)void handleFile(file)}}>
        {dropActive&&<div className="drop-overlay"><Plus/><strong>Drop image or text file</strong><span>Product images will be identified and matched with standards.</span></div>}
        <header className="panel-header">
          <div>
            <span className="status-dot" /> BIS ManakSathi assistant
          </div>
          <span>
            {authenticated ? "History enabled" : "Guest · 6 question limit"}
          </span>
        </header>
        <div className="thread">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <div className="assistant-orb">
                <Sparkles />
              </div>
              <span className="kicker">Ask with confidence</span>
              <h1>What would you like to understand?</h1>
              <p>
                I’ll search the available standards and show exactly what
                supports the answer.
              </p>
              <div className="prompt-grid">
                {prompts.map((prompt) => (
                  <button key={prompt} onClick={() => send(prompt)}>
                    {prompt}
                    <ChevronRight />
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((message) => (
            <motion.article
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`message ${message.role}`}
              key={message.id}
            >
              <div className="message-role">
                {message.role === "user" ? "You" : "म · AI"}
              </div>
              <div className="message-body">
                <p>{message.content.split(/(https?:\/\/[^\s]+)/g).map((part,index)=>part.startsWith("http")?<a className="answer-link" href={part} target="_blank" rel="noreferrer" key={`${part}-${index}`}>{part}</a>:part)}</p>
                {message.lab_results&&message.lab_results.length>0&&<section className="lab-results"><header><div><span className="eyebrow">Location-based results</span><h3>Nearby laboratory candidates</h3></div><span>{message.lab_results.length} found</span></header><div className="lab-grid">{message.lab_results.map((lab,index)=><article className="lab-card" key={lab.name}><div className="lab-rank">{String(index+1).padStart(2,"0")}</div><h4>{lab.name}</h4><p><MapPin/> {lab.location}</p><div className="lab-status"><span>{lab.status}</span><span>{lab.scope_status}</span></div><small>Listing validity: {lab.valid_until}</small><a href={lab.url} target="_blank" rel="noreferrer">Verify current scope in BIS LIMS <ChevronRight/></a></article>)}</div><footer>Distance is indicative. Confirm that the laboratory’s current scope includes the exact IS number before submitting samples.</footer></section>}
                {message.role === "assistant" && message.intent !== "error" && (
                  <><div className="answer-meta">
                    <span>{message.intent.replaceAll("_", " ")}</span>
                    {message.confidence !== null && (
                      <span>
                        {Math.round(message.confidence * 100)}% evidence match
                      </span>
                    )}
                    {message.citations.length > 0 && (
                      <button onClick={() => setSources(message)}>
                        <BookOpen /> {message.citations.length}{" "}
                        {t(language, "sources")}
                      </button>
                    )}
                    <button type="button" className="speak-answer" onClick={()=>speakAnswer(message)} aria-label={speakingId===message.id?"Stop speaking":"Read answer aloud"}><Volume2/> {speakingId===message.id?"Stop":"Listen"}</button>
                  </div>{message.next_steps.length>0&&(message.intent==="manufacturing_roadmap"?<section className="roadmap-card" aria-label="Manufacturing roadmap"><header><div><span className="eyebrow">Action plan</span><h3>{language==="hi"?"आपका manufacturing roadmap":"Your manufacturing roadmap"}</h3></div><span className="roadmap-count">{message.next_steps.length} stages</span></header><ol>{message.next_steps.map((step,index)=><li key={`${step}-${index}`}><span className="roadmap-number">{String(index+1).padStart(2,"0")}</span><button type="button" disabled={loading||guestLocked} onClick={()=>askAboutRoadmapStage(step,index,message.next_steps.length)}><strong>{step}</strong><small>{language==="hi"?"क्लिक करें — सवाल तुरंत भेजा जाएगा":"Click to ask the assistant about this stage"}</small></button><ChevronRight/></li>)}</ol><footer>Planning guidance · Confirm certification applicability with an official BIS channel.</footer></section>:message.intent==="roadmap_stage_detail"?<div className="stage-next"><span>Next step</span>{message.next_steps.map((step,index)=>{const match=step.match(/^(\d+)\.\s*(.*)$/);const number=match?Number(match[1]):index+1;const title=match?.[2]||step;return <button type="button" key={`${step}-${index}`} disabled={loading||guestLocked} onClick={()=>askAboutRoadmapStage(title,number-1,7)}><strong>{String(number).padStart(2,"0")} · {title}</strong><small>Click to continue</small><ChevronRight/></button>})}</div>:<div className="next-steps"><strong>Recommended next steps</strong>{message.next_steps.map((step,index)=><button type="button" disabled={loading||guestLocked} key={`${step}-${index}`} onClick={()=>askRecommendedStep(step)}><span>{index+1}. {step}</span><ChevronRight/></button>)}</div>)}{message.intent==="roadmap_stage_detail"&&message.next_steps.length===0&&<div className="roadmap-complete"><CheckCircle2/><div><strong>Roadmap complete</strong><small>All 7 planning stages have been covered.</small><button type="button" disabled={locating||loading||guestLocked} onClick={recommendFromCurrentLocation}><MapPin/>{locating?"Detecting location…":"Find a recognized lab near me"}</button></div></div>}</>
                )}
              </div>
            </motion.article>
          ))}
          {loading && (
            <div className="retrieving" role="status">
              <LoaderCircle className="spin" />
              <div>
                <strong>{t(language, "thinking")}</strong>
                <span>Matching identifiers, scope and source metadata</span>
              </div>
            </div>
          )}
          {guestLocked && (
            <div className="login-wall">
              <LogIn />
              <div>
                <strong>Continue your standards journey</strong>
                <p>
                  You’ve used six guest questions. Sign in to keep chatting and
                  save history.
                </p>
              </div>
              <button onClick={openLogin}>Sign in with Google</button>
            </div>
          )}
          <div ref={end} />
        </div>
        <form
          className={`composer ${guestLocked ? "locked" : ""}`}
          onSubmit={(event) => {
            event.preventDefault();
            send();
          }}
        >
          <input ref={imageInputRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event)=>{const file=event.target.files?.[0];if(file)void handleFile(file);event.currentTarget.value=""}}/>
          <input ref={cameraInputRef} className="sr-only" type="file" accept="image/*" capture="environment" onChange={(event)=>{const file=event.target.files?.[0];if(file)void handleFile(file);event.currentTarget.value=""}}/>
          <input ref={fileInputRef} className="sr-only" type="file" accept=".txt,.md,.csv,.json,text/plain,text/markdown,text/csv,application/json" onChange={(event)=>{const file=event.target.files?.[0];if(file)void handleFile(file);event.currentTarget.value=""}}/>
          <div className="attach-control"><button type="button" className="attach-button" onClick={()=>setAttachOpen(open=>!open)} aria-label="Add image or file" aria-expanded={attachOpen}><Plus/></button>{attachOpen&&<div className="attach-menu"><button type="button" onClick={()=>imageInputRef.current?.click()}><ImageIcon/> Choose image</button><button type="button" onClick={()=>cameraInputRef.current?.click()}><Camera/> Open camera</button><button type="button" onClick={()=>fileInputRef.current?.click()}><FileText/> Upload text file</button><small>You can also drag and drop into the chat.</small></div>}</div>
          <textarea
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onFocus={() => {
              if (guestLocked) openLogin();
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder={
              guestLocked
                ? "Sign in to ask more questions"
                : t(language, "prompt")
            }
            aria-label={t(language, "prompt")}
            readOnly={guestLocked}
          />
          <button type="button" className={`voice-button ${listening?"listening":""}`} onClick={toggleVoiceInput} disabled={loading||guestLocked} aria-label={listening?"Stop listening":"Ask by voice"}>{listening?<MicOff/>:<Mic/>}</button>
          <button type={loading?"button":"submit"} className={loading?"stop-button":""} disabled={(!loading&&!value.trim())||guestLocked} onClick={loading?()=>requestControllerRef.current?.abort():undefined} aria-label={loading?"Stop generating":"Send message"}>
            {loading?<Square/>:<ArrowUp/>}
          </button>
          <small>
            {voiceNotice&&<span className="voice-notice">{voiceNotice} </span>}Answers are limited to available evidence.{" "}
            {t(language, "officialNotice")}
          </small>
        </form>
      </section>
      {sources && (
        <div className="drawer-backdrop" onClick={() => setSources(null)}>
          <motion.aside
            className="source-drawer"
            initial={{ x: 40, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <header>
              <div>
                <span className="eyebrow">Evidence trail</span>
                <h2>{t(language, "sources")}</h2>
              </div>
              <button className="icon-button" onClick={() => setSources(null)}>
                ×
              </button>
            </header>
            {sources.citations.map((citation) => (
              <CitationCard key={citation.id} citation={citation} />
            ))}
          </motion.aside>
        </div>
      )}
    </div>
  );
}
