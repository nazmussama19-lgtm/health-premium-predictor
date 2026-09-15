"""Contenu des pages de documentation affichées dans l'application.

Séparé de main.py pour que le fichier d'interface reste lisible : ici, du
texte et de la mise en forme, aucune logique.
"""


def _html(source: str) -> str:
    """Retire l'indentation de chaque ligne du balisage.

    Markdown transforme toute ligne indentée de quatre espaces qui suit une
    ligne vide en bloc de code : sans ce nettoyage, les sections espacées
    s'afficheraient sous forme de balises littérales. Le source reste donc
    indenté pour rester lisible, et l'indentation saute au rendu.
    """
    return "\n".join(ligne.lstrip() for ligne in source.split("\n"))


CONTEXTE = _html("""
<div class="doc">

  <p class="doc-lede">
    Jusqu'ici, l'estimation d'une prime santé reposait sur le jugement du
    souscripteur et sur des grilles tarifaires manuelles. Cet outil produit
    la même estimation en quelques secondes, à partir de douze caractéristiques
    de l'assuré, et affiche ce que donneraient les deux autres formules.
  </p>

  <h2>Le cahier des charges</h2>
  <p>
    Deux exigences avaient été posées au départ, et la seconde s'est révélée
    bien plus contraignante que la première :
  </p>
  <ul>
    <li>une <strong>précision supérieure à 97 %</strong> ;</li>
    <li>sur <strong>au moins 95 % des dossiers</strong>, un écart entre montant
        estimé et montant réel <strong>inférieur à 10 %</strong>.</li>
  </ul>
  <p>
    La nuance compte. Un modèle peut être globalement très juste tout en se
    trompant lourdement sur une partie de la clientèle — et c'est exactement ce
    qui s'est produit.
  </p>

  <h2>Les données</h2>
  <p>
    50 000 contrats, treize variables : âge, genre, région, situation familiale,
    personnes à charge, corpulence, tabagisme, statut professionnel, niveau et
    montant de revenu, antécédents médicaux, formule souscrite, prime annuelle.
  </p>
  <p>
    Le nettoyage a révélé les défauts habituels d'un export de production :
    des âges impossibles (jusqu'à 356 ans), des nombres de personnes à charge
    négatifs, et un champ tabagisme renseigné de quatre façons différentes pour
    dire la même chose — <em>No Smoking</em>, <em>Not Smoking</em>,
    <em>Does Not Smoke</em>, <em>Smoking=0</em>. Les revenus très élevés, eux,
    ont été conservés : la méthode classique de détection des valeurs aberrantes
    en écartait 3 559, dont l'immense majorité correspondait à des dossiers
    parfaitement légitimes.
  </p>

  <h2>Pourquoi deux modèles</h2>

  <div class="steps">

    <div class="step">
      <div class="step-title">Un modèle unique sur l'ensemble du portefeuille</div>
      <div class="step-body">
        Résultat en apparence excellent, mais près d'un dossier sur trois
        se retrouvait mal tarifé au-delà du seuil de 10 %. Inexploitable
        en production.
        <br><span class="step-figure is-bad">30 % d'erreurs supérieures à 10 %</span>
      </div>
    </div>

    <div class="step">
      <div class="step-title">L'analyse des résidus désigne un coupable</div>
      <div class="step-body">
        En remontant aux caractéristiques des dossiers mal estimés, une
        variable ressort nettement : l'âge. Les erreurs se concentrent sur
        les <strong>assurés de 25 ans et moins</strong>.
      </div>
    </div>

    <div class="step is-resolved">
      <div class="step-title">Segment des plus de 25 ans</div>
      <div class="step-body">
        Traité séparément, ce segment se modélise sans difficulté.
        <br><span class="step-figure is-good">0,3 % d'erreurs supérieures à 10 %</span>
      </div>
    </div>

    <div class="step">
      <div class="step-title">Segment des 25 ans et moins : le mur</div>
      <div class="step-body">
        Isoler la tranche jeune ne suffit pas. Régression linéaire, XGBoost,
        optimisation des hyperparamètres : rien ne dépasse un R² de 0,60.
        Le problème ne venait pas de l'algorithme.
        <br><span class="step-figure is-bad">73 % d'erreurs supérieures à 10 %</span>
      </div>
    </div>

    <div class="step is-resolved">
      <div class="step-title">Retour vers le métier</div>
      <div class="step-body">
        Le diagnostic posé était qu'il manquait une information explicative,
        pas un réglage. Une variable supplémentaire a donc été collectée :
        le <strong>facteur de risque génétique</strong>. Son ajout a débloqué
        le segment d'un coup.
        <br><span class="step-figure is-good">2,1 % d'erreurs supérieures à 10 %</span>
      </div>
    </div>

  </div>

  <h2>Ce que fait l'outil aujourd'hui</h2>
  <p>
    Selon l'âge saisi, l'application mobilise l'un ou l'autre des deux modèles.
    En dessous de 26 ans, une régression linéaire intégrant le risque génétique.
    Au-delà, un modèle XGBoost. Le souscripteur n'a rien à choisir : la bascule
    est automatique et le modèle retenu est indiqué au-dessus du montant.
  </p>

  <div class="metric-grid">
    <div class="metric">
      <div class="metric-value is-accent">98,9 %</div>
      <div class="metric-label">Précision (R²)<br>segment 25 ans et moins</div>
    </div>
    <div class="metric">
      <div class="metric-value is-accent">99,7 %</div>
      <div class="metric-label">Précision (R²)<br>segment plus de 25 ans</div>
    </div>
    <div class="metric">
      <div class="metric-value">97,9 %</div>
      <div class="metric-label">Estimations à moins de 10 %<br>segment 25 ans et moins</div>
    </div>
    <div class="metric">
      <div class="metric-value">99,7 %</div>
      <div class="metric-label">Estimations à moins de 10 %<br>segment plus de 25 ans</div>
    </div>
  </div>

  <p>
    Les deux exigences du cahier des charges sont donc satisfaites sur les deux
    segments. Ces chiffres sont mesurés sur des dossiers que les modèles n'ont
    jamais vus pendant leur entraînement.
  </p>

  <h2>Ce que l'outil ne fait pas</h2>

  <div class="callout">
    <div class="callout-title">À garder en tête</div>
    <ul>
      <li>
        <strong>Le risque génétique n'a aucun effet au-delà de 25 ans.</strong>
        La variable n'existait pas dans les données d'entraînement de ce
        segment ; elle n'a été ajoutée que pour aligner le format d'entrée des
        deux modèles. Saisir 5 plutôt que 0 pour un assuré de 40 ans ne change
        rien au montant.
      </li>
      <li>
        <strong>Les montants sont en roupies indiennes</strong> et les revenus
        exprimés en lakhs (1 lakh = 100 000 ₹). Les modèles ont été entraînés
        sur un portefeuille indien : l'interface est traduite, pas les ordres
        de grandeur.
      </li>
      <li>
        <strong>Les modèles ne se mettent pas à jour tout seuls.</strong> Ils
        reflètent le portefeuille au moment de leur entraînement. Un changement
        de grille tarifaire ou d'assiette de clientèle impose un réentraînement.
      </li>
      <li>
        <strong>L'estimation ne remplace pas la décision de souscription.</strong>
        Elle donne un point de départ chiffré, pas un tarif contractuel.
      </li>
    </ul>
  </div>

</div>
""")


