"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, FileText, ShieldCheck, Sparkles } from "lucide-react";
import { API_URL, api } from "@/lib/api";
import { getSession } from "@/lib/auth";

type Protocol = { title: string; version: string; summary: string; sections: string[]; pdf_url: string };
type Status = { current_version: string; accepted_current: boolean; acceptance?: { accepted_at_utc: string; protocol_version: string } | null };

export default function ProtocolPage() {
  const router = useRouter();
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getSession()) { router.replace("/"); return; }
    Promise.all([fetch(`${API_URL}/api/protocol`).then(response => response.json()), api<Status>("/api/me/protocol")])
      .then(([document, current]) => {
        setProtocol(document); setStatus(current);
        if (current.accepted_current && typeof window !== "undefined" && !window.location.search.includes("review=1")) router.replace("/tutor");
      })
      .catch(reason => setError(reason instanceof Error ? reason.message : "No fue posible cargar el protocolo"));
  }, [router]);

  async function acceptProtocol() {
    if (!protocol || !accepted) return;
    setBusy(true); setError("");
    try {
      await api("/api/me/protocol/accept", { method: "POST", body: JSON.stringify({ protocol_version: protocol.version, accepted: true }) });
      router.replace("/tutor");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No fue posible registrar la aceptación"); }
    finally { setBusy(false); }
  }

  if (!protocol || !status) return <main className="protocol-page"><div className="protocol-loading"><Sparkles/> Cargando el protocolo…</div></main>;

  return <main className="protocol-page">
    <section className="protocol-header">
      <div className="brand-mark"><Sparkles size={22}/> PATI</div>
      <span className="eyebrow">ANTES DE COMENZAR</span>
      <h1>Protocolo de datos y consentimiento</h1>
      <p>Lee el protocolo completo antes de entrar al tutor. Tu participación es voluntaria y seudónima.</p>
    </section>
    <section className="protocol-layout">
      <article className="protocol-summary glass-card">
        <div className="protocol-icon"><ShieldCheck/></div>
        <span className="eyebrow">RESUMEN</span>
        <h2>¿Qué explica este protocolo?</h2>
        <p>{protocol.summary}</p>
        <ul>{protocol.sections.map(section => <li key={section}><CheckCircle2 size={17}/><span>{section}</span></li>)}</ul>
        <div className="protocol-version"><FileText size={16}/> Versión vigente: <strong>{protocol.version}</strong></div>
        {status.accepted_current ? <div className="protocol-accepted"><CheckCircle2 size={18}/><span>Aceptación vigente registrada el <strong>{new Date(status.acceptance?.accepted_at_utc || "").toLocaleString("es-CO", { timeZone: "UTC" })} UTC</strong>.</span></div> : <label className="consent-check"><input type="checkbox" checked={accepted} onChange={event => setAccepted(event.target.checked)}/><span>He leído y acepto el protocolo de datos y el consentimiento para participar</span></label>}
        {error && <div className="form-error">{error}</div>}
        {status.accepted_current ? <button className="primary-button" onClick={() => router.push("/tutor")}>Volver al tutor<ArrowRight size={18}/></button> : <button className="primary-button" disabled={!accepted || busy} onClick={acceptProtocol}>{busy ? "Guardando aceptación…" : "Aceptar y continuar"}<ArrowRight size={18}/></button>}
        <small>La aceptación se registra con tu usuario seudónimo, la versión del protocolo y la fecha y hora UTC.</small>
      </article>
      <article className="protocol-preview glass-card">
        <div className="preview-heading"><div><span className="eyebrow">DOCUMENTO COMPLETO</span><h2>Previsualización</h2></div><FileText/></div>
        <iframe title="Protocolo completo de manejo ético de datos" src={`${API_URL}${protocol.pdf_url}`}/>
      </article>
    </section>
  </main>;
}
