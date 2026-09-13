import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { ShieldCheck, PhoneCall, FileCheck2, Star, ChevronRight, CheckCircle2, HelpCircle, XCircle } from "lucide-react";
import "./styles.css";

const API=(import.meta.env.VITE_API_URL||"").replace(/\/$/,"");
const ACTIVE_JOB_KEY="earendel.activeCallJob";
const CONTRACT={goal:"Reschedule appointment",preferred:"Friday afternoon",hard_constraints:["No additional charge"],allowed_data:["name","booking reference"],forbidden_actions:["accept paid alternative","share payment details"],success_requirements:[{id:"appointment",text:"Appointment moved to Friday afternoon",evidence_keywords:["friday"]},{id:"fee",text:"No additional charge",evidence_keywords:["no additional charge"]}]};
const simulationScenarios={verified:{label:"Cooperative recipient",result:"VERIFIED_SUCCESS",evidence:[["Appointment moved","Yes, your appointment is rescheduled to Friday afternoon."],["No additional charge","There is no additional charge."]]},partial:{label:"Charge not confirmed",result:"PARTIAL",evidence:[["Appointment moved","Your appointment is rescheduled to Friday afternoon."],["No additional charge",null]]},unknown:{label:"Voicemail / insufficient evidence",result:"UNKNOWN",evidence:[["Appointment moved",null],["No additional charge",null]]},failed:{label:"Recipient insists on a fee",result:"FAILED",evidence:[["Appointment moved","Friday afternoon is available."],["No additional charge","There will be a £25 rescheduling charge."]]}};
async function jsonFetch(path,options={}){const response=await fetch(`${API}${path}`,{...options,headers:{"Content-Type":"application/json",...(options.headers||{})}});const body=await response.json().catch(()=>({}));if(!response.ok)throw new Error(body.detail||body.message||`HTTP ${response.status}`);return body;}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function Badge({children,kind=""}){return <span className={`badge ${kind}`}>{children}</span>}
function Card({title,value}){return <div className="card"><span>{title}</span><b>{value}</b></div>}

