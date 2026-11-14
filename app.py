"""
Tarification automobile de A à Z — application Streamlit
Auteure : Pamela Fagla (M2 Actuariat, ISUP)

Les paramètres du tarif viennent du notebook « Tarification_Auto_de_A_a_Z.ipynb »
(fichier parametres_tarif.json, étape 22). Les résultats de suivi (S/P, déciles,
machine learning) sont des résultats agrégés recopiés du même notebook :
l'app ne recharge aucune donnée individuelle.
Données : freMTPL2freq / freMTPL2sev (CASdatasets, Dutang & Charpentier).
"""

import json
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Tarification auto de A à Z", page_icon="🚗", layout="wide")

# ---------------------------------------------------------------------------
# Palette et style
# ---------------------------------------------------------------------------
NAVY, CORAL, IVORY, SAND, INK, MUTED = "#13294B", "#E8684A", "#FAF7F0", "#EFE8DA", "#1F2633", "#6B7280"
ZONE_COLORS = {"Z1": "#C9D6E8", "Z2": "#8FA8C8", "Z3": "#F2B8A2", "Z4": "#E8684A"}

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, p, li, label {{ font-family: 'Inter', sans-serif; color: {INK}; }}
h1, h2, h3, .serif {{ font-family: 'Fraunces', serif !important; color: {NAVY} !important; letter-spacing: -0.01em; }}
.block-container {{ padding-top: 1.6rem; max-width: 1250px; }}
.hero {{ background: {NAVY}; border-radius: 22px; padding: 2.1rem 2.4rem; color: {IVORY}; margin-bottom: 1.4rem; }}
.hero h1 {{ color: {IVORY} !important; font-size: 2.4rem; margin: 0 0 .4rem 0; }}
.hero p {{ color: #D8DEE9; margin: 0; font-size: 1.02rem; max-width: 760px; }}
.hero .tag {{ display:inline-block; background:{CORAL}; color:white; border-radius:999px; padding:.18rem .75rem;
             font-size:.78rem; font-weight:600; letter-spacing:.04em; margin-bottom:.9rem; }}
.kpi {{ background: white; border: 1px solid {SAND}; border-radius: 16px; padding: 1rem 1.2rem; }}
.kpi .v {{ font-family: 'Fraunces', serif; font-size: 1.9rem; color: {NAVY}; line-height: 1.1; }}
.kpi .l {{ font-size: .82rem; color: {MUTED}; text-transform: uppercase; letter-spacing: .05em; }}
.card {{ background: white; border: 1px solid {SAND}; border-radius: 18px; padding: 1.3rem 1.5rem; }}
.ticket {{ background: white; border: 1px solid {SAND}; border-radius: 18px; padding: 1.4rem 1.6rem;
           box-shadow: 0 10px 30px rgba(19,41,75,.07); }}
.ticket .row {{ display:flex; justify-content:space-between; padding:.42rem 0; border-bottom:1px dashed {SAND}; font-size:.95rem; }}
.ticket .row span:first-child {{ color:{MUTED}; }}
.ticket .sub {{ font-weight:600; color:{NAVY}; border-bottom:1px solid {SAND}; }}
.ticket .sub span:first-child {{ color:{NAVY}; }}
.ticket .total {{ display:flex; justify-content:space-between; align-items:baseline; margin-top:.9rem; }}
.ticket .total .v {{ font-family:'Fraunces', serif; font-size:2.6rem; color:{CORAL}; }}
.ticket .step {{ font-size:.72rem; color:{CORAL}; font-weight:600; letter-spacing:.06em; text-transform:uppercase; margin-top:.7rem; }}
.note {{ font-size:.85rem; color:{MUTED}; }}
.lesson {{ border-left: 4px solid {CORAL}; background: white; padding: .8rem 1.1rem; border-radius: 0 12px 12px 0; margin: .4rem 0; }}
.stTabs [data-baseweb="tab-list"] {{ gap: .4rem; }}
.stTabs [data-baseweb="tab"] {{ background: white; border: 1px solid {SAND}; border-radius: 999px; padding: .35rem 1.1rem; }}
.stTabs [aria-selected="true"] {{ background: {NAVY} !important; color: white !important; }}
.stTabs [aria-selected="true"] p {{ color: white !important; }}
footer {{ visibility: hidden; }}
</style>
""",
    unsafe_allow_html=True,
)


def layout(fig, h=360):
    fig.update_layout(
        height=h, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=INK), legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=SAND)
    return fig


def eur(x):
    return f"{x:,.0f} €".replace(",", " ")


# ---------------------------------------------------------------------------
# Paramètres du tarif (export du notebook, étape 22)
# ---------------------------------------------------------------------------
@st.cache_data
def charger_parametres():
    with open("parametres_tarif.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def charger_carte():
    with open("regions_france.geojson", encoding="utf-8") as f:
        return json.load(f)


P = charger_parametres()
F, C = P["freq"], P["cout"]

AGE_BINS = [17, 21, 25, 30, 45, 60, 75, 101]
VEH_BINS = [-1, 1, 5, 10, 15, 101]
REGIONS = {
    "R11": "Île-de-France", "R21": "Champagne-Ardenne", "R22": "Picardie", "R23": "Haute-Normandie", "R24": "Centre",
    "R25": "Basse-Normandie", "R26": "Bourgogne", "R31": "Nord-Pas-de-Calais", "R41": "Lorraine", "R42": "Alsace",
    "R43": "Franche-Comté", "R52": "Pays de la Loire", "R53": "Bretagne", "R54": "Poitou-Charentes", "R72": "Aquitaine",
    "R73": "Midi-Pyrénées", "R74": "Limousin", "R82": "Rhône-Alpes", "R83": "Auvergne", "R91": "Languedoc-Roussillon",
    "R93": "Provence-Alpes-Côte d'Azur", "R94": "Corse",
}


def tranche(x, bins):
    for a, b in zip(bins[:-1], bins[1:]):
        if a < x <= b:
            return a, b
    return bins[-2], bins[-1]


def relativites(profil):
    """Relativité de chaque variable (1 = catégorie de référence du GLM)."""
    a, b = tranche(profil["age"], AGE_BINS)
    va, vb = tranche(profil["veh_age"], VEH_BINS)
    k_age = f"DrivAge_tr[T.Interval({a}, {b}, closed='right')]"
    k_veh = f"VehAge_tr[T.Interval({va}, {vb}, closed='right')]"
    k_zone = f'C(Zone, Treatment("Z3"))[T.{profil["zone"]}]'
    beta_dens = math.log(F["logDensity"])
    freq = {
        "Âge du conducteur": F.get(k_age, 1.0),
        "Âge du véhicule": F.get(k_veh, 1.0),
        "Puissance": F.get(f"C(VehPower_tr)[T.{min(profil['puissance'], 9)}]", 1.0),
        "Carburant": F.get(f"VehGas[T.{profil['carburant']}]", 1.0),
        "Marque": F.get(f"VehBrand[T.{profil['marque']}]", 1.0),
        "Zone (zonier)": F.get(k_zone, 1.0),
        "Densité": profil["densite"] ** beta_dens,
    }
    cout = {
        "Âge du conducteur": C.get(k_age, 1.0),
        "Âge du véhicule": C.get(k_veh, 1.0),
        "Zone (zonier)": C.get(k_zone, 1.0),
    }
    return freq, cout, f"({a}, {b}]"


def tarifer(profil):
    rf, rc, cle_age = relativites(profil)
    freq = F["Intercept"] * math.prod(rf.values())
    cout = C["Intercept"] * math.prod(rc.values())
    pure = freq * cout * P["coef_surcharge"]
    commerciale = pure / (1 - P["taux_frais"] - P["taux_marge"])
    correction = P["correction_age"][cle_age]
    reference = commerciale / P["facteur_crm"] * correction
    finale = reference * profil["crm"]
    return dict(freq=freq, cout=cout, pure=pure, commerciale=commerciale, correction=correction,
                reference=reference, finale=finale, rf=rf, rc=rc)


PROFIL_TYPE = dict(age=40, veh_age=6, puissance=6, carburant="Diesel", marque="B12", zone="Z3", densite=300, crm=1.0)

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------
st.markdown(
    """
<div class="hero">
  <div class="tag">PROJET ACTUARIAT · TARIFICATION NON-VIE</div>
  <h1>Tarification automobile de A à Z</h1>
  <p>De la donnée brute au prix affiché : GLM fréquence et coût, zonier, prime pure et commerciale,
  bonus-malus, suivi du portefeuille et défis du métier. Données réelles de 678 000 contrats RC auto français.</p>
</div>
""",
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
for col, v, l in [
    (k1, "678 013", "contrats analysés"),
    (k2, "7,4", "sinistres pour 100 assurés / an"),
    (k3, "2 266 €", "coût moyen d'un sinistre"),
    (k4, "167 €", "prime pure moyenne"),
]:
    col.markdown(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)

st.write("")
t1, t2, t3, t4, t5 = st.tabs(["🧾 Simulateur", "🗺️ Zonier", "🔁 Bonus-malus", "📊 Suivi du portefeuille", "🧭 Défis du métier"])

# ---------------------------------------------------------------------------
# 1. Simulateur
# ---------------------------------------------------------------------------
with t1:
    gauche, droite = st.columns([1, 1.15], gap="large")
    with gauche:
        st.markdown("### Le profil à tarifer")
        c1, c2 = st.columns(2)
        with c1:
            age = st.slider("Âge du conducteur", 18, 99, 23)
            region = st.selectbox("Région", list(REGIONS), format_func=lambda r: REGIONS[r], index=17)
            densite = st.select_slider(
                "Densité de la commune (hab/km²)",
                options=[10, 30, 100, 300, 1000, 3000, 10000, 27000], value=3000,
                help="10 : village · 300 : petite ville · 3 000 : grande ville · 27 000 : Paris",
            )
            crm = st.slider("Bonus-malus (CRM)", 0.50, 3.50, 1.00, 0.01,
                            help="1,00 pour un premier contrat ; 0,50 = bonus maximal")
        with c2:
            veh_age = st.slider("Âge du véhicule (ans)", 0, 30, 6)
            puissance = st.selectbox("Puissance fiscale", list(range(4, 16)), index=2)
            carburant = st.radio("Carburant", ["Diesel", "Regular"], horizontal=True,
                                 format_func=lambda x: "Essence" if x == "Regular" else x)
            marque = st.selectbox("Marque (anonymisée)", [f"B{i}" for i in [1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14]], index=8)

        profil = dict(age=age, veh_age=veh_age, puissance=puissance, carburant=carburant, marque=marque,
                      zone=P["zones"][region], densite=densite, crm=crm)
        r = tarifer(profil)
        ref = tarifer(PROFIL_TYPE)

        st.markdown(f"**Ce qui pèse dans ce tarif** <span class='note'>· écart avec un profil type "
                    f"(40 ans, véhicule de 6 ans, diesel, petite ville)</span>", unsafe_allow_html=True)
        ecarts = {}
        for k in r["rf"]:
            ecarts[k] = r["rf"][k] * r["rc"].get(k, 1) / (ref["rf"][k] * ref["rc"].get(k, 1))
        df = pd.DataFrame({"facteur": list(ecarts), "ecart": [(v - 1) * 100 for v in ecarts.values()]}).sort_values("ecart")
        fig = go.Figure(go.Bar(
            x=df["ecart"], y=df["facteur"], orientation="h",
            marker_color=[CORAL if v > 0 else NAVY for v in df["ecart"]],
            text=[f"{v:+.0f} %" for v in df["ecart"]], textposition="outside", cliponaxis=False,
        ))
        lo, hi = min(df["ecart"].min(), 0), max(df["ecart"].max(), 0)
        pad = max(hi - lo, 10) * 0.25
        fig.add_vline(x=0, line_color=MUTED, line_width=1)
        st.plotly_chart(layout(fig, 300).update_xaxes(ticksuffix=" %", zeroline=False, range=[lo - pad, hi + pad]),
                        use_container_width=True)

    with droite:
        st.markdown("### Le ticket de tarif")
        st.markdown(
            f"""
<div class="ticket">
  <div class="step">① Prime pure — ce que coûtent les sinistres</div>
  <div class="row"><span>Fréquence prédite (GLM Poisson)</span><span>{r['freq']*100:.1f} sinistres / 100 ans</span></div>
  <div class="row"><span>× Coût moyen écrêté à 20 000 € (GLM Gamma)</span><span>{eur(r['cout'])}</span></div>
  <div class="row"><span>× Surcharge gros sinistres (mutualisation)</span><span>× {P['coef_surcharge']:.3f}</span></div>
  <div class="row sub"><span>= Prime pure</span><span>{eur(r['pure'])}</span></div>
  <div class="step">② Prime commerciale — frais et marge</div>
  <div class="row"><span>÷ (1 − frais {P['taux_frais']:.0%} − marge {P['taux_marge']:.0%})</span><span>÷ {1-P['taux_frais']-P['taux_marge']:.2f}</span></div>
  <div class="row sub"><span>= Prime commerciale</span><span>{eur(r['commerciale'])}</span></div>
  <div class="step">③ Bonus-malus — l'historique du conducteur</div>
  <div class="row"><span>÷ Rééquilibrage du portefeuille (CRM moyen pondéré)</span><span>÷ {P['facteur_crm']:.3f}</span></div>
  <div class="row"><span>× Recalage par âge (suivi S/P)</span><span>× {r['correction']:.3f}</span></div>
  <div class="row sub"><span>= Prime de référence (CRM 1,00)</span><span>{eur(r['reference'])}</span></div>
  <div class="row"><span>× CRM du conducteur</span><span>× {crm:.2f}</span></div>
  <div class="total"><span class="serif" style="font-size:1.15rem;color:{NAVY}">Prime annuelle hors taxes</span>
  <span class="v">{eur(r['finale'])}</span></div>
</div>
""",
            unsafe_allow_html=True,
        )
        delta = r["finale"] / (ref["finale"] * crm) - 1
        st.markdown(f"<p class='note' style='margin-top:.8rem'>Profil type au même CRM : {eur(ref['finale'] * crm)} · "
                    f"ce profil paie <b style='color:{CORAL if delta > 0 else NAVY}'>{delta*100:+.0f} %</b> "
                    f"de plus ou de moins. Frais et marge = hypothèses d'exemple.</p>",
                    unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 2. Zonier
# ---------------------------------------------------------------------------
# Relativités régionales du premier GLM (notebook, étape 10) et exposition en années
REL_REGION = {
    "R73": (0.777, 7014), "R41": (0.787, 8112), "R43": (0.927, 564), "R25": (0.928, 6653), "R53": (0.928, 27753),
    "R83": (0.940, 2322), "R24": (0.945, 102706), "R23": (0.953, 3177), "R52": (0.976, 21930), "R42": (0.981, 1209),
    "R11": (1.000, 30198), "R21": (1.006, 1204), "R31": (1.021, 11488), "R72": (1.028, 14316), "R54": (1.032, 11163),
    "R26": (1.044, 5023), "R91": (1.049, 14711), "R93": (1.098, 35749), "R82": (1.184, 45333), "R22": (1.187, 3573),
    "R94": (1.213, 1766), "R74": (1.356, 2396),
}
with t2:
    g, d = st.columns([1.25, 1], gap="large")
    with g:
        dz = pd.DataFrame([
            dict(code=k, region=REGIONS[k], zone=P["zones"][k], rel=v[0], expo=v[1]) for k, v in REL_REGION.items()
        ])
        # Carte dessinée à la main (polygones lon/lat) : aucun fond de carte externe nécessaire
        info = dz.set_index("code")
        fig = go.Figure()
        for feat in charger_carte()["features"]:
            code = feat["id"]
            if code not in info.index:
                continue
            row = info.loc[code]
            geom = feat["geometry"]
            polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
            for k, poly in enumerate(polys):
                ring = poly[0]
                fig.add_trace(go.Scatter(
                    x=[pt[0] for pt in ring], y=[pt[1] for pt in ring], mode="lines", fill="toself",
                    fillcolor=ZONE_COLORS[row["zone"]], line=dict(color="white", width=1.2),
                    hoveron="fills", showlegend=False,
                    text=f"<b>{row['region']}</b><br>{row['zone']} · relativité GLM {row['rel']:.2f}"
                         f"<br>exposition {row['expo']:,} ans".replace(",", " "),
                    hoverinfo="text",
                ))
        fig = layout(fig, 540)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1.45)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            "".join(f"<span style='display:inline-block;width:14px;height:14px;background:{c};border-radius:4px;"
                    f"margin:0 .35rem -2px 1rem'></span>{z}" for z, c in ZONE_COLORS.items())
            + "<span class='note'> · du moins risqué au plus risqué</span>", unsafe_allow_html=True)
    with d:
        st.markdown("### Comment le zonier est construit")
        st.markdown("""
<div class="lesson"><b>1. Mesurer.</b> Le premier GLM donne une relativité par région, « toutes choses égales par ailleurs »
(âge, véhicule, densité déjà pris en compte).</div>
<div class="lesson"><b>2. Regrouper.</b> Les 22 régions sont triées puis regroupées en 4 zones aux endroits où les
relativités font un saut. Les petites régions (Corse, Limousin…) n'ont plus de coefficient fragile à elles seules.</div>
<div class="lesson"><b>3. Valider.</b> Avec 4 zones au lieu de 22 régions, l'AIC baisse (219 471 → 219 455) :
modèle plus simple <i>et</i> légèrement meilleur.</div>
""", unsafe_allow_html=True)
        zt = pd.DataFrame({
            "Zone": ["Z1", "Z2", "Z3 (réf.)", "Z4"],
            "Fréquence": [F['C(Zone, Treatment("Z3"))[T.Z1]'], F['C(Zone, Treatment("Z3"))[T.Z2]'], 1.0,
                          F['C(Zone, Treatment("Z3"))[T.Z4]']],
            "Coût moyen": [C['C(Zone, Treatment("Z3"))[T.Z1]'], C['C(Zone, Treatment("Z3"))[T.Z2]'], 1.0,
                           C['C(Zone, Treatment("Z3"))[T.Z4]']],
        })
        st.dataframe(zt.style.format({"Fréquence": "×{:.2f}", "Coût moyen": "×{:.2f}"}), hide_index=True,
                     use_container_width=True)
        st.markdown("<p class='note'>En entreprise, le zonier se fait à la commune ou au code postal, avec lissage "
                    "entre voisins puis classification statistique. Ici : version simplifiée à la maille région.</p>",
                    unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 3. Bonus-malus et crédibilité
# ---------------------------------------------------------------------------
with t3:
    g, d = st.columns([1, 1], gap="large")
    with g:
        st.markdown("### Le CRM légal, année après année")
        st.markdown("<p class='note'>Règle française : ×0,95 par année sans sinistre responsable, ×1,25 par sinistre "
                    "responsable ; bornes 0,50 et 3,50 ; un malus revient à 1,00 après 2 ans sans sinistre.</p>", unsafe_allow_html=True)
        st.markdown("Saisis l'historique d'un conducteur qui démarre à 1,00 :")
        cols = st.columns(8)
        hist = [cols[i].number_input(f"An {i+1}", 0, 3, 1 if i == 2 else 0, key=f"h{i}") for i in range(8)]
        crm_v, path, sans_sinistre = 1.0, [1.0], 0
        for n in hist:
            crm_v = crm_v * 1.25 ** n if n > 0 else crm_v * 0.95
            crm_v = min(max(math.floor(crm_v * 100 + 1e-9) / 100, 0.50), 3.50)  # arrondi à 2 décimales par défaut
            sans_sinistre = 0 if n > 0 else sans_sinistre + 1
            if sans_sinistre >= 2 and crm_v > 1:  # retour à 1,00 après 2 ans sans sinistre
                crm_v = 1.0
            path.append(crm_v)
        fig = go.Figure(go.Scatter(x=list(range(9)), y=path, mode="lines+markers+text", line=dict(color=NAVY, width=3),
                                   marker=dict(size=9, color=[CORAL if h > 0 else NAVY for h in [0] + hist]),
                                   text=[f"{v:.2f}" for v in path], textposition="top center", cliponaxis=False))
        fig.add_hline(y=1, line_dash="dot", line_color=MUTED)
        st.plotly_chart(layout(fig, 300).update_xaxes(title="Année", dtick=1, range=[-0.4, 8.4])
                        .update_yaxes(title="CRM", range=[min(path) - 0.08, max(path) + 0.12]),
                        use_container_width=True)
    with d:
        st.markdown("### La crédibilité : croire l'historique, mais pas trop")
        st.markdown("<p class='note'>Modèle Poisson-Gamma sur 10 000 assurés réels, historique de 5 ans "
                    "<b>simulé</b> (la base ne couvre qu'une année). Facteur = (a + sinistres observés) / "
                    "(a + sinistres attendus), a = 2.</p>", unsafe_allow_html=True)
        cred = pd.DataFrame({"sin": [0, 1, 2, 3, 4, 5, 6],
                             "fac": [0.848, 1.255, 1.636, 1.976, 2.368, 2.532, 3.020],
                             "n": [7113, 2178, 554, 115, 30, 9, 1]})
        fig = go.Figure(go.Bar(x=cred["sin"], y=cred["fac"], marker_color=[NAVY] + [CORAL] * 6,
                               text=[f"×{v:.2f}" for v in cred["fac"]], textposition="outside",
                               customdata=cred["n"], hovertemplate="%{x} sinistre(s) : ×%{y:.2f}<br>%{customdata} assurés<extra></extra>"))
        fig.add_hline(y=1, line_dash="dot", line_color=MUTED)
        st.plotly_chart(layout(fig, 300).update_xaxes(title="Sinistres sur 5 ans", dtick=1)
                        .update_yaxes(title="Facteur de prime"), use_container_width=True)
    st.markdown("""
<div class="lesson"><b>Pourquoi le bonus-malus n'est pas dans le GLM.</b> Il résume l'historique de sinistres :
le mettre dans le GLM <i>et</i> l'appliquer ensuite ferait payer deux fois le même passé. Le GLM donne une prime
de référence (CRM 1,00), puis on multiplie par le CRM. Comme le CRM moyen du portefeuille est de 0,58, la prime de
référence est rééquilibrée (÷ 0,602) pour que le tarif reste à l'équilibre.</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 4. Suivi du portefeuille
# ---------------------------------------------------------------------------
with t4:
    k1, k2, k3 = st.columns(3)
    for col, v, l in [(k1, "0,70", "S/P global"), (k2, "59,9 M€", "charge prédite = charge réelle"),
                      (k3, "× 3,2", "écart de fréquence décile 1 → 10")]:
        col.markdown(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)
    st.write("")
    g, d = st.columns([1.2, 1], gap="large")
    with g:
        st.markdown("### S/P par âge : trois lectures")
        ages = ["18-21", "22-25", "26-30", "31-45", "46-60", "61-75", "76+"]
        fig = go.Figure()
        fig.add_bar(name="S/P réel", x=ages, y=[1.60, 0.41, 0.53, 0.64, 0.65, 0.77, 0.85], marker_color="#C9D6E8")
        fig.add_bar(name="S/P lissé (gros sinistres mutualisés)", x=ages, y=[0.45, 0.49, 0.58, 0.72, 0.79, 0.80, 0.81],
                    marker_color=NAVY)
        fig.add_bar(name="Après recalage", x=ages, y=[0.70] * 7, marker_color=CORAL)
        fig.add_hline(y=0.70, line_dash="dot", line_color=MUTED)
        st.plotly_chart(layout(fig, 360), use_container_width=True)
        st.markdown("""
<div class="lesson">Le 1,60 des 18-21 ans venait de quelques <b>gros sinistres</b> : une fois lissé, il tombe à 0,45.
Les jeunes étaient en fait <b>sur-tarifés</b> (le GLM et le CRM les chargent tous les deux). Un recalage par âge
ramène chaque tranche à 0,70.</div>""", unsafe_allow_html=True)
    with d:
        st.markdown("### Le modèle sait-il classer les risques ?")
        dec = list(range(1, 11))
        fig = go.Figure()
        fig.add_scatter(name="Prédite", x=dec, y=[.0425, .0518, .0575, .0626, .0675, .0730, .0793, .0873, .0988, .1377],
                        mode="lines+markers", line=dict(color=NAVY, width=3))
        fig.add_scatter(name="Observée", x=dec, y=[.0420, .0527, .0567, .0638, .0667, .0708, .0788, .0889, .1020, .1352],
                        mode="lines+markers", line=dict(color=CORAL, width=3, dash="dot"))
        st.plotly_chart(layout(fig, 360).update_xaxes(title="Décile de risque prédit", dtick=1)
                        .update_yaxes(title="Fréquence"), use_container_width=True)
        st.markdown("""
<div class="lesson">Prédit et observé se superposent dans chaque décile : le tarif est bien calibré et
segmente du simple au triple.</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 5. Défis du métier
# ---------------------------------------------------------------------------
with t5:
    g, d = st.columns([1.1, 1], gap="large")
    with g:
        st.markdown("### Inflation : que devient le S/P si on ne revalorise pas ?")
        a, b = st.columns(2)
        infl = a.slider("Inflation du coût des sinistres (/an)", 0.0, 10.0, 5.0, 0.5, format="%.1f %%") / 100
        reval = b.slider("Revalorisation du tarif (/an)", 0.0, 10.0, 0.0, 0.5, format="%.1f %%") / 100
        ans = list(range(0, 6))
        sp = [0.70 * ((1 + infl) / (1 + reval)) ** n for n in ans]
        fig = go.Figure(go.Scatter(x=ans, y=sp, mode="lines+markers+text", text=[f"{v:.2f}" for v in sp],
                                   textposition="top center", cliponaxis=False, line=dict(color=NAVY, width=3), fill="tozeroy",
                                   fillcolor="rgba(19,41,75,.06)"))
        fig.add_hline(y=0.75, line_color=CORAL, line_dash="dash",
                      annotation_text="Seuil de perte : S/P + 25 % de frais = 100 %", annotation_position="bottom right",
                      annotation_font_color=CORAL)
        st.plotly_chart(layout(fig, 330).update_xaxes(title="Années", dtick=1, range=[-0.3, 5.3])
                        .update_yaxes(range=[0.5, max(1.1, max(sp) + 0.08)]),
                        use_container_width=True)
    with d:
        st.markdown("### Machine learning contre GLM")
        m1, m2 = st.columns(2)
        m1.markdown('<div class="kpi"><div class="v">0,4773</div><div class="l">déviance test · GLM</div></div>',
                    unsafe_allow_html=True)
        m2.markdown('<div class="kpi"><div class="v">0,4755</div><div class="l">déviance test · gradient boosting</div></div>',
                    unsafe_allow_html=True)
        st.markdown("""
<div class="lesson">Sur 20 % de contrats jamais vus, le gradient boosting gagne <b>0,4 %</b> seulement.
Le GLM reste compétitif, lisible (relativités) et validable : le ML sert plutôt à repérer ce qu'il oublie.</div>
""", unsafe_allow_html=True)
    st.markdown("### Les autres défis")
    c1, c2, c3 = st.columns(3)
    c1.markdown("""<div class="card"><h4 class="serif">🌦️ Climat</h4>La RC auto est peu exposée, mais les garanties
dommages (grêle, inondations) voient fréquence et coûts monter. Le passé sous-estime le futur : scénarios
climatiques et zonier revu régulièrement.</div>""", unsafe_allow_html=True)
    c2.markdown("""<div class="card"><h4 class="serif">⚖️ Équité</h4>Depuis 2012 (arrêt Test-Achats), le sexe ne peut
plus servir à tarifer dans l'UE. Une variable « neutre » peut pourtant en être un proxy : il faut tester
les effets du tarif sur les groupes protégés.</div>""", unsafe_allow_html=True)
    c3.markdown("""<div class="card"><h4 class="serif">🏁 Concurrence</h4>Un tarif techniquement juste peut être trop cher
face au marché. On combine prime technique et élasticité-prix pour fixer le prix commercial, sans
sélection adverse.</div>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    "<p class='note'>Pamela Fagla · M2 Actuariat, ISUP (Sorbonne Université) · Données : freMTPL2freq & freMTPL2sev "
    "(CASdatasets, Dutang & Charpentier) · Paramètres issus du notebook <i>Tarification_Auto_de_A_a_Z</i>. "
    "Frais, marge et inflation sont des hypothèses d'illustration.</p>",
    unsafe_allow_html=True,
)
