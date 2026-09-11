import React, {useMemo, useState} from "react";
import { createRoot } from "react-dom/client";
import { ShieldCheck, PhoneCall, FileCheck2, Star, ChevronRight, CheckCircle2, HelpCircle, XCircle } from "lucide-react";
import "./styles.css";

const scenarios = {
  verified: {
    label: "Cooperative recipient",
    result: "VERIFIED SUCCESS",
    evidence: [
      ["Appointment moved", "Yes, your appointment is rescheduled to Friday afternoon."],
      ["No additional charge", "There is no additional charge."]
    ]
  },
  partial: {
    label: "Charge not confirmed",
    result: "PARTIAL",
    evidence: [
      ["Appointment moved", "Your appointment is rescheduled to Friday afternoon."],
      ["No additional charge", null]
    ]
  },
  unknown: {
    label: "Voicemail / insufficient evidence",
    result: "UNKNOWN",
    evidence: [["Appointment moved", null], ["No additional charge", null]]
  },
  failed: {
    label: "Recipient insists on a fee",
    result: "FAILED",
    evidence: [
      ["Appointment moved", "Friday afternoon is available."],
      ["No additional charge", "There will be a £25 rescheduling charge."]
    ]
  }
}

function Badge({children, kind=""}) { return <span className={`badge ${kind}`}>{children}</span>; }

function App() {
  const [step, setStep] = useState(0);
  const [consent, setConsent] = useState(false);
  const [scenario, setScenario] = useState("verified");
  const [rating, setRating] = useState(0);
  const s = scenarios[scenario];
  const stateClass = s.result.toLowerCase().replace(" ","-");

  return <div className="shell">
    <header>
      <div className="brand"><ShieldCheck size={22}/> Future Call AI</div>
      <Badge kind="muted">NOT CONFIGURED</Badge>
    </header>

    <div className="steps">
      {["Request","Contract","Guardian","Call","Result"].map((x,i)=>
        <div className={`step ${i===step?"active":i<step?"done":""}`} key={x}>
          <span>{i+1}</span>{x}
        </div>
      )}
    </div>

    <main>
      {step===0 && <>
        <p className="eyebrow">TRUSTED TASK COMPLETION</p>
        <h1>Say what you need.<br/>We prove what happened.</h1>
        <p className="lede">Future Call AI turns a phone task into a controlled goal, protects your permissions, and only marks success when the evidence supports it.</p>
        <label>Your request</label>
        <textarea defaultValue="Move my appointment to Friday afternoon, but only if there is no additional charge."/>
        <button onClick={()=>setStep(1)}>Compile Goal Contract <ChevronRight size={18}/></button>
      </>}

      {step===1 && <>
        <p className="eyebrow">GOAL CONTRACT</p>
        <h2>Review what success means</h2>
        <div className="grid">
          <Card title="Goal" value="Reschedule appointment"/>
          <Card title="Preferred outcome" value="Friday afternoon"/>
          <Card title="Hard constraint" value="No additional charge"/>
          <Card title="Permitted data" value="Name · Booking reference"/>
          <Card title="Forbidden" value="Payment details · Paid alternative"/>
          <Card title="Success conditions" value="A. Friday afternoon confirmed · B. No additional charge confirmed"/>
        </div>
        <button onClick={()=>setStep(2)}>Continue to Guardian <ChevronRight size={18}/></button>
      </>}

      {step===2 && <>
        <p className="eyebrow">GUARDIAN</p>
        <h2>You stay in control</h2>
        <div className="guardian">
          <ShieldCheck size={30}/>
          <div><b>Recipient:</b> Test Clinic<br/><b>Purpose:</b> Reschedule appointment<br/><b>May share:</b> Name + booking reference<br/><b>Must not share:</b> Payment details<br/><b>Hard constraint:</b> No additional charge</div>
        </div>
        <label className="toggle"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/> I explicitly authorize this task.</label>
        <label>Execution mode</label>
        <select value={scenario} onChange={e=>setScenario(e.target.value)}>
          {Object.entries(scenarios).map(([k,v])=><option value={k} key={k}>{v.label}</option>)}
        </select>
        <div className="notice">SIMULATED — live Twilio is not configured in this package.</div>
        <button disabled={!consent} onClick={()=>setStep(3)}>Authorize simulated call <PhoneCall size={18}/></button>
      </>}

      {step===3 && <>
        <p className="eyebrow">CALL</p>
        <h2>Simulation complete</h2>
        <div className="timeline">
          <div>CREATED</div><div>ANSWERED</div><div>COMPLETED</div>
        </div>
        <p className="notice">Provider status is transport-only. It does not determine goal success.</p>
        <button onClick={()=>setStep(4)}>Check evidence <FileCheck2 size={18}/></button>
      </>}

      {step===4 && <>
        <p className="eyebrow">EVIDENCE & VERIFY</p>
        <h2>What actually happened?</h2>
        <div className={`verdict ${stateClass}`}>
          {s.result==="VERIFIED SUCCESS"?<CheckCircle2/>:s.result==="FAILED"?<XCircle/>:<HelpCircle/>}
          <strong>{s.result}</strong>
          <Badge>SIMULATED</Badge>
        </div>
        {s.evidence.map(([title,ev],i)=>
          <div className="evidence" key={i}>
            <div className="e-title">{ev?"✓":"?"} {title}</div>
            <div className="quote">{ev?`“${ev}”`:"No explicit supporting evidence found."}</div>
          </div>
        )}
        <div className="principle">CALL COMPLETED ≠ TASK COMPLETED</div>
        <div className="rating">
          <p>How was your experience?</p>
          {[1,2,3,4,5].map(n=><Star key={n} onClick={()=>setRating(n)} fill={n<=rating?"currentColor":"none"} />)}
        </div>
        <button className="secondary" onClick={()=>{setStep(0);setConsent(false);setRating(0)}}>Start a new request</button>
      </>}
    </main>
  </div>
}
function Card({title,value}) { return <div className="card"><span>{title}</span><b>{value}</b></div> }
createRoot(document.getElementById("root")).render(<App/>)
