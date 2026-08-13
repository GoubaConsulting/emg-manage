"""
==========================================================
Projet : EMG MANAGE

Module : Situations

URLs du module Situations.
==========================================================
"""

from django.urls import path

from . import views


app_name = "situations"


urlpatterns = [

    path(

        "ajouter/",

        views.ajouter_situation,

        name="ajouter_situation"

    ),


]