function App(){
 const [step,setStep]=useState(0),[consent,setConsent]=useState(false),[scenario,setScenario]=useState("verified"),[rating,setRating]=useState(0),[mode,setMode]=useState("simulated"),[phone,setPhone]=useState(""),[routeIndex,setRouteIndex]=useState(0);
 const [request,setRequest]=useState("Move my appointment to Friday afternoon, but only if there is no additional charge.");
 const [customerName,setCustomerName]=useState(""),[bookingReference,setBookingReference]=useState("");
 const [calle,setCalle]=useState({configured:false,mode:"NOT_CONFIGURED"}),[liveResult,setLiveResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[callStatus,setCallStatus]=useState("");
 const [activeJobId,setActiveJobId]=useState(()=>sessionStorage.getItem(ACTIVE_JOB_KEY)||"");
 const runLock=useRef(false);
 const routes=calle.controlled_live_routes||[],sim=simulationScenarios[scenario],route=routes[routeIndex];
 const displayedResult=mode==="live"&&liveResult?{result:liveResult.goal_state,evidence:[["Appointment moved",evidenceText(liveResult,"appointment")],["No additional charge",evidenceText(liveResult,"fee")]]}:sim;
 const stateClass=(displayedResult.result||"unknown").toLowerCase().replaceAll("_","-");
 useEffect(()=>{jsonFetch("/calle/readiness").then(setCalle).catch(()=>setCalle({configured:false,mode:"NOT_CONFIGURED"}))},[]);

 function rememberJob(jobId){sessionStorage.setItem(ACTIVE_JOB_KEY,jobId);setActiveJobId(jobId)}
 function forgetJob(){sessionStorage.removeItem(ACTIVE_JOB_KEY);setActiveJobId("")}
 async function pollLiveJob(jobId){
  setCallStatus(`Resuming CALL-E job ${jobId.slice(0,8)}… No new call will be created.`);
  const deadline=Date.now()+40*60*1000;
  while(Date.now()<deadline){
   const job=await jsonFetch(`/calls/calle/status/${jobId}`);
   setCallStatus(`CALL-E: ${job.status}`);
   if(job.status==="COMPLETED"){forgetJob();setLiveResult(job.result);setStep(4);return}
   if(job.status==="FAILED"){forgetJob();throw new Error(job.error||"CALL-E call failed.")}
   await sleep(3000);
  }
  throw new Error("The existing CALL-E job is still pending. It has been saved; use Resume existing CALL-E job instead of starting another call.");
 }
 async function authorizeAndRun(){
  if(runLock.current||busy)return;
  setError(""); if(!consent)return;
  if(mode==="simulated"){setStep(3);return}
  if(!calle.configured){setError("CALL-E credentials are not connected on the server.");return}
  if(!route){setError("No CALL-E route is enabled for a controlled live trial.");return}
  if(!/^\+[1-9]\d{7,14}$/.test(phone)&&!activeJobId){setError("Enter the destination in E.164 format.");return}
  runLock.current=true;setBusy(true);
  try{
   if(activeJobId){await pollLiveJob(activeJobId);return}
   setCallStatus("Checking Guardian and provider route…");
   const capability=await jsonFetch(`/calle/capability?phone=${encodeURIComponent(phone)}&region=${encodeURIComponent(route.region)}&locale=${encodeURIComponent(route.locale)}`);
   if(!capability.allowed)throw new Error(capability.reason);
   const identity=[customerName.trim()?`Name supplied by user: ${customerName.trim()}`:"",bookingReference.trim()?`Booking reference supplied by user: ${bookingReference.trim()}`:""].filter(Boolean).join(". ");
   const providerIntent=identity?`${request} ${identity}.`:request;
   const created=await jsonFetch("/tasks",{method:"POST",body:JSON.stringify({intent:providerIntent,recipient:"Live recipient",contract:CONTRACT})});
   await jsonFetch("/consent",{method:"POST",body:JSON.stringify({task_id:created.task_id,recipient:"Live recipient",purpose:"Reschedule appointment",allowed_data:CONTRACT.allowed_data,forbidden_actions:CONTRACT.forbidden_actions,constraints:CONTRACT.hard_constraints,approved:true})});
   const started=await jsonFetch("/calls/calle/start",{method:"POST",body:JSON.stringify({task_id:created.task_id,phone,region:route.region,locale:route.locale})});
   rememberJob(started.job_id);
   setCallStatus("CALL-E accepted one Earendel job. Waiting for provider outcome…");
   await pollLiveJob(started.job_id);
  }catch(e){setError(e.message||"Live CALL-E request failed.")}finally{runLock.current=false;setBusy(false)}
 }
 return <div className="shell"><header><div className="brand"><ShieldCheck size={22}/> Future Call AI</div><Badge kind={calle.configured?"ready":"muted"}>{calle.configured?"CALL-E CONNECTED":"NOT CONFIGURED"}</Badge></header>
 <div className="steps">{["Request","Contract","Guardian","Call","Result"].map((x,i)=><div className={`step ${i===step?"active":i<step?"done":""}`} key={x}><span>{i+1}</span>{x}</div>)}</div><main>
 {step===0&&<><p className="eyebrow">TRUSTED TASK COMPLETION</p><h1>Say what you need.<br/>We prove what happened.</h1><p className="lede">Future Call AI turns a phone task into a controlled goal, protects your permissions, and only marks success when the evidence supports it.</p><label>Your request</label><textarea value={request} onChange={e=>setRequest(e.target.value)}/><button onClick={()=>setStep(1)}>Compile Goal Contract <ChevronRight size={18}/></button></>}
 {step===1&&<><p className="eyebrow">GOAL CONTRACT</p><h2>Review what success means</h2><div className="grid"><Card title="Goal" value="Reschedule appointment"/><Card title="Preferred outcome" value="Friday afternoon"/><Card title="Hard constraint" value="No additional charge"/><Card title="Permitted data" value="Name · Booking reference"/><Card title="Forbidden" value="Payment details · Paid alternative"/><Card title="Success conditions" value="A. Friday afternoon · B. No additional charge"/></div><button onClick={()=>setStep(2)}>Continue to Guardian <ChevronRight size={18}/></button></>}
 {step===2&&<><p className="eyebrow">GUARDIAN</p><h2>You stay in control</h2><div className="guardian"><ShieldCheck size={30}/><div><b>Purpose:</b> Reschedule appointment<br/><b>May share:</b> Name + booking reference<br/><b>Must not share:</b> Payment details<br/><b>Hard constraint:</b> No additional charge</div></div><label className="toggle"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>I explicitly authorize this task under the exact Goal Contract.</label><label>Execution mode</label><div className="mode-row"><button className={mode==="simulated"?"mode active-mode":"mode"} onClick={()=>setMode("simulated")}>Simulated</button><button className={mode==="live"?"mode active-mode":"mode"} onClick={()=>setMode("live")}>Real CALL-E</button></div>
 {mode==="simulated"?<><label>Simulated scenario</label><select value={scenario} onChange={e=>setScenario(e.target.value)}>{Object.entries(simulationScenarios).map(([k,v])=><option value={k} key={k}>{v.label}</option>)}</select><div className="notice">SIMULATED — no real phone call is placed and no CALL-E credits are used.</div></>:<><label>Certified recipient route</label><select value={routeIndex} onChange={e=>{setRouteIndex(Number(e.target.value));setError("")}} disabled={!routes.length||!!activeJobId}>{routes.length?routes.map((v,i)=><option value={i} key={`${v.region}-${v.locale}`}>{v.label}</option>):<option>No route enabled</option>}</select><label>Destination phone</label><input className="text-input" value={phone} onChange={e=>setPhone(e.target.value)} placeholder={route?`${route.calling_code}…`:"No route available"} inputMode="tel" disabled={!!activeJobId}/><label>Name (optional; only shared if supplied)</label><input className="text-input" value={customerName} onChange={e=>setCustomerName(e.target.value)} disabled={!!activeJobId}/><label>Booking reference (optional; only shared if supplied)</label><input className="text-input" value={bookingReference} onChange={e=>setBookingReference(e.target.value)} disabled={!!activeJobId}/><div className="notice">LIVE CALL-E consumes credits. One active job at a time. Duplicate provider requests are suppressed; if a job is pending, this screen resumes it instead of creating another call.</div>{activeJobId&&<div className="notice">Existing job saved: {activeJobId.slice(0,8)}… Press Resume; do not start another live task.</div>}</>}
 {callStatus&&<div className="notice">{callStatus}</div>}{error&&<div className="error">{error}</div>}<button disabled={!consent||busy} onClick={authorizeAndRun}>{busy?"Working on existing call…":mode==="live"?(activeJobId?"Resume existing CALL-E job":"Authorize ONE real CALL-E call"):"Authorize simulated call"}<PhoneCall size={18}/></button></>}
 {step===3&&<><p className="eyebrow">CALL</p><h2>Simulation complete</h2><div className="timeline"><div>CREATED</div><div>ANSWERED</div><div>COMPLETED</div></div><p className="notice">Provider status is transport-only. It does not determine goal success.</p><button onClick={()=>setStep(4)}>Check evidence <FileCheck2 size={18}/></button></>}
 {step===4&&<><p className="eyebrow">EVIDENCE & VERIFY</p><h2>What actually happened?</h2><div className={`verdict ${stateClass}`}>{displayedResult.result==="VERIFIED_SUCCESS"?<CheckCircle2/>:displayedResult.result==="FAILED"?<XCircle/>:<HelpCircle/>}<strong>{displayedResult.result}</strong><Badge>{mode==="live"?"LIVE CALL-E":"SIMULATED"}</Badge></div>{displayedResult.evidence.map(([title,ev],i)=><div className="evidence" key={i}><div className="e-title">{ev?"✓":"?"} {title}</div><div className="quote">{ev?`“${ev}”`:"No explicit supporting evidence found."}</div></div>)}{mode==="live"&&liveResult&&<div className="provider-card"><b>Provider state:</b> {String(liveResult.provider_state||"unknown")}<br/><b>Provider task_completed:</b> {String(liveResult.provider_task_completed)}<br/><b>Earendel goal state:</b> {liveResult.goal_state}</div>}<div className="principle">CALL COMPLETED ≠ TASK COMPLETED ≠ VERIFIED SUCCESS</div><div className="rating"><p>How was your experience?</p>{[1,2,3,4,5].map(n=><Star key={n} onClick={()=>setRating(n)} fill={n<=rating?"currentColor":"none"}/>)}</div><button className="secondary" onClick={()=>{setStep(0);setConsent(false);setRating(0);setLiveResult(null);setError("");setCallStatus("")}}>Start a new request</button></>}
 </main></div>
}
function evidenceText(result,key){const source=Array.isArray(result.provider_evidence)?result.provider_evidence:[];const text=source.map(x=>typeof x==="string"?x:JSON.stringify(x)).join(" | ");if((result.verified||[]).includes(key))return text||"CALL-E returned explicit supporting evidence.";if((result.contradicted||[]).includes(key))return text||"CALL-E returned explicit contradicting evidence.";return null}
createRoot(document.getElementById("root")).render(<App/>);
