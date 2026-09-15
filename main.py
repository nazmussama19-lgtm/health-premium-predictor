"""Interface de tarification à destination des souscripteurs.

L'interface est en français, les modèles ont été entraînés sur un jeu de
données indien : les libellés affichés sont traduits vers les modalités
d'origine juste avant l'appel au modèle (cf. dictionnaires ci-dessous).
"""

from pathlib import Path

import streamlit as st

from content import CONTEXTE, GUIDE
from prediction_helper import YOUNG_AGE_CUTOFF, predict, predict_all_plans

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title="Estimation de prime santé",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------------------------------
# Traductions : libellé affiché -> modalité attendue par le modèle
# --------------------------------------------------------------------------

GENRES = {"Homme": "Male", "Femme": "Female"}

SITUATIONS = {"Célibataire": "Unmarried", "Marié(e)": "Married"}

CORPULENCES = {
    "Normale": "Normal",
    "Surpoids": "Overweight",
    "Obésité": "Obesity",
    "Insuffisance pondérale": "Underweight",
}

TABAGISMES = {
    "Non-fumeur": "No Smoking",
    "Occasionnel": "Occasional",
    "Régulier": "Regular",
}

EMPLOIS = {
    "Salarié(e)": "Salaried",
    "Indépendant(e)": "Self-Employed",
    "Freelance": "Freelancer",
}

REGIONS = {
    "Nord-Ouest": "Northwest",
    "Nord-Est": "Northeast",
    "Sud-Ouest": "Southwest",
    "Sud-Est": "Southeast",
}

ANTECEDENTS = {
    "Aucun": "No Disease",
    "Diabète": "Diabetes",
    "Hypertension": "High blood pressure",
    "Troubles thyroïdiens": "Thyroid",
    "Maladie cardiaque": "Heart disease",
    "Diabète et hypertension": "Diabetes & High blood pressure",
    "Diabète et troubles thyroïdiens": "Diabetes & Thyroid",
    "Diabète et maladie cardiaque": "Diabetes & Heart disease",
    "Hypertension et maladie cardiaque": "High blood pressure & Heart disease",
}

FORMULES = {"Bronze": "Bronze", "Argent": "Silver", "Or": "Gold"}

# Part des estimations à moins de 10 % du montant réel, mesurée sur le jeu
# de test de chaque segment (cf. tests/validate_pipeline.py).
FIABILITE = {"young": 97.9, "rest": 99.7}


def format_montant(valeur: int) -> str:
    """Séparateur de milliers à la française (espace fine insécable)."""
    return f"{valeur:,}".replace(",", " ")


def charger_styles() -> str:
    """Feuille de style de l'application.

    Volontairement non mise en cache : le fichier fait quelques kilo-octets
    et le cache empecherait de voir les retouches sans relancer le serveur.
    """
    return (ASSETS / "styles.css").read_text(encoding="utf-8")


