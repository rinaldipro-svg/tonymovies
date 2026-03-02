from google import genai
import os

client = genai.Client(api_key='AIzaSyBlf1vKDKnb9Y0gbNAf-Xkv9aM3yS2ox4M')

print("--- TEST DE VALIDATION : GEMINI 2.0 FLASH LITE ---")
try:
    # On teste la version Lite, souvent plus permissive sur les quotas gratuits
    response = client.models.generate_content(
        model='gemini-2.0-flash-lite', 
        contents="Dis OK"
    )
    print(f"RÉPONSE IA : {response.text}")
    print("✅ ENFIN ! C'est ce modèle qu'il faut utiliser.")
except Exception as e:
    print(f"❌ ÉCHEC : {e}")