GUIDE = _html("""
<div class="doc">

  <p class="doc-lede">
    Remplissez les quatre sections du formulaire, lancez le calcul, lisez le
    montant. Cette page détaille ce que recouvre chaque champ et comment
    interpréter le résultat.
  </p>

  <h2>Les champs à renseigner</h2>

  <div class="fields">

    <div class="field">
      <div class="field-name">Âge</div>
      <div class="field-desc">
        Âge de l'assuré, entre 18 et 100 ans. <em>C'est ce champ qui détermine
        lequel des deux modèles est utilisé : la bascule se fait à 26 ans.</em>
      </div>
    </div>

    <div class="field">
      <div class="field-name">Personnes à charge</div>
      <div class="field-desc">Nombre de personnes rattachées au contrat.</div>
    </div>

    <div class="field">
      <div class="field-name">Genre, situation familiale</div>
      <div class="field-desc">
        Tels que déclarés au dossier. <em>Leur poids dans le calcul reste
        faible.</em>
      </div>
    </div>

    <div class="field">
      <div class="field-name">Statut professionnel</div>
      <div class="field-desc">Salarié, indépendant ou freelance.</div>
    </div>

    <div class="field">
      <div class="field-name">Revenu annuel</div>
      <div class="field-desc">
        En lakhs de roupies. <em>1 lakh = 100 000 ₹ ; un revenu de 20 lakhs
        correspond donc à 2 000 000 ₹ par an.</em>
      </div>
    </div>

    <div class="field">
      <div class="field-name">Corpulence</div>
      <div class="field-desc">
        Catégorie d'indice de masse corporelle : insuffisance pondérale,
        normale, surpoids ou obésité.
      </div>
    </div>

    <div class="field">
      <div class="field-name">Tabagisme</div>
      <div class="field-desc">
        Non-fumeur, occasionnel ou régulier. <em>L'un des facteurs les plus
        lourds du calcul.</em>
      </div>
    </div>

    <div class="field">
      <div class="field-name">Antécédents médicaux</div>
      <div class="field-desc">
        Une pathologie ou une combinaison de deux. Chacune porte un poids de
        risque différent : maladie cardiaque, puis diabète et hypertension à
        égalité, puis troubles thyroïdiens.
      </div>
    </div>

    <div class="field">
      <div class="field-name">Facteur de risque génétique</div>
      <div class="field-desc">
        Score de 0 à 5 établi à partir des antécédents familiaux, où 0 signifie
        aucun antécédent connu. <em>Ce facteur n'entre dans le calcul que pour
        les assurés de 25 ans et moins.</em>
      </div>
    </div>

    <div class="field">
      <div class="field-name">Formule souscrite</div>
      <div class="field-desc">
        Bronze, Argent ou Or. <em>Le résultat affiche de toute façon les trois
        montants : ce choix ne sert qu'à désigner celui qui est mis en avant.</em>
      </div>
    </div>

    <div class="field">
      <div class="field-name">Région de résidence</div>
      <div class="field-desc">Nord-Ouest, Nord-Est, Sud-Ouest ou Sud-Est.</div>
    </div>

  </div>

  <h2>Lire le résultat</h2>

  <h3>Le bandeau du haut</h3>
  <p>
    Il indique lequel des deux modèles a produit l'estimation. C'est une
    information utile : le segment des 25 ans et moins est légèrement moins
    fiable que l'autre, et le risque génétique n'a d'effet que sur lui.
  </p>

  <h3>Le montant</h3>
  <p>
    Prime annuelle estimée, avec son équivalent mensuel en dessous. Ce montant
    est une estimation statistique, pas un tarif contractuel.
  </p>

  <h3>Le comparatif des formules</h3>
  <p>
    Les trois montants correspondent au <strong>même profil d'assuré</strong>,
    seule la formule change. La barre pleine et colorée désigne celle que vous
    avez sélectionnée. C'est le moyen le plus rapide de chiffrer un passage
    d'une formule à une autre pendant un entretien.
  </p>

  <h3>La note de fiabilité</h3>
  <p>
    Elle rappelle la proportion de dossiers, sur le segment concerné, pour
    lesquels l'estimation tombe à moins de 10 % du montant réel. Autrement dit :
    à quel point vous pouvez vous appuyer sur le chiffre affiché.
  </p>

  <h2>Quand se méfier de l'estimation</h2>

  <div class="callout">
    <div class="callout-title">Repasser en instruction manuelle</div>
    <p>
      L'estimation reste fiable sur des profils comparables à ceux du
      portefeuille d'entraînement. Trois situations justifient de ne pas s'y
      fier seul :
    </p>
    <ul>
      <li>
        un <strong>revenu très élevé</strong>, au-delà d'une centaine de lakhs :
        ces dossiers sont rares dans les données d'apprentissage ;
      </li>
      <li>
        un <strong>cumul de facteurs défavorables</strong> — tabagisme régulier,
        obésité et double pathologie — qui produit une combinaison peu
        représentée ;
      </li>
      <li>
        un montant qui <strong>s'écarte nettement de ce que vous attendiez</strong>
        pour un profil de ce type. L'outil n'a pas de garde-fou métier : il
        restitue ce que les données lui ont appris.
      </li>
    </ul>
  </div>

</div>
""")
