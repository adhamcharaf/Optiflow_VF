# Règles de Développement Optiflow

## Règles Générales

### 1. Interdiction des Emojis
- **JAMAIS d'emojis** dans le code, documentation, ou interface
- Les emojis ne sont pas professionnels et peuvent causer des erreurs d'encodage
- Cette règle s'applique à tous les fichiers : Python, Markdown, JSON, etc.

### 2. Utilisation des Icônes (Pages UI uniquement)
- Pour les pages Streamlit uniquement, utiliser des icônes à la place des emojis
- Streamlit intègre nativement Google Material Symbols (plus de 2000+ icônes) que tu peux utiliser avec la syntaxe : :material/icon_name:
-Uniquement si besoin utiliser le mcp context7 pour avoir plus d'informations sur la documentation

### 3. Application des Règles
- Scripts ML : Aucun emoji, aucune icône
- Utilitaires et composants : Aucun emoji, aucune icône
- Pages Streamlit : Icônes autorisées pour l'UX, emojis interdits
- Documentation : Aucun emoji, aucune icône

### 4. Alternatives Professionnelles
- Utiliser des couleurs pour différencier les statuts
- Utiliser des formes géométriques simples (●, ■, ▲, ▼)
- Utiliser du texte descriptif clair
- Utiliser des codes couleur CSS/HTML

## Exemples d'Application

### ❌ Incorrect
```python
st.write("🔴 Alerte critique")
st.write("📊 Dashboard")
print("✅ Traitement terminé")
```

### ✅ Correct
```python
st.write("🔴 Alerte critique")  # Icône pour page UI
st.write("● Dashboard")        # Icône simple pour page UI
print("Traitement terminé")    # Pas d'icône pour script
```

### 5. Eviter les duplications de code
- utiliser le code existant et ajouter ce qu'il faut
- ne pas dupliquer une fonctionnalites deja existante partiellement



Cette règle doit être respectée dans tous les développements Optiflow.