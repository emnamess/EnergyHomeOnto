# Frontend

Application hôte React + TypeScript + Vite. Lancer avec `npm install` puis
`npm run dev`. Les cinq parcours individuels sont dans `src/features/` ; le module
de recherche partagé est dans `src/shared/recherche-intelligente/`. Le proxy Vite
transmet `/api` à FastAPI sur le port 8000.

L’application s’ouvre sur le tableau de bord (`src/shared/tableau-de-bord/`). Le cadre
commun (barre latérale, en-tête de page, état de l’API) est dans `src/shared/Layout.tsx`.
Pour ajouter une page : l’activer dans `SECTIONS` (`Layout.tsx`) et la déclarer dans
`src/App.tsx`. Voir le guide pas à pas dans le `README.md` racine (§ 6).
