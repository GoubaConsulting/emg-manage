"""
==========================================================
Projet : EMG MANAGE

Module : Situations

Description :
Numérotation des situations et des manquants.

==========================================================
"""

from django.db.models import Max

from .models import (
    SituationJournaliere,
    Manquant,
    ReglementManquant,
)


# ==========================================================
# NUMERO SITUATION
# ==========================================================

def generer_numero_situation():

    dernier = (
        SituationJournaliere.objects
        .aggregate(
            maximum=Max("idsituation")
        )
        ["maximum"]
    )

    numero = (
        dernier + 1
        if dernier
        else 1
    )

    return f"SIT-{numero:06d}"


# ==========================================================
# NUMERO MANQUANT
# ==========================================================

def generer_numero_manquant():

    dernier = (
        Manquant.objects
        .aggregate(
            maximum=Max("idmanquant")
        )
        ["maximum"]
    )

    numero = (
        dernier + 1
        if dernier
        else 1
    )

    return f"MAN-{numero:06d}"


# ==========================================================
# NUMERO REGLEMENT
# ==========================================================

def generer_numero_reglement():

    dernier = (
        ReglementManquant.objects
        .aggregate(
            maximum=Max("idreglement")
        )
        ["maximum"]
    )

    numero = (
        dernier + 1
        if dernier
        else 1
    )

    return f"REG-{numero:06d}"