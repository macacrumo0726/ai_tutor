"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Archive, ArrowUp, BookOpen, ChevronRight, LogOut, Menu, MessageCirclePlus, Palette, Sparkles, X } from "lucide-react";
import { Avatar, AvatarConfig, defaultAvatar } from "@/components/Avatar";
import { api, streamChat } from "@/lib/api";
import { clearSession, getSession, Session } from "@/lib/auth";

type Conversation = { conversation_id: string; title: string; updated_at: string; messages?: Message[] };
type Message = { message_id?: string; role: "user" | "assistant"; content: string; metadata?: Record<string, unknown> };
type Me = Session & { avatar: AvatarConfig };

const prompts = [
  "¿Cómo encuentro el dominio de una función racional?",
  "Ayúdame a factorizar x² - 5x + 6",
  "¿Cuál es la diferencia entre relación y función?",
];

export default function TutorPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [avatar, setAvatar] = useState<AvatarConfig>(defaultAvatar);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(false);
  const [sidebar, setSidebar] = useState(false);
  const [avatarOpen, setAvatarOpen] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversation = useCallback(async (id: string) => {
    const item = await api<Conversation>(`/api/conversations/${id}`);
    setActiveId(id); setMessages(item.messages || []); setSidebar(false);
  }, []);

  const createConversation = useCallback(async () => {
    const item = await api<Conversation>("/api/conversations", { method: "POST", body: JSON.stringify({ title: "Nueva conversación" }) });
    setConversations(previous => [item, ...previous]); setActiveId(item.conversation_id); setMessages([]); setSidebar(false);
  }, []);

  useEffect(() => {
    if (!getSession()) { router.replace("/"); return; }
    Promise.all([api<Me>("/api/me"), api<Conversation[]>("/api/conversations")])
      .then(async ([identity, list]) => {
        setMe(identity); setAvatar(identity.avatar || defaultAvatar); setConversations(list);
        if (list.length) await loadConversation(list[0].conversation_id); else await createConversation();
      })
      .catch(reason => { clearSession(); setError(reason.message); router.replace("/"); });
  }, [createConversation, loadConversation, router]);

  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, status]);

  async function send(message = input) {
    const clean = message.trim();
    if (!clean || !activeId || sending) return;
    setInput(""); setSending(true); setError(""); setStatus("Pensando contigo…");
    setMessages(previous => [...previous, { role: "user", content: clean }, { role: "assistant", content: "" }]);
    try {
      await streamChat(activeId, clean, {
        onStatus: setStatus,
        onToken: token => setMessages(previous => {
          const copy = [...previous]; const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, content: last.content + token }; return copy;
        }),
        onDone: () => setStatus(""),
      });
      const list = await api<Conversation[]>("/api/conversations"); setConversations(list);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "El tutor no pudo responder");
      setMessages(previous => previous.slice(0, -1));
    } finally { setSending(false); setStatus(""); }
  }

  async function saveAvatar() {
    const saved = await api<AvatarConfig>("/api/me/avatar", { method: "PUT", body: JSON.stringify(avatar) });
    setAvatar(saved); setAvatarOpen(false);
  }

  async function archive(id: string) {
    await api(`/api/conversations/${id}`, { method: "DELETE" });
    const remaining = conversations.filter(item => item.conversation_id !== id); setConversations(remaining);
    if (id === activeId) {
      if (remaining.length) await loadConversation(remaining[0].conversation_id);
      else await createConversation();
    }
  }

  async function logout() {
    await api("/api/auth/logout", { method: "POST" }).catch(() => null); clearSession(); router.replace("/");
  }

  const greeting = useMemo(() => me?.display_name?.split(" ")[0] || "estudiante", [me]);

  return (
    <main className="tutor-app">
      <aside className={sidebar ? "conversation-sidebar open" : "conversation-sidebar"}>
        <div className="sidebar-brand"><span><Sparkles size={20}/> PATI</span><button className="mobile-only icon-button" onClick={() => setSidebar(false)}><X/></button></div>
        <button className="new-chat" onClick={createConversation}><MessageCirclePlus size={19}/> Nueva conversación</button>
        <p className="sidebar-label">Tus conversaciones</p>
        <nav className="conversation-list">
          {conversations.map(item => <div className={item.conversation_id === activeId ? "conversation-item active" : "conversation-item"} key={item.conversation_id}>
            <button onClick={() => loadConversation(item.conversation_id)}><span>{item.title}</span><small>{new Date(item.updated_at).toLocaleDateString("es-CO", { day: "numeric", month: "short" })}</small></button>
            <button className="archive-button" aria-label="Archivar" onClick={() => archive(item.conversation_id)}><Archive size={15}/></button>
          </div>)}
        </nav>
        <div className="sidebar-footer">
          {me?.role === "researcher" && <button onClick={() => router.push("/admin")}><BookOpen size={17}/> Vista de investigación</button>}
          <button onClick={logout}><LogOut size={17}/> Cerrar sesión</button>
        </div>
      </aside>
      <section className="chat-workspace">
        <header className="chat-header">
          <button className="mobile-only icon-button" onClick={() => setSidebar(true)}><Menu/></button>
          <div className="tutor-identity"><div className="numa-orb"><Sparkles size={20}/></div><div><strong>PATI</strong><span><i/> Tutora disponible</span></div></div>
          <button className="profile-chip" onClick={() => setAvatarOpen(true)}><span>Hola, {greeting}</span><Avatar config={avatar} size={42}/><ChevronRight size={17}/></button>
        </header>
        <div className="messages-stage">
          {!messages.length ? <section className="empty-chat">
            <div className="hero-mascot"><div className="mascot-halo"/><div className="numa-face"><Sparkles size={35}/></div></div>
            <span className="eyebrow">APRENDAMOS JUNTOS</span>
            <h1>¿Qué quieres comprender hoy?</h1>
            <p>Puedes traer un ejercicio, contarme dónde te confundiste o pedirme que expliquemos un concepto desde el principio.</p>
            <div className="prompt-grid">{prompts.map(prompt => <button onClick={() => send(prompt)} key={prompt}>{prompt}<ArrowUp size={16}/></button>)}</div>
          </section> : <div className="message-column">
            {messages.map((message, index) => <article className={`message ${message.role}`} key={message.message_id || index}>
              {message.role === "assistant" && <div className="mini-tutor"><Sparkles size={16}/></div>}
              <div className="message-bubble">{message.content || <span className="typing"><i/><i/><i/></span>}</div>
            </article>)}
            {status && <div className="thinking-label"><Sparkles size={14}/>{status}</div>}
            <div ref={bottomRef}/>
          </div>}
        </div>
        {error && <div className="chat-error">{error}<button onClick={() => setError("")}><X size={15}/></button></div>}
        <div className="composer-wrap">
          <div className="composer">
            <textarea value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Escribe tu pregunta o cuéntame qué intentaste…" rows={1}/>
            <button disabled={!input.trim() || sending} onClick={() => send()} aria-label="Enviar"><ArrowUp/></button>
          </div>
          <small>PATI puede equivocarse. Comprueba los resultados importantes con tu docente.</small>
        </div>
      </section>
      {avatarOpen && <div className="modal-backdrop" onMouseDown={() => setAvatarOpen(false)}><section className="avatar-modal glass-card" onMouseDown={event => event.stopPropagation()}>
        <button className="modal-close" onClick={() => setAvatarOpen(false)}><X/></button>
        <div className="avatar-preview"><Avatar config={avatar} size={132} animated/><div><span className="eyebrow">TU COMPAÑERO VISUAL</span><h2>Hazlo tuyo</h2><p>El avatar se guarda como una configuración segura, no como una fotografía.</p></div></div>
        <AvatarOptions label="Color" values={["violet", "ocean", "mango", "mint"]} current={avatar.background} onChange={background => setAvatar({ ...avatar, background })}/>
        <AvatarOptions label="Tono" values={["sunny", "honey", "cocoa", "moon"]} current={avatar.skin_tone} onChange={skin_tone => setAvatar({ ...avatar, skin_tone })}/>
        <AvatarOptions label="Cabello" values={["waves", "curls", "short"]} current={avatar.hair} onChange={hair => setAvatar({ ...avatar, hair })}/>
        <AvatarOptions label="Detalle" values={["stars", "orbit", "glasses", "none"]} current={avatar.accessory} onChange={accessory => setAvatar({ ...avatar, accessory })}/>
        <button className="primary-button" onClick={saveAvatar}><Palette size={18}/> Guardar mi avatar</button>
      </section></div>}
    </main>
  );
}

function AvatarOptions({ label, values, current, onChange }: { label: string; values: string[]; current: string; onChange: (value: string) => void }) {
  return <div className="avatar-options"><strong>{label}</strong><div>{values.map(value => <button className={current === value ? "selected" : ""} key={value} onClick={() => onChange(value)}>{value}</button>)}</div></div>;
}
