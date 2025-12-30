import os
import json
import base64
import datetime
import requests
from flask import Flask, request, jsonify, render_template

# GCP & Partner SDKs
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import bigquery
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from elevenlabs.client import ElevenLabs
from confluent_kafka import Producer
from datadog import initialize, api
from ddtrace import tracer, patch_all
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# --- STEP 1: INITIALIZE MONITORING ---
os.environ["DD_SITE"] = os.environ.get("DD_SITE", "us5.datadoghq.com")
os.environ["DD_TRACE_AGENT_URL"] = "https://trace.agent.us5.datadoghq.com"

initialize(
    api_key=os.environ.get("DD_API_KEY"), 
    app_key=os.environ.get("DD_APP_KEY"),
    api_host=f"https://api.{os.environ.get('DD_SITE')}"
)
patch_all()

app = Flask(__name__)

# --- STEP 2: LOAD CONFIGURATION ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "tag-file-manager")
CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
MAPS_API_KEY = os.environ.get("MAPS_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "x8xv0H8Ako6Iw3cKXLoC") # Default: Adam

# Initialize Services
vertexai.init(project=PROJECT_ID, location="us-central1")
bq_client = bigquery.Client(project=PROJECT_ID)
el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Kafka Configuration
producer = Producer({
    'bootstrap.servers': os.environ.get("KAFKA_BOOTSTRAP"),
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': os.environ.get("KAFKA_USER"), 
    'sasl.password': os.environ.get("KAFKA_PASS") 
})

def safe_float(value, default=0.0):
    try: return float(value) if value is not None else default
    except: return default

@app.route('/')
def index():
    return render_template('index.html', maps_key=MAPS_API_KEY, client_id=CLIENT_ID)

@app.route('/chat', methods=['POST'])
@tracer.wrap()
def chat():
    try:
        data = request.json
        token = data.get('credential') 
        user_prompt = data.get('prompt')

        # 1. Identity
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
        user_email = idinfo['email']

        # 2. AI Brain
        with tracer.trace("gemini.thinking", service="ecostream-ai") as span:
            model = GenerativeModel("gemini-2.5-flash")
            config = GenerationConfig(response_mime_type="application/json")
            sys_msg = "You are EcoStream Guide. Respond ONLY in JSON: {answer, lat, lng, market_name, carbon_saved}"
            ai_res = model.generate_content(f"{sys_msg} Query: {user_prompt}", generation_config=config)
            ai_data = json.loads(ai_res.text.strip().replace('```json', '').replace('```', ''))
            span.set_tag("eco.carbon_saved", ai_data.get('carbon_saved', 0))

        # 3. Voice (Robust Loop)
        try:
            audio_stream = el_client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text=ai_data['answer'],
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            audio_bytes = b"".join(audio_stream)
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        except: audio_base64 = ""

        # 4. Data Payloads
        event_payload = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "user_email": user_email,
            "user_name": idinfo.get('name', 'User'),
            "user_prompt": user_prompt,
            "market_name": ai_data.get('market_name', 'Eco Market'),
            "carbon_saved": safe_float(ai_data.get('carbon_saved'), 0.1),
            "lat": safe_float(ai_data.get('lat'), 6.5244),
            "lng": safe_float(ai_data.get('lng'), 3.3792)
        }

        # 5. Partner Exports
        api.Event.create(title='Market Search', text=f"User {user_email} saved {event_payload['carbon_saved']}kg", tags=["env:prod"])
        producer.produce('market-activity', json.dumps(event_payload).encode('utf-8'))
        producer.flush()
        
        bq_row = {k: v for k, v in event_payload.items() if k not in ['lat', 'lng']}
        bq_client.insert_rows_json(f"{PROJECT_ID}.ecostream_dataset.logs", [bq_row])

        return jsonify({
            "audio": audio_base64,
            "answer": ai_data['answer'],
            "location": {"lat": event_payload['lat'], "lng": event_payload['lng']},
            "carbon_saved": event_payload['carbon_saved'],
            "user_name": event_payload['user_name']
        })
    except Exception as e:
        print(f"CRASH: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)