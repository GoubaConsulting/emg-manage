[1mdiff --git a/comptes/urls.py b/comptes/urls.py[m
[1mindex fc109f3..796e78b 100644[m
[1m--- a/comptes/urls.py[m
[1m+++ b/comptes/urls.py[m
[36m@@ -1,24 +1,30 @@[m
 from django.urls import path[m
[32m+[m[32mfrom django.views.generic import RedirectView[m
 from . import views[m
 [m
 urlpatterns = [[m
 [m
     path([m
[31m-        'login/',[m
[32m+[m[32m        "",[m
[32m+[m[32m        RedirectView.as_view(pattern_name="login", permanent=False),[m
[32m+[m[32m    ),[m
[32m+[m
[32m+[m[32m    path([m
[32m+[m[32m        "login/",[m
         views.connexion,[m
[31m-        name='login'[m
[32m+[m[32m        name="login"[m
     ),[m
 [m
     path([m
[31m-        'logout/',[m
[32m+[m[32m        "logout/",[m
         views.deconnexion,[m
[31m-        name='logout'[m
[32m+[m[32m        name="logout"[m
     ),[m
 [m
     path([m
[31m-        'dashboard/',[m
[32m+[m[32m        "dashboard/",[m
         views.dashboard,[m
[31m-        name='dashboard'[m
[32m+[m[32m        name="dashboard"[m
     ),[m
 [m
 ][m
\ No newline at end of file[m
