# 🌊 EcoStreammonitor: Monitoring marchent account real-time

**Built for the AI Partner Catalyst: Google Cloud Partnerships Hackathon | Confluent Challenge Entry**

> "Turning Sustainable Intent into Local Action through Data in Motion."

---

## 📖 Overview
**EcoStreammonitor** is a voice-driven AI navigator designed to solve **UN Sustainable Development Goal (SDG) 12: Responsible Consumption and Production**. 

In mega-cities like Lagos, citizens face a "Green Visibility Gap"—they want to shop sustainably but lack real-time data on local eco-friendly markets. EcoStream bridges this gap by using **Vertex AI** and **ElevenLabs** to provide a conversational guide that maps local markets and provides instant carbon-savings transparency. 

Every interaction is treated as **Data in Motion**, streamed through **Confluent Cloud** and monitored for reliability by **Datadog**.

---

## 🏗️ System Architecture
EcoStreammonitor is built on a high-availability, multi-partner cloud architecture:

1.  **Secure Entry:** Google OAuth 2.0 ensures identity-based tracking.
2.  **The Brain:** **Vertex AI (Gemini 2.5 Flash)** processes voice intent and calculates carbon impact.
3.  **The Voice:** **ElevenLabs (Rachel)** provides natural, human-like coaching and feedback.
4.  **The Heartbeat:** **Confluent Cloud** handles real-time streaming of shopping events via the `market-activity` Kafka topic.
5.  **The Eyes:** **Google Maps JavaScript API** uses Vector Maps and Advanced Markers to navigate the user.
6.  **The Warehouse:** **Google BigQuery** persists data for long-term urban sustainability analytics.
7.  **The Watchtower:** **Datadog** provides full-stack observability, tracking AI latency and business impact metrics.

---

## 🚀 Partner Integration Excellence

### 🧡 Confluent (Primary Category)
*   **Data in Motion:** We moved beyond "Data at Rest." Every search produces a rich JSON payload to the `market-activity` topic.
*   **Real-time Logic:** This architecture enables city planners to see sustainability pulses as they happen, not weeks later in a report.

### 💜 Datadog (Observability Supporter)
*   **Application Health:** Deep integration with Google Cloud Platform via the Marketplace.
*   **Actionable Items:** Automated monitors for BigQuery quotas and custom business events for AI searches.
*   **Incident Management:** Every AI anomaly triggers an automated **Datadog Case** with full user context.

### 🎙️ ElevenLabs (Conversational Supporter)
*   **Voice Design:** Utilizing the **Multilingual v2** model to provide an encouraging, human-like persona (Rachel) for the Eco-Guide.
*   **Accessibility:** Removed the barrier of typing, allowing users to interact entirely through natural speech.

---

## 🛠️ Google Cloud Products Used (9)
*   **Vertex AI (Gemini 2.5 Flash)**
*   **Cloud Run** (Containerized Hosting)
*   **BigQuery** (Data Warehousing)
*   **Google Maps Platform** (Advanced Markers & Vector Engine)
*   **Google Cloud Speech-to-Text**
*   **Cloud Identity (OAuth 2.0)**
*   **Secret Manager**
*   **Cloud Build**
*   **Artifact Registry**

---

## 📁 Repository Contents
*   `app.py`: The production Flask backend.
*   `templates/index.html`: The modern, voice-enabled frontend.
*   `ecostream_dashboard.json`: **[Hard Requirement]** Exported Datadog Dashboard configuration.
*   `datadog_monitor.json`: **[Hard Requirement]** Exported BigQuery quota monitor logic.
*   `Procfile` & `Dockerfile`: Professional deployment configurations.

---

## 🎬 Cinematic Demo
Our final demo features **Veo 3.1** generative video, illustrating a citizen's journey from a digital search in Lagos to the physical act of sustainable shopping in a local market. Ambient audio was generated using **ElevenLabs Sound Effects** to provide a hyper-realistic experience.

---

## 👨‍💻 Developer
**Jeremiah Ope**  
*Solutions Architect & AI Developer*  
Lagos, Nigeria 🇳🇬

---

