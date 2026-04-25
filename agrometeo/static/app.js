"use strict";
let chartInstance = null;
let niveauFiltreAlerte = "";
let _parcelles = [];

const SEUILS = {
  temperature:{critique_haut:40,warning_haut:35,warning_bas:10,critique_bas:5},
  humidite:   {critique_bas:20,warning_bas:30,warning_haut:85,critique_haut:95},
  ph_sol:     {critique_bas:5.0,warning_bas:5.5,warning_haut:8.0,critique_haut:8.5},
};
function etatValeur(type,valeur){
  const s=SEUILS[type]; if(!s) return{label:"—",cls:""};
  if(valeur>=( s.critique_haut||Infinity)||valeur<=(s.critique_bas||-Infinity)) return{label:"🔴 Critique",cls:"etat-critique"};
  if(valeur>=(s.warning_haut||Infinity)||valeur<=(s.warning_bas||-Infinity))   return{label:"🟡 Warning",cls:"etat-warning"};
  return{label:"✅ Normal",cls:"etat-ok"};
}

document.addEventListener("DOMContentLoaded",()=>{
  configurerOnglets();
  chargerParcelles().then(()=>chargerTout());
  // Rafraîchissement automatique toutes les 60s — SANS bouton
  setInterval(chargerTout, 60_000);
  setInterval(chargerResumeAlertes, 30_000);
});

