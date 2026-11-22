"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, BrainCircuit, Database, Gauge, MessageSquare, Search, ShieldCheck, Users } from "lucide-react";
import { api } from "@/lib/api";
import { getSession } from "@/lib/auth";

type Overview = { users: number; provider: string; retrieval_method: string; providers?: string[]; retrieval_methods?: string[]; fallback_enabled: boolean };
type User = { user_id: string; display_name: string; role: string; created_at: string };
type HistoryMessage = { message_id: string; role: "user" | "assistant"; content: string; created_at: string };
type HistoryConversation = { conversation_id: string; title: string; updated_at: string; archived: boolean; messages: HistoryMessage[] };
type UserDetail = { user: User; protocol: { current_version: string; accepted_current: boolean; acceptance?: { accepted_at_utc: string } | null }; profile: { mastery: Array<{concept_id: string; mastery: number; confidence: number; evidence_count: number}>; evidence: unknown[] }; conversations: HistoryConversation[] };

export default function AdminPage() {
  const router = useRouter(); const [overview, setOverview] = useState<Overview | null>(null); const [users, setUsers] = useState<User[]>([]);
  const [selected, setSelected] = useState<UserDetail | null>(null); const [selectedConversation, setSelectedConversation] = useState(""); const [filter, setFilter] = useState(""); const [error, setError] = useState("");
  const [metricUser, setMetricUser] = useState("");
  useEffect(() => {
    if (getSession()?.role !== "admin") { router.replace("/tutor"); return; }
    api<User[]>("/api/admin/users").then(setUsers).catch(reason => setError(reason.message));
  }, [router]);
  useEffect(() => {
    if (getSession()?.role !== "admin") return;
    const params = new URLSearchParams();
    if (metricUser) params.set("user_id", metricUser);
    api<Overview>(`/api/admin/overview${params.toString() ? `?${params}` : ""}`).then(setOverview).catch(reason => setError(reason.message));
  }, [metricUser]);
  async function selectUser(userId: string) { const detail = await api<UserDetail>(`/api/admin/users/${userId}`); setSelected(detail); setSelectedConversation(detail.conversations[0]?.conversation_id || ""); setMetricUser(userId); }
  const visible = users.filter(user => `${user.display_name} ${user.user_id}`.toLowerCase().includes(filter.toLowerCase()));
  const activeConversation = selected?.conversations.find(item => item.conversation_id === selectedConversation);
  return <main className="admin-page">
    <header className="admin-header"><div><button className="back-link" onClick={() => router.push("/tutor")}><ArrowLeft/> Volver al tutor</button><span className="eyebrow">ÁREA DE INVESTIGACIÓN</span><h1>Panel del estudio</h1><p>Observa el sistema sin exponer esta complejidad al estudiante.</p></div><div className="research-badge"><ShieldCheck/> Acceso autorizado</div></header>
    {error && <div className="chat-error">{error}</div>}
    <section className="metric-grid">
      <Metric icon={<Users/>} label="Usuarios" value={overview?.users ?? "—"}/>
      <Metric icon={<BrainCircuit/>} label="Retrieval activo" value={<MetricScroller values={overview?.retrieval_methods || []} fallback={overview?.retrieval_method ? displayLabel(overview.retrieval_method) : "—"}/>}/>
      <Metric icon={<MessageSquare/>} label="Modelo" value={<MetricScroller values={overview?.providers || []} fallback={overview?.provider ? displayLabel(overview.provider) : "—"}/>}/>
      <Metric icon={<Gauge/>} label="Fallback" value={overview?.fallback_enabled ? "Activo" : "Inactivo"}/>
    </section>
    <section className="admin-content">
      <div className="users-panel panel"><div className="panel-title"><div><span className="eyebrow">PARTICIPANTES</span><h2>Perfiles del estudio</h2></div><div className="search-box"><Search/><input placeholder="Buscar estudiante" value={filter} onChange={event => setFilter(event.target.value)}/></div></div>
        <div className="user-list">{visible.map(user => <button className={selected?.user.user_id === user.user_id ? "selected" : ""} key={user.user_id} onClick={() => selectUser(user.user_id)}><span className="user-initial">{user.display_name[0]?.toUpperCase()}</span><span><strong>{user.display_name}</strong><small>{user.user_id} · {user.role}</small></span></button>)}</div>
      </div>
      <div className="profile-panel panel">{selected ? <><div className="panel-title"><div><span className="eyebrow">PERFIL LONGITUDINAL</span><h2>{selected.user.display_name}</h2></div><Database/></div>
        <div className="profile-summary"><span><strong>{selected.profile.mastery.length}</strong> conceptos observados</span><span><strong>{selected.profile.evidence.length}</strong> evidencias</span><span><strong>{selected.conversations.length}</strong> conversaciones</span></div>
        <div className="protocol-admin-status"><ShieldCheck size={16}/><span>Protocolo: <strong>{selected.protocol.accepted_current ? "aceptado" : "pendiente"}</strong>{selected.protocol.acceptance ? ` · ${new Date(selected.protocol.acceptance.accepted_at_utc).toLocaleString("es-CO", { timeZone: "UTC" })} UTC` : ""}</span></div>
        <h3>Dominio por concepto</h3><div className="mastery-list">{selected.profile.mastery.length ? selected.profile.mastery.slice(0, 10).map(item => <div key={item.concept_id}><div><span>{item.concept_id.replaceAll("_", " ")}</span><strong>{Math.round(item.mastery * 100)}%</strong></div><div className="mastery-track"><i style={{width: `${item.mastery * 100}%`}}/></div><small>Confianza {Math.round(item.confidence * 100)}% · {item.evidence_count} evidencias</small></div>) : <p className="empty-note">Este estudiante todavía no tiene evidencias suficientes.</p>}</div>
        <div className="history-section"><h3>Historial de conversaciones</h3>{selected.conversations.length ? <><div className="history-tabs">{selected.conversations.map(item => <button className={selectedConversation === item.conversation_id ? "active" : ""} key={item.conversation_id} onClick={() => setSelectedConversation(item.conversation_id)}><strong>{item.title}</strong><small>{item.messages.length} mensajes{item.archived ? " · archivada" : ""}</small></button>)}</div>{activeConversation && <div className="research-transcript">{activeConversation.messages.length ? activeConversation.messages.map(message => <article className={message.role} key={message.message_id}><strong>{message.role === "user" ? "Estudiante" : "PATI"}</strong><p>{message.content}</p></article>) : <p className="empty-note">La conversación todavía no tiene mensajes.</p>}</div>}</> : <p className="empty-note">Este usuario todavía no ha creado conversaciones.</p>}</div>
      </> : <div className="empty-profile"><BrainCircuit/><h2>Selecciona un estudiante</h2><p>Aquí aparecerán su perfil conceptual, evidencias y conversaciones autorizadas.</p></div>}</div>
    </section>
  </main>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) { return <article className="metric-card"><span>{icon}</span><div><small>{label}</small>{value}</div></article>; }

function MetricScroller({ values, fallback }: { values: string[]; fallback: string }) {
  const visible = values.length ? values : [fallback];
  return <div className="metric-scroller" aria-label="Valores disponibles">
    {visible.map((item, index) => <strong key={`${item}-${index}`}>{displayLabel(item)}</strong>)}
  </div>;
}

function displayLabel(value: string) {
  return value.split(" · ").map(item => ({
    pep_plan_rag: "PEP-Plan-RAG v3",
    rag: "RAG baseline",
    graph_rag: "Graph-RAG",
    gemini: "Gemini",
    instructional: "Tutor instruccional",
    local_qwen3_1_7b: "Qwen local",
    local_base: "Modelo local",
    instructional_emergency: "Fallback instruccional",
  }[item] || item)).join(" · ");
}
