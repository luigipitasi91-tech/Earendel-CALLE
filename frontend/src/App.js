import { useEffect, useMemo, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster, toast } from "sonner";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  HelpCircle,
  XCircle,
  PhoneCall,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Lock,
  Unlock,
  FileText,
  Ban,
  Info,
} from "lucide-react";
import "@/App.css";
import { api } from "@/lib/api";
import { VERDICT_STYLES } from "@/lib/verdicts";
import { ModeBadge } from "@/components/ModeBadge";
import { Stepper } from "@/components/Stepper";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const DEMO_REQUEST =
  "Move my appointment to Friday afternoon, but only if there is no additional charge.";

const PRESETS = [
  { label: "Reschedule dental appointment (demo)", text: DEMO_REQUEST },
  {
    label: "Cancel gym membership without a cancellation fee",
    text: "Cancel my gym membership, but only if there is no cancellation fee.",
  },
  {
    label: "Confirm hotel late check-in at no extra charge",
    text: "Ask the hotel to hold my room for a late check-in tonight with no additional charge.",
  },
];

function Header({ telephony }) {
  return (
    <header
      className="sticky top-0 z-30 bg-white/85 backdrop-blur border-b border-slate-200"
      data-testid="app-header"
    >
      <div className="mx-auto max-w-2xl px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-slate-900 text-white grid place-items-center">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-bold text-slate-900 tracking-tight">Future Call AI</div>
            <div className="text-[10px] uppercase font-mono tracking-widest text-slate-500">
              Evidence-first calling
            </div>
          </div>
        </div>
        {telephony && (
          <div className="flex items-center gap-2" data-testid="telephony-status">
            <ModeBadge mode={telephony.mode} testId="telephony-mode-badge" />
          </div>
        )}
      </div>
    </header>
  );
}

function RequestScreen({ onSubmit, submitting }) {
  const [text, setText] = useState(DEMO_REQUEST);
  return (
    <section className="space-y-6" data-testid="request-screen">
      <div className="space-y-3">
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 leading-tight">
          Say what you need.
          <br />
          <span className="text-slate-500">We prove what happened.</span>
        </h1>
        <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
          Describe a phone task in plain language. Future Call AI compiles it into a Goal
          Contract, asks for your explicit consent, makes the call, and only marks it
          complete when evidence supports every required condition.
        </p>
      </div>

      <Card className="border-slate-200">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2 text-slate-900">
            <Sparkles className="h-4 w-4 text-slate-500" />
            <CardTitle className="text-lg font-semibold">Your request</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            data-testid="request-textarea"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            className="text-base leading-relaxed resize-none"
            placeholder="e.g. Move my appointment to Friday afternoon, but only if there is no additional charge."
          />
          <div className="space-y-2">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
              Quick presets
            </div>
            <div className="flex flex-col gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p.label}
                  data-testid={`preset-${p.label.slice(0, 12).replace(/\s+/g, "-").toLowerCase()}`}
                  onClick={() => setText(p.text)}
                  className="text-left text-sm px-3 py-2 rounded-md border border-slate-200 hover:border-slate-900 hover:bg-slate-50 transition-colors"
                >
                  <span className="font-medium text-slate-900">{p.label}</span>
                  <div className="text-slate-500 text-xs mt-0.5 line-clamp-1">{p.text}</div>
                </button>
              ))}
            </div>
          </div>
          <Button
            className="w-full h-11 text-base"
            data-testid="compile-contract-btn"
            disabled={submitting || !text.trim()}
            onClick={() => onSubmit(text.trim())}
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Compiling contract…
              </>
            ) : (
              <>
                Compile Goal Contract <ArrowRight className="h-4 w-4 ml-2" />
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </section>
  );
}

