"""Rejoue le pipeline de l'application sur les jeux de test des notebooks.

L'objectif est de verifier que prediction_helper.predict() reproduit bien
les performances mesurees a l'entrainement. Un ecart ici signalerait une
erreur de pretraitement dans l'application, pas dans le modele.

Lancer depuis la racine du projet :  python tests/validate_pipeline.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prediction_helper import predict  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Cibles issues des notebooks (cellules d'evaluation finales).
TARGETS = {
    "young": {"rows": 6026, "r2": 0.9887, "extreme_pct": 2.14},
    "rest": {"rows": 8947, "r2": 0.9971, "extreme_pct": 0.32},
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage identique a celui des notebooks."""
    df.columns = df.columns.str.replace(" ", "_").str.lower()
    df = df.dropna().drop_duplicates()
    df["number_of_dependants"] = df["number_of_dependants"].abs()
    df = df[df.age <= 100]
    df = df[df.income_lakhs <= df.income_lakhs.quantile(0.999)].copy()
    df["smoking_status"] = df["smoking_status"].replace(
        {
            "Not Smoking": "No Smoking",
            "Does Not Smoke": "No Smoking",
            "Smoking=0": "No Smoking",
        }
    )
    return df


def to_input_dict(row: pd.Series) -> dict:
    return {
        "Age": int(row.age),
        "Number of Dependants": int(row.number_of_dependants),
        "Income in Lakhs": int(row.income_lakhs),
        "Genetical Risk": int(row.genetical_risk),
        "Insurance Plan": row.insurance_plan,
        "Employment Status": row.employment_status,
        "Gender": row.gender,
        "Marital Status": row.marital_status,
        "BMI Category": row.bmi_category,
        "Smoking Status": row.smoking_status,
        "Region": row.region,
        "Medical History": row.medical_history,
    }


def evaluate(segment: str, df: pd.DataFrame) -> bool:
    df = clean(df)

    # Meme decoupage que les notebooks : seul le jeu de test est evalue.
    y = df["annual_premium_amount"]
    _, test_idx = train_test_split(df.index, test_size=0.30, random_state=10)
    test = df.loc[test_idx]

    predictions = np.array([predict(to_input_dict(r)) for r in test.itertuples()])
    actual = y.loc[test_idx].to_numpy()

    r2 = r2_score(actual, predictions)
    diff_pct = np.abs((predictions - actual) / actual) * 100
    extreme_pct = (diff_pct > 10).mean() * 100

    target = TARGETS[segment]
    ok = (
        len(test) == target["rows"]
        and abs(r2 - target["r2"]) < 0.01
        and abs(extreme_pct - target["extreme_pct"]) < 1.0
    )

    print(f"\n[{segment}]  {len(test)} lignes de test (attendu {target['rows']})")
    print(f"  R2                        {r2:.4f}   (notebook {target['r2']:.4f})")
    print(f"  erreurs > 10 %            {extreme_pct:.2f} % (notebook {target['extreme_pct']:.2f} %)")
    print(f"  erreurs <= 10 %           {100 - extreme_pct:.2f} % (cible >= 95 %)")
    print(f"  ecart median              {np.median(diff_pct):.2f} %")
    print(f"  -> {'CONFORME' if ok else 'ECART DETECTE'}")
    return ok


def main() -> int:
    young = pd.read_excel(DATA / "premiums_young_with_gr.xlsx")

    # Le modele >25 ans a ete entraine avec genetical_risk a zero partout :
    # la variable existait pour aligner les schemas, pas pour etre utilisee.
    rest = pd.read_excel(DATA / "premiums_rest.xlsx")
    rest["Genetical_Risk"] = 0

    results = [evaluate("young", young), evaluate("rest", rest)]

    print("\n" + "=" * 52)
    if all(results):
        print("Pipeline applicatif conforme aux notebooks.")
        return 0
    print("Le pipeline applicatif s'ecarte des notebooks.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
