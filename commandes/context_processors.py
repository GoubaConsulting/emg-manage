from .selectors import nombre_commandes_en_attente


def commandes_en_attente(request):

    if not request.user.is_authenticated:

        return {
            "nb_commandes_en_attente": 0
        }

    return {

        "nb_commandes_en_attente":
            nombre_commandes_en_attente(
                request.user
            )

    }