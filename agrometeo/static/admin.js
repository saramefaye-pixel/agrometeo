"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  chargerTout();
  setInterval(chargerSessions,10000);
  setInterval(chargerStats,60000);
  setInterval(chargerAlertesRecentes,60000);
  setInterval(()=>{
    const c=document.getElementById("clockAdmin");
    if(c) c.textContent=new Date().toLocaleTimeString("fr-FR");
  },1000);
});

async function chargerTout(){
  await Promise.all([chargerStats(),chargerSessions(),chargerAlertesRecentes(),chargerUtilisateurs()]);
}

async function chargerStats(){
  try{
    const d=await fj("/api/admin/stats");
    document.getElementById("adminStats").innerHTML=`
      <div class="admin-stat-card"><div class="label">Mesures totales</div><div class="value">${d.nb_mesures_total}</div><div class="unit">documents</div></div>
      <div class="admin-stat-card bleu"><div class="label">Mesures (1h)</div><div class="value">${d.nb_mesures_1h}</div><div class="unit">nouvelles</div></div>
      <div class="admin-stat-card rouge"><div class="label">Alertes critiques</div><div class="value">${d.nb_alertes_critiques}</div><div class="unit">cette heure</div></div>
      <div class="admin-stat-card ambre"><div class="label">Avertissements</div><div class="value">${d.nb_alertes_warnings}</div><div class="unit">cette heure</div></div>
      <div class="admin-stat-card"><div class="label">Utilisateurs</div><div class="value">${d.nb_utilisateurs}</div><div class="unit">inscrits</div></div>
      <div class="admin-stat-card"><div class="label">Capteurs IoT</div><div class="value">${d.nb_capteurs}</div><div class="unit">actifs</div></div>`;
    const cols=d.collections;
    document.getElementById("collectionsGrid").innerHTML=
      Object.entries(cols).map(([n,c])=>`<div class="collection-card"><div class="collection-nom">${n}</div><div class="collection-count">${c}</div><div class="collection-unit">documents</div></div>`).join("");
  }catch(e){document.getElementById("adminStats").innerHTML=`<div class="admin-stat-card loading">Erreur: ${e.message}</div>`;}
}

async function chargerUtilisateurs(){
  const tbody=document.getElementById("tbodyUsers");
  try{
    const data=await fj("/api/admin/utilisateurs");
    if(!data.length){tbody.innerHTML=`<tr><td colspan="9" class="empty">Aucun utilisateur inscrit.</td></tr>`;return;}
    tbody.innerHTML=data.map(u=>`
      <tr>
        <td><strong>${u.avatar} ${u.username}</strong></td>
        <td>${u.nom_complet}</td>
        <td style="font-size:.8rem;color:#666;">${u.email}</td>
        <td style="font-size:.8rem;">${u.date_inscription||"—"}</td>
        <td>${(u.parcelles||[]).join(", ")||"<em style='color:#999'>Aucune</em>"}</td>
        <td>
          <input type="number" min="1" max="20" value="${u.quota_parcelles||3}"
            style="width:55px;padding:4px 6px;border:1px solid #dde;border-radius:6px;font-family:monospace;"
            onchange="setQuotaUser('${u.username}',this.value)"/>
        </td>
        <td style="font-family:'Space Mono',monospace;font-size:.8rem;">${u.nb_mesures}</td>
        <td><span style="font-size:.78rem;font-weight:700;padding:3px 10px;border-radius:50px;background:${u.en_ligne?'#d8f3dc':'#f0f0f0'};color:${u.en_ligne?'#1a5c2a':'#666'}">${u.en_ligne?'🟢 En ligne':'⚫ Hors ligne'}</span></td>
        <td><span style="font-size:.75rem;color:#666;">${(u.parcelles||[]).length}/${u.quota_parcelles||3}</span></td>
      </tr>`).join("");
  }catch(e){tbody.innerHTML=`<tr><td colspan="9" class="empty">Erreur: ${e.message}</td></tr>`;}
}

async function chargerSessions(){
  const el=document.getElementById("sessionsListe");
  try{
    const data=await fj("/api/admin/sessions");
    if(!data.length){el.innerHTML=`<div class="empty">Aucun utilisateur connecté.</div>`;return;}
    el.innerHTML=data.map(s=>`
      <div class="session-card">
        <div class="session-avatar">${s.avatar}</div>
        <div class="session-info">
          <div class="session-nom">${s.nom_complet} <span class="session-badge ${s.role}">${s.role}</span></div>
          <div class="session-detail">@${s.username} · ${s.email} · connecté depuis ${s.depuis} · ${s.nb_parcelles||0} parcelle(s)</div>
        </div>
        <div class="session-duree">${s.duree_min} min</div>
      </div>`).join("");
  }catch(e){el.innerHTML=`<div class="empty">Erreur: ${e.message}</div>`;}
}

async function chargerAlertesRecentes(){
  const tbody=document.getElementById("tbodyAlertesAdmin");
  try{
    const data=await fj("/api/admin/alertes_recentes");
    if(!data.length){tbody.innerHTML=`<tr><td colspan="6" class="empty">Aucune alerte.</td></tr>`;return;}
    tbody.innerHTML=data.map(a=>`
      <tr>
        <td style="font-family:'Space Mono',monospace;font-size:.78rem;">${a.timestamp?a.timestamp.slice(11,19):"—"}</td>
        <td><span class="${a.niveau==="critique"?"alerte-critique":"alerte-warning"}">${a.icone} ${a.niveau}</span></td>
        <td style="font-size:.8rem;">${a.username||"système"}</td>
        <td>${a.parcelle}</td>
        <td style="font-weight:600;font-size:.85rem;">${a.titre}</td>
        <td style="font-size:.78rem;color:#666;">${a.recommandation}</td>
      </tr>`).join("");
  }catch(e){tbody.innerHTML=`<tr><td colspan="6" class="empty">Erreur: ${e.message}</td></tr>`;}
}

async function setQuota(){
  const v=parseInt(document.getElementById("inputQuota").value);
  const msg=document.getElementById("msgQuota");
  try{
    await fj("/api/admin/set_quota","POST",{valeur:v});
    msg.className="action-msg ok"; msg.textContent=`✅ Quota global défini à ${v} parcelles.`;
  }catch(e){msg.className="action-msg err";msg.textContent="❌ "+e.message;}
}

async function setQuotaUser(username,valeur){
  try{await fj("/api/admin/set_quota","POST",{username,valeur:parseInt(valeur)});}
  catch(e){alert("Erreur: "+e.message);}
}

async function viderMesures(){
  if(!confirm("Supprimer les mesures de plus de 7 jours ?")) return;
  const msg=document.getElementById("msgVider");
  try{
    const d=await fj("/api/admin/vider_mesures","POST");
    msg.className="action-msg ok"; msg.textContent=`✅ ${d.supprimees} mesures supprimées.`;
    chargerStats();
  }catch(e){msg.className="action-msg err";msg.textContent="❌ "+e.message;}
}

async function fj(url,method="GET",body=null){
  const opts={method,headers:{}};
  if(body){opts.headers["Content-Type"]="application/json";opts.body=JSON.stringify(body);}
  const r=await fetch(url,opts);
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  const d=await r.json();
  if(d.erreur) throw new Error(d.erreur);
  return d;
}