function configurerOnglets(){
  document.querySelectorAll(".tab").forEach(btn=>{
    btn.addEventListener("click",()=>{
      document.querySelectorAll(".tab").forEach(b=>b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c=>c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-"+btn.dataset.tab).classList.add("active");
    });
  });
}

async function chargerTout(){
  await Promise.all([
    verifierStatut(), chargerMesures(), chargerAnomalies(),
    chargerAggregation(), chargerAlertes(), chargerRecommandations()
  ]);
}

async function verifierStatut(){
  const badge=document.getElementById("statusBadge");
  const texte=document.getElementById("statusText");
  const statsEl=document.getElementById("statsGrid");
  try{
    const d=await fetchJson("/api/status");
    if(d.ok){
      badge.className="status-badge connected";
      texte.textContent="Connecté";
      statsEl.innerHTML=`
        <div class="stat-card"><div class="label">Mes mesures</div><div class="value">${d.nb_mesures}</div><div class="unit">enregistrements</div></div>
        <div class="stat-card"><div class="label">Capteurs actifs</div><div class="value">${d.nb_capteurs}</div><div class="unit">capteurs IoT</div></div>
        <div class="stat-card"><div class="label">Fréquence</div><div class="value">1</div><div class="unit">mesure / minute</div></div>
        <div class="stat-card"><div class="label">Dernière MAJ</div><div class="value" style="font-size:1rem;">${heureActuelle()}</div><div class="unit">automatique</div></div>`;
    }else{ badge.className="status-badge error"; texte.textContent="Erreur"; }
  }catch(e){ badge.className="status-badge error"; texte.textContent="Hors ligne"; }
}

async function chargerParcelles(){
  try{
    const [parcelles,capteurs]=await Promise.all([fetchJson("/api/parcelles"),fetchJson("/api/capteurs")]);
    _parcelles=parcelles;
    const sel=document.getElementById("selectParcelle");
    const selAP=document.getElementById("alerteParcelle");
    sel.innerHTML='<option value="">Toutes mes parcelles</option>';
    selAP.innerHTML='';
    parcelles.forEach(p=>{
      sel.innerHTML+=`<option value="${p}">${p}</option>`;
      selAP.innerHTML+=`<option value="${p}">${p}</option>`;
    });
    const selC=document.getElementById("selectCapteurGraph");
    selC.innerHTML='';
    capteurs.forEach(c=>{
      selC.innerHTML+=`<option value="${c.capteur_id}">${c.capteur_id} — ${c.parcelle} (${libelle(c.type)})</option>`;
    });
    // Quota info
    const quotaEl=document.getElementById("quotaInfo");
    const quotaTexte=document.getElementById("quotaTexte");
    try{
      const info=await fetchJson("/api/mes_parcelles");
      const nbParcelles=info.length;
      // On essaie de deviner le quota depuis le dashboard (injecté en data-attr)
      quotaTexte.textContent=`📍 ${nbParcelles} parcelle(s) active(s) — Rafraîchissement automatique toutes les 60s`;
    }catch(e){}
    if(capteurs.length) chargerGraphique();
  }catch(e){}
}

async function chargerMesures(){
  const parcelle=document.getElementById("selectParcelle").value;
  const type=document.getElementById("selectType").value;
  const limite=document.getElementById("selectLimite").value;
  const tbody=document.getElementById("tbodyMesures");
  const params=new URLSearchParams();
  if(parcelle) params.set("parcelle",parcelle);
  if(type) params.set("type",type);
  params.set("limite",limite);
  try{
    const data=await fetchJson("/api/mesures?"+params);
    if(!data.length){tbody.innerHTML=`<tr><td colspan="7" class="empty">Aucune mesure.</td></tr>`;return;}
    tbody.innerHTML=data.map(m=>{
      const etat=etatValeur(m.type,m.valeur);
      return`<tr><td>${m.timestamp}</td><td>${m.capteur_id}</td><td>${m.parcelle}</td>
      <td><span class="type-badge badge-${m.type}">${libelle(m.type)}</span></td>
      <td><strong>${m.valeur}</strong></td><td>${m.unite}</td>
      <td class="${etat.cls}">${etat.label}</td></tr>`;
    }).join("");
  }catch(e){tbody.innerHTML=`<tr><td colspan="7" class="empty">Erreur : ${e.message}</td></tr>`;}
}

async function chargerAnomalies(){
  const parcelle=document.getElementById("selectParcelle").value;
  const tbody=document.getElementById("tbodyAnomalies");
  const params=new URLSearchParams();
  if(parcelle) params.set("parcelle",parcelle);
  try{
    const data=await fetchJson("/api/anomalies?"+params);
    if(!data.length){tbody.innerHTML=`<tr><td colspan="5" class="empty">✅ Aucune anomalie.</td></tr>`;return;}
    tbody.innerHTML=data.map(m=>{
      const n=m.valeur<20?`<span class="etat-critique">🔴 Critique</span>`:`<span class="etat-warning">🟡 Avertissement</span>`;
      return`<tr><td>${m.timestamp}</td><td>${m.capteur_id}</td><td>${m.parcelle}</td><td><strong>${m.valeur}%</strong></td><td>${n}</td></tr>`;
    }).join("");
  }catch(e){tbody.innerHTML=`<tr><td colspan="5" class="empty">Erreur</td></tr>`;}
}

async function chargerAggregation(){
  const el=document.getElementById("agregCards");
  try{
    const data=await fetchJson("/api/stats/temperature");
    if(!data.length){el.innerHTML=`<div class="agreg-card loading">Pas encore de données sur 24h.</div>`;return;}
    el.innerHTML=data.map(d=>`
      <div class="agreg-card">
        <div class="parcelle-title">🌿 ${d.parcelle}</div>
        <div class="metric"><span class="metric-label">Moyenne</span><span class="metric-value moyenne">${d.moyenne} °C</span></div>
        <div class="metric"><span class="metric-label">Min</span><span class="metric-value">${d.min} °C</span></div>
        <div class="metric"><span class="metric-label">Max</span><span class="metric-value">${d.max} °C</span></div>
        <div class="metric"><span class="metric-label">Nb mesures</span><span class="metric-value">${d.nb_mesures}</span></div>
      </div>`).join("");
  }catch(e){el.innerHTML=`<div class="agreg-card loading">Erreur</div>`;}
}

async function chargerAlertes(){
  await chargerResumeAlertes();
  await afficherAlertes(niveauFiltreAlerte);
}

async function chargerResumeAlertes(){
  try{
    const d=await fetchJson("/api/alertes/resume");
    const compteurs=document.getElementById("alerteCompteurs");
    const badge=document.getElementById("badgeAlertes");
    const banniere=document.getElementById("banniereAlerte");
    const total=d.critiques+d.warnings;
    if(total>0){
      compteurs.style.display="flex";
      document.getElementById("cptCritique").textContent=`${d.critiques} critique${d.critiques>1?"s":""}`;
      document.getElementById("cptWarning").textContent=`${d.warnings} warning${d.warnings>1?"s":""}`;
      badge.style.display="inline-block"; badge.textContent=total;
    }else{ compteurs.style.display="none"; badge.style.display="none"; }
    if(d.critiques>0){
      banniere.style.display="flex";
      document.getElementById("banniereTexte").textContent=`${d.critiques} alerte(s) critique(s) sur vos parcelles !`;
    }
  }catch(e){}
}

async function afficherAlertes(niveau){
  const liste=document.getElementById("alertesListe");
  const parcelle=document.getElementById("selectParcelle").value;
  const params=new URLSearchParams({limite:40});
  if(niveau) params.set("niveau",niveau);
  if(parcelle) params.set("parcelle",parcelle);
  try{
    const data=await fetchJson("/api/alertes?"+params);
    if(!data.length){liste.innerHTML=`<div class="empty">✅ Aucune alerte.</div>`;return;}
    liste.innerHTML=data.map(a=>`
      <div class="alerte-card ${a.niveau}">
        <div class="alerte-icone">${a.icone}</div>
        <div class="alerte-body">
          <div class="alerte-titre">${a.titre}</div>
          <div class="alerte-message">${a.message}</div>
          <div class="alerte-reco">💡 ${a.recommandation}</div>
          ${a.source==="manuel"?'<span style="font-size:0.72rem;color:#888;">✏️ Signalé manuellement</span>':""}
        </div>
        <div class="alerte-meta">
          <div class="alerte-ts">${a.timestamp?a.timestamp.slice(11,16):""}</div>
          <div class="alerte-parcelle">${a.parcelle}</div>
        </div>
      </div>`).join("");
  }catch(e){liste.innerHTML=`<div class="empty">Erreur</div>`;}
}

function filtrerAlertes(niveau){
  niveauFiltreAlerte=niveau;
  document.querySelectorAll(".btn-filtre").forEach(b=>b.classList.remove("active"));
  const map={"":"fAll","critique":"fCritique","warning":"fWarning"};
  const el=document.getElementById(map[niveau]);
  if(el) el.classList.add("active");
  afficherAlertes(niveau);
}

async function chargerRecommandations(){
  const grid=document.getElementById("recoGrid");
  const parcelle=document.getElementById("selectParcelle").value;
  const params=new URLSearchParams();
  if(parcelle) params.set("parcelle",parcelle);
  try{
    const data=await fetchJson("/api/recommandations?"+params);
    if(!data.length){grid.innerHTML=`<div class="reco-card loading">Patientez 1 minute...</div>`;return;}
    grid.innerHTML=data.map(r=>`
      <div class="reco-card statut-${r.statut}">
        <div class="reco-parcelle">🌿 ${r.parcelle}</div>
        <div class="reco-statut">${r.icone} ${r.statut.charAt(0).toUpperCase()+r.statut.slice(1)}</div>
        <div class="reco-conseil">${r.conseil}</div>
        <div class="reco-valeurs">
          <span class="reco-val">🌡️ ${r.temperature}°C</span>
          <span class="reco-val">💧 ${r.humidite}%</span>
          <span class="reco-val">⚗️ pH ${r.ph_sol}</span>
        </div>
      </div>`).join("");
  }catch(e){grid.innerHTML=`<div class="reco-card loading">Erreur</div>`;}
}

async function chargerGraphique(){
  const capteurId=document.getElementById("selectCapteurGraph").value;
  const heures=document.getElementById("selectHeures").value;
  const canvas=document.getElementById("chartEvolution");
  const emptyMsg=document.getElementById("chartEmpty");
  if(!capteurId) return;
  try{
    const data=await fetchJson(`/api/evolution?capteur_id=${capteurId}&heures=${heures}`);
    if(!data.length){canvas.style.display="none";emptyMsg.style.display="block";return;}
    canvas.style.display="block"; emptyMsg.style.display="none";
    const labels=data.map(d=>d.heure.slice(11,16));
    const moyennes=data.map(d=>d.moyenne);
    const mins=data.map(d=>d.min);
    const maxs=data.map(d=>d.max);
    if(chartInstance) chartInstance.destroy();
    chartInstance=new Chart(canvas,{
      type:"line",
      data:{labels,datasets:[
        {label:"Moyenne",data:moyennes,borderColor:"#2d6a4f",backgroundColor:"rgba(45,106,79,0.1)",borderWidth:2.5,pointRadius:4,tension:0.4,fill:true},
        {label:"Min",data:mins,borderColor:"#52b788",borderWidth:1.5,borderDash:[5,5],pointRadius:2,tension:0.4,fill:false},
        {label:"Max",data:maxs,borderColor:"#e9c46a",borderWidth:1.5,borderDash:[5,5],pointRadius:2,tension:0.4,fill:false},
      ]},
      options:{responsive:true,interaction:{mode:"index",intersect:false},
        plugins:{legend:{position:"top"},title:{display:true,text:`Évolution — ${capteurId} (${heures}h)`,font:{size:13},color:"#1a3a2a"}},
        scales:{y:{grid:{color:"rgba(45,106,79,0.1)"}},x:{grid:{display:false}}}}
    });
  }catch(e){}
}

// ── Nouvelle parcelle ─────────────────────────────────────────────────────────
async function ajouterParcelle(){
  const nom=prompt("Nom de la nouvelle parcelle (ex: Parcelle D) :");
  if(!nom||!nom.trim()) return;
  try{
    const res=await fetchJson("/api/ajouter_parcelle","POST",{nom:nom.trim()});
    if(res.ok){
      alert("✅ "+res.message);
      await chargerParcelles();
      chargerTout();
    }
  }catch(e){alert("❌ "+e.message);}
}

// ── Alerte manuelle ───────────────────────────────────────────────────────────
async function envoyerAlerte(){
  const msg=document.getElementById("msgAlerte");
  const data={
    parcelle: document.getElementById("alerteParcelle").value,
    niveau:   document.getElementById("alerteNiveau").value,
    titre:    document.getElementById("alerteTitre").value.trim(),
    message:  document.getElementById("alerteMessage").value.trim(),
    recommandation: document.getElementById("alerteReco").value.trim(),
  };
  if(!data.parcelle||!data.titre||!data.message){
    msg.style.cssText="color:#c0392b;"; msg.textContent="❌ Parcelle, titre et message sont obligatoires."; return;
  }
  try{
    await fetchJson("/api/ajouter_alerte","POST",data);
    msg.style.cssText="color:#2d6a4f;"; msg.textContent="✅ Alerte envoyée avec succès !";
    document.getElementById("alerteTitre").value="";
    document.getElementById("alerteMessage").value="";
    document.getElementById("alerteReco").value="";
    chargerAlertes();
  }catch(e){msg.style.cssText="color:#c0392b;"; msg.textContent="❌ "+e.message;}
}

// ── Utilitaires ───────────────────────────────────────────────────────────────
async function fetchJson(url,method="GET",body=null){
  const opts={method,headers:{"Content-Type":"application/json"}};
  if(body) opts.body=JSON.stringify(body);
  const r=await fetch(url,opts);
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  const d=await r.json();
  if(d.erreur) throw new Error(d.erreur);
  return d;
}
function libelle(type){return{temperature:"Température",humidite:"Humidité",ph_sol:"pH sol"}[type]||type;}
function heureActuelle(){return new Date().toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit",second:"2-digit"});}

// ─── Horloge ─────────────────────────────────────────────────────────────────
setInterval(()=>{
  const c=document.getElementById("clockUser");
  if(c) c.textContent=new Date().toLocaleTimeString("fr-FR");
},1000);

// ─── Modal parcelle ───────────────────────────────────────────────────────────
function ouvrirModalParcelle(){
  document.getElementById("modalParcelle").style.display="flex";
  document.getElementById("inputNomParcelle").focus();
}
async function ajouterParcelle(){
  const nom=document.getElementById("inputNomParcelle").value.trim();
  const msg=document.getElementById("msgParcelle");
  if(!nom){msg.style.color="#e63946";msg.textContent="Veuillez entrer un nom.";return;}
  try{
    const d=await fetchJson("/api/ajouter_parcelle","POST",{nom});
    msg.style.color="#2d6a4f";
    msg.textContent=`✅ Parcelle "${d.parcelle}" ajoutée !`;
    document.getElementById("inputNomParcelle").value="";
    setTimeout(()=>{
      document.getElementById("modalParcelle").style.display="none";
      chargerTout();
    },1500);
  }catch(e){msg.style.color="#e63946";msg.textContent="❌ "+e.message;}
}

// ─── Modal alerte manuelle ────────────────────────────────────────────────────
async function ouvrirModalAlerte(){
  const sel=document.getElementById("selectParcelleAlerte");
  sel.innerHTML="";
  try{
    const parcelles=await fetchJson("/api/parcelles");
    parcelles.forEach(p=>{const o=document.createElement("option");o.value=p;o.textContent=p;sel.appendChild(o);});
  }catch(e){}
  document.getElementById("modalAlerte").style.display="flex";
}
async function envoyerAlerte(){
  const parcelle=document.getElementById("selectParcelleAlerte").value;
  const message=document.getElementById("inputMessageAlerte").value.trim();
  const msg=document.getElementById("msgAlerte");
  if(!message){msg.style.color="#e63946";msg.textContent="Veuillez décrire le problème.";return;}
  try{
    await fetchJson("/api/alerte_manuelle","POST",{parcelle,message});
    msg.style.color="#2d6a4f";msg.textContent="✅ Alerte envoyée à l'administrateur !";
    document.getElementById("inputMessageAlerte").value="";
    setTimeout(()=>{document.getElementById("modalAlerte").style.display="none";chargerAlertes();},1500);
  }catch(e){msg.style.color="#e63946";msg.textContent="❌ "+e.message;}
}

// ─── fetchJson étendu pour POST avec body ─────────────────────────────────────
const _fetchJsonOrig = fetchJson;
async function fetchJson(url, method="GET", body=null){
  const opts={method,headers:{}};
  if(body){opts.headers["Content-Type"]="application/json";opts.body=JSON.stringify(body);}
  const r=await fetch(url,opts);
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  const d=await r.json();
  if(d.erreur) throw new Error(d.erreur);
  return d;
}
