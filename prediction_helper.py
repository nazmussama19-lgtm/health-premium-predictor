"""Pretraitement des saisies et routage vers le bon modele de prime.

Deux modeles coexistent : un pour les assures de 25 ans ou moins
(regression lineaire, entrainee avec la variable risque genetique) et un
pour les plus de 25 ans (XGBoost). Le decoupage vient de l'analyse des
erreurs : sans segmentation, 30 % des predictions derapaient de plus de
10 %, presque toutes sur la tranche jeune.

Les valeurs attendues ici sont celles du jeu d'entrainement (en anglais).
La traduction depuis l'interface est faite en amont, dans main.py.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import joblib
import pandas as pd
import xgboost as xgb

# Les artefacts ont ete serialises avec scikit-learn 1.3 ; on les recharge
# avec une version plus recente. Les objets concernes (LinearRegression,
# MinMaxScaler) ne stockent que des tableaux numpy, la relecture est sure.
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.base")

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

model_young = joblib.load(ARTIFACTS_DIR / "model_young.joblib")
scaler_young = joblib.load(ARTIFACTS_DIR / "scaler_young.joblib")
scaler_rest = joblib.load(ARTIFACTS_DIR / "scaler_rest.joblib")

# Le modele XGBoost est charge depuis son format natif plutot que depuis le
# pickle d'origine : le pickle declenche un avertissement de version et n'est
# pas garanti compatible entre versions majeures. Conversion verifiee a la
# prediction pres (cf. README).
model_rest = xgb.XGBRegressor()
model_rest.load_model(ARTIFACTS_DIR / "model_rest.json")

# Age pivot entre les deux modeles (cf. notebooks/data_segmentation.ipynb).
YOUNG_AGE_CUTOFF = 25

# Ordre impose par les modeles : toute permutation fausse silencieusement
# les predictions de XGBoost.
EXPECTED_COLUMNS = [
    "age",
    "number_of_dependants",
    "income_lakhs",
    "insurance_plan",
    "genetical_risk",
    "normalized_risk_score",
    "gender_Male",
    "region_Northwest",
    "region_Southeast",
    "region_Southwest",
    "marital_status_Unmarried",
    "bmi_category_Obesity",
    "bmi_category_Overweight",
    "bmi_category_Underweight",
    "smoking_status_Occasional",
    "smoking_status_Regular",
    "employment_status_Salaried",
    "employment_status_Self-Employed",
]

INSURANCE_PLAN_ENCODING = {"Bronze": 1, "Silver": 2, "Gold": 3}

RISK_SCORES = {
    "diabetes": 6,
    "heart disease": 8,
    "high blood pressure": 6,
    "thyroid": 5,
    "no disease": 0,
    "none": 0,
}

# Combinaison la plus lourde du jeu d'entrainement : hypertension (6) +
# maladie cardiaque (8). Le min/max n'ayant pas ete serialise avec le
# modele, il est fige ici pour reproduire la normalisation d'origine.
MAX_RISK_SCORE = 14


def calculate_normalized_risk(medical_history: str) -> float:
    """Ramene les antecedents medicaux sur une echelle de 0 a 1."""
    diseases = medical_history.lower().split(" & ")
    total = sum(RISK_SCORES.get(disease, 0) for disease in diseases)
    return total / MAX_RISK_SCORE


def preprocess_input(input_dict: dict) -> pd.DataFrame:
    """Construit la ligne de features attendue par les modeles."""
    df = pd.DataFrame(0.0, columns=EXPECTED_COLUMNS, index=[0])

    df["age"] = input_dict["Age"]
    df["number_of_dependants"] = input_dict["Number of Dependants"]
    df["income_lakhs"] = input_dict["Income in Lakhs"]
    df["genetical_risk"] = input_dict["Genetical Risk"]
    df["insurance_plan"] = INSURANCE_PLAN_ENCODING[input_dict["Insurance Plan"]]

    # Modalites de reference (drop_first a l'entrainement) : Female,
    # Northeast, Married, Normal, No Smoking, Freelancer. Elles restent a 0.
    if input_dict["Gender"] == "Male":
        df["gender_Male"] = 1
    if input_dict["Region"] in ("Northwest", "Southeast", "Southwest"):
        df[f"region_{input_dict['Region']}"] = 1
    if input_dict["Marital Status"] == "Unmarried":
        df["marital_status_Unmarried"] = 1
    if input_dict["BMI Category"] in ("Obesity", "Overweight", "Underweight"):
        df[f"bmi_category_{input_dict['BMI Category']}"] = 1
    if input_dict["Smoking Status"] in ("Occasional", "Regular"):
        df[f"smoking_status_{input_dict['Smoking Status']}"] = 1
    if input_dict["Employment Status"] in ("Salaried", "Self-Employed"):
        df[f"employment_status_{input_dict['Employment Status']}"] = 1

    df["normalized_risk_score"] = calculate_normalized_risk(
        input_dict["Medical History"]
    )

    return handle_scaling(input_dict["Age"], df)


def handle_scaling(age: int, df: pd.DataFrame) -> pd.DataFrame:
    """Applique le MinMaxScaler du segment correspondant.

    Subtilite heritee des notebooks : le scaler a ete ajuste sur six
    colonnes dont income_level, que les modeles n'utilisent pas (VIF trop
    eleve, elle a ete retiree apres le scaling). Il faut donc la fournir
    pour que transform() accepte l'entree, puis la retirer.
    """
    scaler_object = scaler_young if age <= YOUNG_AGE_CUTOFF else scaler_rest
    scaler = scaler_object["scaler"]
    cols_to_scale = scaler_object["cols_to_scale"]

    df["income_level"] = None
    df[cols_to_scale] = scaler.transform(df[cols_to_scale])
    df = df.drop("income_level", axis="columns")

    return df[EXPECTED_COLUMNS]


def predict(input_dict: dict) -> int:
    """Renvoie la prime annuelle estimee, en roupies."""
    input_df = preprocess_input(input_dict)

    if input_dict["Age"] <= YOUNG_AGE_CUTOFF:
        prediction = model_young.predict(input_df)
    else:
        prediction = model_rest.predict(input_df)

    # La regression lineaire peut sortir un montant negatif sur des
    # combinaisons de saisies absentes du jeu d'entrainement.
    return max(0, int(round(float(prediction[0]))))


def predict_all_plans(input_dict: dict) -> dict:
    """Meme profil, les trois formules. Utile pour comparer a l'ecran."""
    return {
        plan: predict({**input_dict, "Insurance Plan": plan})
        for plan in INSURANCE_PLAN_ENCODING
    }


def get_segment(age: int) -> str:
    """Identifiant du modele mobilise, pour affichage."""
    return "young" if age <= YOUNG_AGE_CUTOFF else "rest"
