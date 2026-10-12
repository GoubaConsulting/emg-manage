from .models import NotificationCorrection


def corrections_non_lues(request):
    if not request.user.is_authenticated:
        return {"nb_corrections_non_lues": 0}
    if request.user.profil.role != "GERANT":
        return {"nb_corrections_non_lues": 0}
    return {
        "nb_corrections_non_lues": NotificationCorrection.objects.filter(
            destinataire=request.user, date_lecture__isnull=True
        ).count()
    }
