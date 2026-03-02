import google.generativeai as genai

genai.configure(api_key='AIzaSyBlf1vKDKnb9Y0gbNAf-Xkv9aM3yS2ox4M')

# On utilise l'alias universel listé dans tes logs
model = genai.GenerativeModel('gemini-flash-latest')

try:
    print("Tentative avec gemini-flash-latest...")
    response = model.generate_content("OK")
    print(f"RÉPONSE IA : {response.text}")
    print("✅ ENFIN ! Ce modèle est celui qu'il faut utiliser.")
except Exception as e:
    print(f"❌ ÉCHEC : {e}")