def titre_section(numero: str, titre: str, indice: str = "", premier: bool = False):
    classe = "section-head is-first" if premier else "section-head"
    st.markdown(
        f"""
        <div class="{classe}">
          <span class="section-num">{numero}</span>
          <span class="section-title">{titre}</span>
          <span class="section-hint">{indice}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Rendu
# --------------------------------------------------------------------------

st.markdown(f"<style>{charger_styles()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="masthead">
      <div class="masthead-top">
        <span class="eyebrow">Outil de souscription &middot; Usage interne</span>
        <span class="eyebrow">Modèle v1.0</span>
      </div>
      <h1>Estimation de <em>prime santé</em></h1>
      <p>
        Renseignez le profil de l'assuré pour obtenir une estimation immédiate
        de la prime annuelle. Le calcul mobilise deux modèles distincts selon
        la tranche d'âge, l'un des deux intégrant le facteur de risque génétique.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

onglet_tarification, onglet_contexte, onglet_guide = st.tabs(
    ["Tarification", "Contexte et méthode", "Guide du souscripteur"]
)

with onglet_tarification:
    colonne_saisie, colonne_resultat = st.columns([1.32, 1], gap="large")

    with colonne_saisie:
        with st.form("tarification", border=False):
            titre_section("01", "Profil de l'assuré", "4 champs", premier=True)
            l1 = st.columns(2)
            with l1[0]:
                age = st.number_input("Âge", min_value=18, max_value=100, value=32, step=1)
            with l1[1]:
                personnes_a_charge = st.number_input(
                    "Personnes à charge", min_value=0, max_value=20, value=0, step=1
                )
            l2 = st.columns(2)
            with l2[0]:
                genre = st.selectbox("Genre", list(GENRES))
            with l2[1]:
                situation = st.selectbox("Situation familiale", list(SITUATIONS))

            titre_section("02", "Situation professionnelle et revenus", "2 champs")
            l3 = st.columns(2)
            with l3[0]:
                emploi = st.selectbox("Statut professionnel", list(EMPLOIS))
            with l3[1]:
                revenu = st.number_input(
                    "Revenu annuel (lakhs)",
                    min_value=0,
                    max_value=200,
                    value=20,
                    step=1,
                    help="1 lakh = 100 000 roupies indiennes.",
                )

            titre_section("03", "Santé et habitudes de vie", "4 champs")
            l4 = st.columns(2)
            with l4[0]:
                corpulence = st.selectbox("Corpulence (IMC)", list(CORPULENCES))
            with l4[1]:
                tabagisme = st.selectbox("Tabagisme", list(TABAGISMES))
            antecedents = st.selectbox("Antécédents médicaux", list(ANTECEDENTS))
            risque_genetique = st.slider(
                "Facteur de risque génétique",
                min_value=0,
                max_value=5,
                value=0,
                help=(
                    "Score de 0 (aucun antécédent familial) à 5 (antécédents lourds). "
                    "Ce facteur n'influe que sur les profils de 25 ans ou moins."
                ),
            )

            titre_section("04", "Contrat", "2 champs")
            l5 = st.columns(2)
            with l5[0]:
                formule = st.selectbox("Formule souscrite", list(FORMULES))
            with l5[1]:
                region = st.selectbox("Région de résidence", list(REGIONS))

            calculer = st.form_submit_button("Calculer la prime annuelle")

    with colonne_resultat:
        if not calculer:
            st.markdown(
                """
                <div class="panel is-empty">
                  <span class="glyph">&#9671;</span>
                  <p>
                    Complétez le formulaire puis lancez le calcul pour afficher
                    l'estimation et le comparatif des trois formules.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            saisie = {
                "Age": age,
                "Number of Dependants": personnes_a_charge,
                "Income in Lakhs": revenu,
                "Genetical Risk": risque_genetique,
                "Insurance Plan": FORMULES[formule],
                "Employment Status": EMPLOIS[emploi],
                "Gender": GENRES[genre],
                "Marital Status": SITUATIONS[situation],
                "BMI Category": CORPULENCES[corpulence],
                "Smoking Status": TABAGISMES[tabagisme],
                "Region": REGIONS[region],
                "Medical History": ANTECEDENTS[antecedents],
            }

            prime = predict(saisie)
            par_formule = predict_all_plans(saisie)
            maximum = max(par_formule.values()) or 1

            segment = "young" if age <= YOUNG_AGE_CUTOFF else "rest"
            libelle_segment = (
                f"Modèle {YOUNG_AGE_CUTOFF} ans et moins"
                if segment == "young"
                else f"Modèle plus de {YOUNG_AGE_CUTOFF} ans"
            )

            lignes = []
            for libelle_fr, valeur_modele in FORMULES.items():
                montant = par_formule[valeur_modele]
                largeur = montant / maximum * 100
                actif = " is-active" if valeur_modele == FORMULES[formule] else ""
                lignes.append(
                    f'<div class="cmp-row{actif}" data-plan="{libelle_fr}">'
                    f'<span class="cmp-name">{libelle_fr}</span>'
                    f'<span class="cmp-track"><span class="cmp-fill" style="width:{largeur:.1f}%"></span></span>'
                    f'<span class="cmp-val">{format_montant(montant)}&nbsp;&#8377;</span>'
                    f"</div>"
                )

            # Virgule decimale, separateur francais.
            fiabilite = f"{FIABILITE[segment]:.1f}".replace(".", ",")

            note_genetique = (
                ""
                if segment == "young"
                else (
                    " Le facteur de risque génétique n'entre pas dans le calcul "
                    "au-delà de 25 ans : il était absent des données d'entraînement "
                    "de ce segment."
                )
            )

            st.markdown(
                f"""
                <div class="panel">
                  <span class="badge"><span class="dot"></span>{libelle_segment}</span>
                  <div class="result-label">Prime annuelle estimée</div>
                  <div class="result-value"><span class="cur">&#8377;</span>{format_montant(prime)}</div>
                  <div class="result-sub">
                    soit environ <strong>{format_montant(round(prime / 12))}&nbsp;&#8377;</strong> par mois
                  </div>
                  <div class="rule"></div>
                  <div class="cmp-title">Comparatif des formules</div>
                  {"".join(lignes)}
                  <div class="note">
                    <span class="mark">i</span>
                    <span>
                      Sur ce segment, <strong>{fiabilite}&nbsp;% des estimations</strong>
                      s'écartent de moins de 10&nbsp;% du montant réellement constaté.
                      {note_genetique}
                    </span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with onglet_contexte:
    st.markdown(CONTEXTE, unsafe_allow_html=True)

with onglet_guide:
    st.markdown(GUIDE, unsafe_allow_html=True)

st.markdown(
    """
    <div class="colophon">
      <span><strong>Segmentation</strong> &nbsp;deux modèles, bascule à 25 ans</span>
      <span><strong>Algorithmes</strong> &nbsp;régression linéaire &middot; XGBoost</span>
      <span><strong>Montants</strong> &nbsp;roupies indiennes</span>
    </div>
    """,
    unsafe_allow_html=True,
)
