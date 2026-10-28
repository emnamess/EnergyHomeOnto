# Données

L’ontologie et ses individus sont lus directement depuis `../energyhomeonto.owx`
(fichier Protégé, format OWL/XML) : il n’y a plus de copie Turtle à maintenir.

Ce dossier contient uniquement `journal-crud.rq`, créé automatiquement par le
backend : chaque requête SPARQL Update (création, modification, suppression)
faite depuis l’application y est ajoutée, puis rejouée au démarrage. Ce fichier
est local à chaque poste (ignoré par Git). Le supprimer remet les données à
l’état de l’ontologie.
