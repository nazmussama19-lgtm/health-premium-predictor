# Estimation de prime d'assurance santé

Outil de tarification pour souscripteurs : un formulaire, un montant de prime
annuelle estimé, et le comparatif des trois formules pour le même profil.
Derrière l'interface, deux modèles de régression choisis selon l'âge de
l'assuré.

![Python](https://img.shields.io/badge/Python-3.10+-1F5F55)
![Streamlit](https://img.shields.io/badge/Streamlit-1.64-1F5F55)
![Licence](https://img.shields.io/badge/licence-MIT-1F5F55)

---

## Le problème et la démarche

Un premier modèle entraîné sur l'ensemble des 50 000 assurés atteignait un R²
de 0,98 — chiffre flatteur qui masquait un défaut rédhibitoire : **30 % des
estimations s'écartaient de plus de 10 % du montant réel**. Pour un tarificateur,
cela signifie surfacturer ou sous-facturer près d'un client sur trois.

L'analyse des résidus a montré que ces erreurs se concentraient presque
entièrement sur les assurés de 25 ans et moins. D'où la démarche retenue :

| Étape | Résultat |
|---|---|
| Modèle unique, tous âges | R² 0,981 — **30 %** d'erreurs > 10 % |
| Segment > 25 ans isolé | R² 0,995 — problème résolu |
| Segment ≤ 25 ans isolé | R² 0,60 — **73 %** d'erreurs > 10 % |
| Ajout du facteur de risque génétique (≤ 25 ans) | R² 0,989 — **2,1 %** d'erreurs |

Le blocage sur la tranche jeune ne venait pas de l'algorithme mais des données :
aucune combinaison de modèles ne rattrapait l'absence d'une variable explicative.
Il a fallu retourner vers le métier pour faire collecter le facteur de risque
génétique. C'est cet ajout, et non un réglage d'hyperparamètres, qui a débloqué
le segment.

### Performances retenues

| Segment | Modèle | R² (test) | Estimations à moins de 10 % |
|---|---|---|---|
| ≤ 25 ans | Régression linéaire | 0,9887 | 97,9 % |
| > 25 ans | XGBoost | 0,9971 | 99,7 % |

Les deux objectifs du cahier des charges sont atteints : précision supérieure à
97 %, et au moins 95 % des écarts sous la barre des 10 %.

---

## Démarrage

```bash
pip install -r requirements.txt
```

```bash
streamlit run main.py
```

L'application s'ouvre sur `http://localhost:8501`.

---

## Vérification du pipeline

L'application refait le prétraitement des notebooks à la main : encodage
ordinal, variables indicatrices, score de risque médical, mise à l'échelle.
Une erreur à cette étape fausserait les prédictions sans rien casser
visiblement. Le script de validation rejoue donc le pipeline applicatif
complet sur les jeux de test d'origine et compare aux métriques des notebooks :

```bash
python tests/validate_pipeline.py
```

```
[young]  6026 lignes de test (attendu 6026)
  R2                        0.9887   (notebook 0.9887)
  erreurs > 10 %            2.14 % (notebook 2.14 %)
[rest]   8947 lignes de test (attendu 8947)
  R2                        0.9971   (notebook 0.9971)
  erreurs > 10 %            0.32 % (notebook 0.32 %)
```

---

## Structure

```
.
├── main.py                  Interface Streamlit (français)
├── prediction_helper.py     Prétraitement, mise à l'échelle, routage
├── assets/styles.css        Feuille de style
├── artifacts/               Modèles et scalers entraînés
├── notebooks/               Analyse exploratoire et entraînement
├── data/                    Jeux de données
└── tests/                   Validation du pipeline
```

---

## Points techniques

**Le scaler attend une colonne que les modèles n'utilisent pas.** À
l'entraînement, `income_level` était mise à l'échelle avec les autres variables
numériques, puis retirée pour cause de multicolinéarité (VIF > 12). Le scaler
sérialisé en garde la trace : `handle_scaling()` doit donc créer cette colonne
avant d'appeler `transform()`, puis la supprimer. L'omettre déclenche une erreur
sur les noms de variables attendus.

**L'ordre des colonnes est contraint.** XGBoost ne vérifie pas les noms au
moment de la prédiction : une permutation donnerait des montants faux sans la
moindre erreur. `EXPECTED_COLUMNS` fige cet ordre et `handle_scaling()` le
réapplique en sortie.

**Le score de risque médical est normalisé sur 14.** Le minimum et le maximum
observés à l'entraînement n'ont pas été sérialisés avec le modèle ; la borne
haute (hypertension + maladie cardiaque) est donc codée en dur.

**Le risque génétique n'a aucun effet au-delà de 25 ans.** La variable a été
ajoutée au segment des plus de 25 ans avec une valeur nulle partout, uniquement
pour aligner le format d'entrée des deux modèles. L'interface le signale
explicitement plutôt que de laisser croire à une prise en compte.

**Format des artefacts.** Les modèles ont été entraînés sous scikit-learn 1.3.
Les objets scikit-learn se rechargent sans difficulté sous 1.7, mais le pickle
XGBoost déclenchait un avertissement de compatibilité et n'offre aucune garantie
entre versions majeures. Le modèle a donc été réexporté au format natif
(`model_rest.json`) ; la conversion a été vérifiée sur 2 000 tirages, écart
maximal nul. Le pickle d'origine est conservé à titre de référence.

---

## Limites

- Les montants sont exprimés en **roupies indiennes** et les revenus en lakhs
  (1 lakh = 100 000 ₹) : le modèle a été entraîné sur un portefeuille indien.
  Les libellés sont traduits, pas les ordres de grandeur.
- Le modèle des 25 ans et moins étant une régression linéaire, des saisies très
  éloignées des données d'entraînement peuvent produire un montant négatif.
  `predict()` ramène le résultat à zéro le cas échéant.
- Aucune ré-estimation périodique n'est prévue : les modèles reflètent le
  portefeuille au moment de leur entraînement.

---

## Licence

MIT.
