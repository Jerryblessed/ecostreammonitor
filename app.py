import os
from dotenv import load_dotenv

# --- STEP 1: INITIAL CONFIG (MUST BE AT THE TOP) ---
load_dotenv() # Loads local .env for development

# Datadog Environment Settings
os.environ["DD_SITE"] = os.environ.get("DD_SITE", "us5.datadoghq.com")
os.environ["DD_TRACE_AGENT_URL"] = os.environ.get("DD_TRACE_AGENT_URL", "https://trace.agent.us5.datadoghq.com")
os.environ["DD_SERVICE"] = "ecostream-ai"
os.environ["DD_ENV"] = os.environ.get("DD_ENV", "production")

import json
import base64
import datetime
import sys
import requests
from flask import Flask, request, jsonify, render_template

# GCP & Partner SDKs
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import bigquery
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from confluent_kafka import Producer

from google.cloud import speech
# Partner: ElevenLabs Official SDK (v2.27.0)

from elevenlabs.client import ElevenLabs

# Partner: Datadog Components
from datadog import initialize, api
from ddtrace import tracer, patch_all

speech_client = speech.SpeechClient()

# Initialize Datadog with explicit US5 Host for Events and Traces
initialize(
    api_key=os.environ.get("DD_API_KEY"), 
    app_key=os.environ.get("DD_APP_KEY"),
    api_host=f"https://api.{os.environ.get('DD_SITE')}"
)
patch_all()

app = Flask(__name__)

# ==========================================
# 2. LOAD CONFIGURATION FROM ENV
# ==========================================
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "tag-file-manager")
os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = PROJECT_ID

CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
MAPS_API_KEY = os.environ.get("MAPS_API_KEY")

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") 

# Initialize Clients
vertexai.init(project=PROJECT_ID, location="us-central1")
bq_client = bigquery.Client(project=PROJECT_ID)
el_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Kafka Configuration (Confluent Cloud)
kafka_config = {
    'bootstrap.servers': os.environ.get("KAFKA_BOOTSTRAP"),
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': os.environ.get("KAFKA_USER"), 
    'sasl.password': os.environ.get("KAFKA_PASS") 
}
producer = Producer(kafka_config)

def safe_float(value, default=0.0):
    try: return float(value) if value is not None else default
    except: return default

# ==========================================
# 3. ROUTES
# ==========================================

@app.route('/')
def index():
    return render_template('index.html', maps_key=MAPS_API_KEY, client_id=CLIENT_ID)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        audio_data = request.json.get('audio') # Base64 audio from JS
        content = base64.b64decode(audio_data)

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code="en-NG", # Optimized for Nigeria
            enable_automatic_punctuation=True
        )

        response = speech_client.recognize(config=config, audio=audio)
        
        # Get the highest confidence transcript
        transcript = response.results[0].alternatives[0].transcript if response.results else ""
        
        return jsonify({"transcript": transcript})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/chat', methods=['POST'])
@tracer.wrap()
def chat():
    try:
        data = request.json
        token = data.get('credential') 
        user_prompt = data.get('prompt')

        # 1. Identity Verification
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
        user_email = idinfo['email']

        # 2. AI Brain (Vertex AI)
        with tracer.trace("gemini.thinking", service="ecostream-ai") as span:
            model = GenerativeModel("gemini-2.5-flash")
            config = GenerationConfig(response_mime_type="application/json")
            sys_msg = "You are EcoStream Guide. Helping the user find local sustainable markets. Respond ONLY in JSON: {answer, lat, lng, market_name, carbon_saved}"
            ai_res = model.generate_content(f"{sys_msg} Query: {user_prompt}", generation_config=config)
            
            ai_data = json.loads(ai_res.text.strip().replace('```json', '').replace('```', ''))
            span.set_tag("eco.carbon_saved", ai_data.get('carbon_saved', 0))

        # 3. Voice Synthesis (ElevenLabs SDK v2.27.0)
        try:
            audio_generator = el_client.text_to_speech.convert(
                text=ai_data['answer'],
                voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            # Draining generator into buffer to ensure full delivery
            audio_bytes = b"".join([chunk for chunk in audio_generator if isinstance(chunk, bytes)])
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        except Exception as ve:
            print(f"ElevenLabs Error: {ve}")
            audio_base64 = ""

        # 4. Prepare Data Payload
        event_payload = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "user_email": user_email,
            "user_name": idinfo.get('name', 'Jeremiah Ope'),
            "user_prompt": user_prompt,
            "market_name": ai_data.get('market_name', 'Eco Market'),
            "carbon_saved": safe_float(ai_data.get('carbon_saved'), 0.1),
            "lat": safe_float(ai_data.get('lat'), 6.5244),
            "lng": safe_float(ai_data.get('lng'), 3.3792)
        }

        # 5. Partner Observability & Streaming
        api.Event.create(
            title='Sustainable Market Found', 
            text=f"User {user_email} saved {event_payload['carbon_saved']}kg CO2.", 
            tags=["env:production", "service:ecostream-ai"],
            alert_type='info'
        )
        
        # Confluent Kafka "Data in Motion"
        producer.produce('market-activity', json.dumps(event_payload).encode('utf-8'))
        producer.flush()
        
        # BigQuery "Data at Rest" (Matches Schema)
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
        api.Event.create(title='EcoStream Critical Crash', text=str(e), alert_type='error')
        print(f"CRITICAL ERROR: {e}")
        return jsonify({"error": "Internal server error reported to Datadog"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)