function List({ items, testId, emptyLabel = "None" }) {
  if (!items || items.length === 0)
    return <div className="text-sm text-slate-400 italic" data-testid={`${testId}-empty`}>{emptyLabel}</div>;
  return (
    <ul className="space-y-1" data-testid={testId}>
      {items.map((it, i) => (
        <li key={i} className="text-sm text-slate-700 flex gap-2">
          <span className="text-slate-400">•</span>
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}

function ContractScreen({ contract, onBack, onNext }) {
  return (
    <section className="space-y-4" data-testid="contract-screen">
      <div className="space-y-1">
        <div className="text-xs font-mono uppercase tracking-widest text-slate-500">Step 2 · Goal Contract</div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Review the compiled contract</h2>
        <p className="text-sm text-slate-600">
          This is exactly what the agent is authorized to do. Nothing more.
        </p>
      </div>

      <Card className="border-slate-200">
        <CardContent className="p-5 space-y-5">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-1">Goal</div>
            <div className="text-base font-semibold text-slate-900" data-testid="contract-goal">
              {contract.goal || "—"}
            </div>
          </div>
          <Separator />
          <div>
            <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-1">Preferred outcome</div>
            <div className="text-sm text-slate-700" data-testid="contract-preferred">{contract.preferred_outcome || "—"}</div>
          </div>
          <Separator />
          <div>
            <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-2">Hard constraints</div>
            <List items={contract.hard_constraints} testId="contract-hard-constraints" />
          </div>
          <Separator />
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <div className="text-[11px] font-mono uppercase tracking-widest text-emerald-700 mb-2">Permitted data</div>
              <List items={contract.permitted_data} testId="contract-permitted-data" />
            </div>
            <div>
              <div className="text-[11px] font-mono uppercase tracking-widest text-rose-700 mb-2">Forbidden data</div>
              <List items={contract.forbidden_data} testId="contract-forbidden-data" />
            </div>
          </div>
          <div>
            <div className="text-[11px] font-mono uppercase tracking-widest text-rose-700 mb-2">Forbidden actions</div>
            <List items={contract.forbidden_actions} testId="contract-forbidden-actions" />
          </div>
          <Separator />
          <div>
            <div className="text-[11px] font-mono uppercase tracking-widest text-slate-500 mb-2">Success conditions</div>
            <ol className="space-y-2" data-testid="contract-success-conditions">
              {contract.success_conditions?.map((c) => (
                <li key={c.id} className="flex items-start gap-2 text-sm">
                  <Badge variant="secondary" className="mt-0.5 font-mono">{c.id}</Badge>
                  <span className="text-slate-700 flex-1">{c.text}</span>
                </li>
              ))}
            </ol>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack} data-testid="contract-back-btn">
          <ArrowLeft className="h-4 w-4 mr-1" /> Edit request
        </Button>
        <Button className="flex-1 h-11" onClick={onNext} data-testid="contract-continue-btn">
          Continue to Guardian <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </div>
    </section>
  );
}

function GuardianScreen({ contract, telephony, scenarios, onExecute, executing, onBack }) {
  const [consent, setConsent] = useState(false);
  const [mode, setMode] = useState(telephony?.mode === "REAL" ? "REAL" : "SIMULATED");
  const [scenario, setScenario] = useState("cooperative");
  const [recipient, setRecipient] = useState("");

  const canProceed = consent && (mode === "SIMULATED" || (mode === "REAL" && recipient.trim()));

  return (
    <section className="space-y-4" data-testid="guardian-screen">
      <div className="space-y-1">
        <div className="text-xs font-mono uppercase tracking-widest text-slate-500">Step 3 · Guardian</div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Approve the controlled action</h2>
        <p className="text-sm text-slate-600">
          The Guardian enforces the hierarchy: <span className="font-mono">system safety → your consent → your goal → recipient input</span>. Recipients can never expand permissions.
        </p>
      </div>

      <Card className="border-rose-200 bg-rose-50/50">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-rose-700" />
            <CardTitle className="text-base font-semibold text-rose-900">Consent checkpoint</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-sm text-slate-700 space-y-2">
            <div><span className="font-mono text-xs text-slate-500 mr-2">PURPOSE</span>{contract.goal}</div>
            {contract.permitted_data?.length > 0 && (
              <div><span className="font-mono text-xs text-slate-500 mr-2">MAY SHARE</span>{contract.permitted_data.join(", ")}</div>
            )}
            {contract.forbidden_data?.length > 0 && (
              <div><span className="font-mono text-xs text-slate-500 mr-2">FORBIDDEN</span>{contract.forbidden_data.join(", ")}</div>
            )}
          </div>
          <Separator className="bg-rose-200" />
          <div className="flex items-start gap-3">
            <Switch
              id="consent-switch"
              checked={consent}
              onCheckedChange={setConsent}
              data-testid="consent-switch"
            />
            <Label htmlFor="consent-switch" className="text-sm leading-snug text-slate-800 cursor-pointer">
              I explicitly authorize Future Call AI to place this call under the exact terms of the Goal Contract. I understand I can revoke this at any time.
            </Label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold">Execution mode</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <button
              className={`px-3 py-2 text-sm rounded-md border font-medium ${mode === "SIMULATED" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 hover:border-slate-400"}`}
              onClick={() => setMode("SIMULATED")}
              data-testid="mode-simulated-btn"
            >
              Simulated
            </button>
            <button
              className={`px-3 py-2 text-sm rounded-md border font-medium ${mode === "REAL" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 hover:border-slate-400"} ${telephony?.mode !== "REAL" ? "opacity-60" : ""}`}
              onClick={() => setMode("REAL")}
              data-testid="mode-real-btn"
            >
              Real Twilio call
            </button>
            <ModeBadge mode={telephony?.mode || "UNKNOWN"} testId="mode-telephony-status" />
          </div>

          {mode === "REAL" && telephony?.mode !== "REAL" && (
            <Alert variant="destructive" data-testid="not-configured-alert">
              <Info className="h-4 w-4" />
              <AlertTitle>Twilio is NOT CONFIGURED</AlertTitle>
              <AlertDescription className="text-xs">
                Missing: {telephony?.missing?.join(", ")}. A real outbound call cannot be started until these are provided.
              </AlertDescription>
            </Alert>
          )}

          {mode === "SIMULATED" && (
            <div className="space-y-2">
              <Label className="text-xs font-mono uppercase tracking-wider text-slate-500">Simulated scenario</Label>
              <Select value={scenario} onValueChange={setScenario}>
                <SelectTrigger data-testid="scenario-select">
                  <SelectValue placeholder="Choose scenario" />
                </SelectTrigger>
                <SelectContent>
                  {scenarios.map((s) => (
                    <SelectItem key={s.key} value={s.key} data-testid={`scenario-option-${s.key}`}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-500">
                Every element produced by the simulator is labeled <span className="font-mono">SIMULATED</span> and never treated as real evidence.
              </p>
            </div>
          )}

          {mode === "REAL" && (
            <div className="space-y-2">
              <Label className="text-xs font-mono uppercase tracking-wider text-slate-500">Recipient phone number (E.164)</Label>
              <Input
                data-testid="recipient-input"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="+15551234567"
              />
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack} data-testid="guardian-back-btn">
          <ArrowLeft className="h-4 w-4 mr-1" /> Back
        </Button>
        <Button
          className="flex-1 h-11"
          disabled={!canProceed || executing}
          onClick={() => onExecute({ mode, scenario, recipient })}
          data-testid="authorize-btn"
        >
          {executing ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Starting…
            </>
          ) : (
            <>
              <PhoneCall className="h-4 w-4 mr-2" /> Authorize agent call
            </>
          )}
        </Button>
      </div>
    </section>
  );
}

function VerdictIcon({ verdict }) {
  const map = {
    VERIFIED_SUCCESS: ShieldCheck,
    PARTIAL: AlertTriangle,
    UNKNOWN: HelpCircle,
    FAILED: XCircle,
    IN_PROGRESS: Loader2,
  };
  const Icon = map[verdict] || HelpCircle;
  const spin = verdict === "IN_PROGRESS" ? "animate-spin" : "";
  return <Icon className={`h-5 w-5 ${spin}`} />;
}

function ResultScreen({ call, contract, onRestart }) {
  const verdictKey = call.goal_state || "UNKNOWN";
  const style = VERDICT_STYLES[verdictKey] || VERDICT_STYLES.UNKNOWN;
  const perCondition = call.verdict?.per_condition || [];
  const guardianBlocks = call.guardian_blocks || [];
  const transcript = call.transcript || [];

  return (
    <section className="space-y-4" data-testid="result-screen">
      <div className="space-y-1">
        <div className="text-xs font-mono uppercase tracking-widest text-slate-500">Step 5 · Result</div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Outcome</h2>
      </div>

      <Card className={`border ${style.heroClass}`} data-testid={`verdict-hero-${verdictKey}`}>
        <CardContent className="p-5 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={`${style.badgeClass} border font-mono uppercase tracking-wider text-[10px]`} data-testid="verdict-badge">
              <VerdictIcon verdict={verdictKey} />
              <span className="ml-1">{verdictKey.replace("_", " ")}</span>
            </Badge>
            <ModeBadge mode={call.mode || "SIMULATED"} testId="result-mode-badge" />
            <Badge variant="outline" className="font-mono text-[10px] uppercase tracking-wider" data-testid="provider-state-badge">
              provider: {call.provider_state || "—"}
            </Badge>
          </div>
          <div className="text-2xl font-bold tracking-tight text-slate-900">{style.label}</div>
          <div className="text-sm text-slate-700" data-testid="verdict-reason">{call.verdict_reason || style.subtitle}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <FileText className="h-4 w-4 text-slate-500" /> Evidence per condition
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3" data-testid="evidence-matrix">
          {perCondition.length === 0 && (
            <div className="text-sm text-slate-500 italic">No success conditions were defined.</div>
          )}
          {perCondition.map((c) => {
            const state = c.state;
            const isConfirmed = state === "CONFIRMED";
            const isContradicted = state === "CONTRADICTED";
            const cls = isConfirmed
              ? "border-emerald-200 bg-emerald-50/40"
              : isContradicted
                ? "border-rose-200 bg-rose-50/40"
                : "border-slate-200 bg-slate-50/40";
            const stateBadge = isConfirmed
              ? "bg-emerald-100 text-emerald-800 border-emerald-300"
              : isContradicted
                ? "bg-rose-100 text-rose-800 border-rose-300"
                : "bg-slate-100 text-slate-700 border-slate-300";
            return (
              <div key={c.condition_id} className={`rounded-md border p-3 ${cls}`} data-testid={`condition-${c.condition_id}`}>
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="secondary" className="font-mono">{c.condition_id}</Badge>
                  <Badge variant="outline" className={`${stateBadge} font-mono text-[10px] uppercase tracking-wider`}>
                    {state}
                  </Badge>
                </div>
                <div className="text-sm text-slate-800 font-medium">{c.requirement}</div>
                {c.supporting_evidence?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-emerald-700">Supporting evidence</div>
                    {c.supporting_evidence.map((e, i) => (
                      <blockquote key={i} className="text-xs text-slate-700 border-l-2 border-emerald-400 pl-2">
                        “{e.turn.text}” <span className="text-slate-400">— recipient</span>
                      </blockquote>
                    ))}
                  </div>
                )}
                {c.contradicting_evidence?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-rose-700">Contradicting evidence</div>
                    {c.contradicting_evidence.map((e, i) => (
                      <blockquote key={i} className="text-xs text-slate-700 border-l-2 border-rose-400 pl-2">
                        “{e.turn.text}” <span className="text-slate-400">— recipient</span>
                      </blockquote>
                    ))}
                  </div>
                )}
                {c.supporting_evidence?.length === 0 && c.contradicting_evidence?.length === 0 && (
                  <div className="mt-2 text-xs text-slate-500 italic">No explicit evidence found for this requirement.</div>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>

      {guardianBlocks.length > 0 && (
        <Card className="border-rose-200 bg-rose-50/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold text-rose-900 flex items-center gap-2">
              <Ban className="h-4 w-4" /> Guardian blocks
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2" data-testid="guardian-blocks">
            {guardianBlocks.map((b, i) => (
              <div key={i} className="text-sm text-rose-900">
                <span className="font-mono text-[10px] uppercase tracking-wider mr-2">turn {b.seq}</span>
                Blocked attempt to elicit: <span className="font-semibold">{b.matched}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold">Transcript</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2" data-testid="transcript">
          {transcript.length === 0 && <div className="text-sm text-slate-500 italic">No transcript captured.</div>}
          {transcript.map((t, i) => (
            <div key={i} className="text-sm">
              <span
                className={`inline-block font-mono text-[10px] uppercase tracking-widest mr-2 ${
                  t.role === "recipient"
                    ? "text-emerald-700"
                    : t.role === "agent"
                      ? "text-slate-900"
                      : "text-slate-400"
                }`}
              >
                {t.role}
              </span>
              <span className="text-slate-800">{t.text}</span>
              {t.mode && (
                <span className="ml-2 text-[10px] font-mono uppercase tracking-widest text-violet-600">
                  [{t.mode}]
                </span>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      <Button className="w-full h-11" variant="outline" onClick={onRestart} data-testid="new-request-btn">
        Start a new request
      </Button>
    </section>
  );
}

function Home() {
  const [step, setStep] = useState("request");
  const [telephony, setTelephony] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [contract, setContract] = useState(null);
  const [call, setCall] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    api.telephonyStatus().then(setTelephony).catch(() => setTelephony({ mode: "NOT_CONFIGURED", missing: [] }));
    api.scenarios().then((r) => setScenarios(r.scenarios || [])).catch(() => setScenarios([]));
  }, []);

  const onCompile = async (text) => {
    setSubmitting(true);
    try {
      const c = await api.createContract(text);
      setContract(c);
      setStep("contract");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not compile contract");
    } finally {
      setSubmitting(false);
    }
  };

  const onAuthorize = async ({ mode, scenario, recipient }) => {
    if (!contract) return;
    setExecuting(true);
    try {
      await api.consent(contract.id, true, recipient);
      const c = await api.execute(contract.id, mode, scenario, recipient);
      setCall(c);
      setStep("result");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Execution failed");
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header telephony={telephony} />
      <main className="mx-auto max-w-2xl px-4 py-6 pb-24 space-y-6">
        <Stepper current={step} />
        {step === "request" && <RequestScreen onSubmit={onCompile} submitting={submitting} />}
        {step === "contract" && contract && (
          <ContractScreen
            contract={contract}
            onBack={() => setStep("request")}
            onNext={() => setStep("guardian")}
          />
        )}
        {step === "guardian" && contract && (
          <GuardianScreen
            contract={contract}
            telephony={telephony}
            scenarios={scenarios}
            executing={executing}
            onExecute={onAuthorize}
            onBack={() => setStep("contract")}
          />
        )}
        {step === "result" && call && contract && (
          <ResultScreen
            call={call}
            contract={contract}
            onRestart={() => {
              setContract(null);
              setCall(null);
              setStep("request");
            }}
          />
        )}
      </main>
      <footer className="mx-auto max-w-2xl px-4 pb-8 text-center text-[11px] text-slate-400 font-mono uppercase tracking-widest">
        Provider state ≠ Goal state · AI claim ≠ Verified evidence
      </footer>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-center" />
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
